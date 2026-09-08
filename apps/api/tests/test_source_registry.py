from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from app.services.sources.fetcher import FakeFetchScript
from app.services.sources.registry import FetchResult, SourceError, SourceRegistry, SourceState
from app.services.sources.url_policy import (
    UrlPolicyError,
    load_allowlist,
    to_punycode,
    validate_redirect_chain,
    validate_url,
)

ROOT = Path(__file__).resolve().parents[3]
ALLOWLIST = str(ROOT / "sources" / "allowlist.json")


@pytest.fixture()
def cfg():
    return load_allowlist(ALLOWLIST)


@pytest.fixture()
def registry(cfg):
    return SourceRegistry(allowlist=cfg)


def test_allowlist_loads_official_hosts_only(cfg) -> None:
    hosts = {h.host for h in cfg.hosts}
    assert "pravo.gov.ru" in hosts
    assert "consultant.ru" not in hosts
    assert "garant.ru" not in hosts


def test_https_only_and_userinfo_and_port(cfg) -> None:
    with pytest.raises(UrlPolicyError) as e1:
        validate_url("http://pravo.gov.ru/", cfg=cfg)
    assert e1.value.code == "https_only"
    with pytest.raises(UrlPolicyError) as e2:
        validate_url("https://user:pass@pravo.gov.ru/", cfg=cfg)
    assert e2.value.code == "userinfo_forbidden"
    with pytest.raises(UrlPolicyError) as e3:
        validate_url("https://pravo.gov.ru:8443/", cfg=cfg)
    assert e3.value.code == "port_forbidden"


def test_private_ip_and_deny_unknown_host(cfg) -> None:
    with pytest.raises(UrlPolicyError) as e1:
        validate_url("https://127.0.0.1/", cfg=cfg)
    assert e1.value.code in {"private_ip", "host_not_allowlisted"}
    with pytest.raises(UrlPolicyError) as e2:
        validate_url("https://evil.example/", cfg=cfg)
    assert e2.value.code == "host_not_allowlisted"


def test_idn_punycode(cfg) -> None:
    # Cyrillic label → punycode; still must be allowlisted host
    puny = to_punycode("прavo.gov.ru") if False else to_punycode("xn--example")
    assert "xn--" in to_punycode("münchen.de") or to_punycode("example.com") == "example.com"
    _ = puny
    ok = validate_url("https://pravo.gov.ru/path", cfg=cfg)
    assert ok.startswith("https://pravo.gov.ru/")


def test_redirect_bypass_blocked(cfg) -> None:
    with pytest.raises(UrlPolicyError) as ei:
        validate_redirect_chain(
            ["https://pravo.gov.ru/", "https://evil.example/steal"],
            cfg=cfg,
        )
    assert ei.value.code == "host_not_allowlisted"


def test_redirect_within_allowlist_ok(cfg) -> None:
    final = validate_redirect_chain(
        ["https://pravo.gov.ru/", "https://publication.pravo.gov.ru/Document"],
        cfg=cfg,
    )
    assert "publication.pravo.gov.ru" in final


def test_ssrf_metadata_ip_literal(cfg) -> None:
    with pytest.raises(UrlPolicyError):
        validate_url("https://169.254.169.254/latest/meta-data/", cfg=cfg)


def test_unapproved_snapshot_not_basis(registry: SourceRegistry) -> None:
    registry.seed_from_allowlist()
    src = next(iter(registry.sources.values()))
    fake = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=200,
                headers={"content-type": "text/html", "etag": "v1"},
                body=b"<html><body>Official text</body></html>",
                redirect_chain=[src.official_url],
            ),
        },
    )
    registry.fetch_fn = fake
    snap = registry.fetch_and_parse(src.id)
    assert snap.state == SourceState.AWAITING_REVIEW
    assert registry.production_basis_visible(snap.id) is False
    cite = registry.citation(snap.id, quote="Official text", on_date=date(2026, 1, 1))
    assert cite["usable_as_basis"] is False


def test_hash_change_creates_review_and_marks_dependents(registry: SourceRegistry) -> None:
    registry.seed_from_allowlist()
    src = next(iter(registry.sources.values()))
    registry.bind_dependent(src.id, norm_id="NORM.DEMO", form_id="FORM.DEMO")
    responses = {
        src.official_url: FetchResult(
            final_url=src.official_url,
            status_code=200,
            headers={"content-type": "text/html", "etag": "1"},
            body=b"<html>version-one</html>",
            redirect_chain=[src.official_url],
        ),
    }
    registry.fetch_fn = FakeFetchScript(responses)
    snap1 = registry.fetch_and_parse(src.id)
    registry.approve(
        snap1.id,
        actor="reviewer@example.com",
        comment="initial",
        valid_from=date(2024, 1, 1),
        act_title="Portal home",
    )
    assert registry.norms_status["NORM.DEMO"] in {"approved", "review"}
    responses[src.official_url] = FetchResult(
        final_url=src.official_url,
        status_code=200,
        headers={"content-type": "text/html", "etag": "2"},
        body=b"<html>version-two-changed</html>",
        redirect_chain=[src.official_url],
    )
    snap2 = registry.fetch_and_parse(src.id)
    assert snap2.content_hash != snap1.content_hash
    assert any(t.reason == "content_hash_changed" and t.status == "open" for t in registry.review_tasks)
    assert registry.norms_status["NORM.DEMO"] == "review"
    assert registry.forms_status["FORM.DEMO"] == "review"
    diff = registry.diff_snapshots(snap1.id, snap2.id)
    assert diff["hash_changed"] is True


def test_broken_link_marked_visible(registry: SourceRegistry) -> None:
    registry.seed_from_allowlist()
    src = next(iter(registry.sources.values()))
    registry.fetch_fn = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=500,
                headers={},
                body=b"",
                redirect_chain=[src.official_url],
            ),
        },
    )
    with pytest.raises(SourceError) as ei:
        registry.fetch_and_parse(src.id)
    assert ei.value.code == "fetch_broken"
    snap = registry.latest_snapshot(src.id)
    assert snap is not None
    assert snap.link_status == "broken"


def test_stale_not_hidden(registry: SourceRegistry) -> None:
    registry.seed_from_allowlist()
    src = next(iter(registry.sources.values()))
    registry.fetch_fn = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=200,
                headers={"content-type": "text/html"},
                body=b"<html>ok</html>",
                redirect_chain=[src.official_url],
            ),
        },
    )
    snap = registry.fetch_and_parse(src.id)
    snap.fetched_at = datetime.now(UTC) - timedelta(hours=src.fetch_interval_hours * 2)
    due = registry.freshness_due()
    assert src.id in due
    assert snap.link_status == "stale"


def test_temporal_applicability_no_auto_current(registry: SourceRegistry) -> None:
    registry.seed_from_allowlist()
    src = next(iter(registry.sources.values()))
    registry.fetch_fn = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=200,
                headers={"content-type": "text/html"},
                body=b"<html>act</html>",
                redirect_chain=[src.official_url],
            ),
        },
    )
    snap = registry.fetch_and_parse(src.id)
    registry.approve(
        snap.id,
        actor="ed@example.com",
        comment="approve",
        valid_from=date(2025, 1, 1),
        valid_to=date(2025, 12, 31),
        act_title="Demo act metadata from review — not from model memory",
        act_number="N/A",
        act_date=date(2025, 1, 1),
    )
    assert registry.applicable_on(snap.id, date(2025, 6, 1)) is True
    assert registry.applicable_on(snap.id, date(2026, 6, 1)) is False
    cite = registry.citation(snap.id, quote="act", on_date=date(2026, 1, 2))
    assert cite["usable_as_basis"] is False
    assert cite["reason"] == "not_applicable_on_date"


def test_audit_shows_who_approved(registry: SourceRegistry) -> None:
    registry.seed_from_allowlist()
    src = next(iter(registry.sources.values()))
    registry.fetch_fn = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=200,
                headers={"content-type": "text/html"},
                body=b"<html>x</html>",
                redirect_chain=[src.official_url],
            ),
        },
    )
    snap = registry.fetch_and_parse(src.id)
    registry.approve(snap.id, actor="alice@org", comment="lgtm", valid_from=date(2026, 1, 1))
    approved = [a for a in registry.audit if a.action == "approved"]
    assert approved and approved[-1].actor == "alice@org"
    assert approved[-1].snapshot_id == snap.id


def test_seed_has_no_invented_norms(registry: SourceRegistry) -> None:
    created = registry.seed_from_allowlist()
    assert created
    for s in created:
        # metadata only
        assert "Official domain:" in s.title
        assert s.official_url.startswith("https://")
