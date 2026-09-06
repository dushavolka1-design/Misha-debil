from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, UTC
from typing import Any
from uuid import UUID, uuid4

from app.services.entry.deadlines import DeadlineResult, calculate_deadline
from app.services.entry.pack import (
    APPROVED_VISA_REGIMES,
    DECISION_RULES,
    PACK_VERSION,
    DecisionRule,
    Stage,
)
from app.services.sources.registry import SourceRegistry, SourceState

DISCLAIMER = (
    "Информационный чеклист по утверждённым правилам. "
    "Сервис не обещает допуск через границу и не гарантирует принятие заявления. "
    "Это не юридическая консультация."
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class EntryError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class Questionnaire:
    citizenship: str  # ISO-like code or "stateless" or "unknown"
    second_citizenship: bool = False
    second_citizenship_code: str | None = None
    age_band: str = "adult"  # minor|adult
    visa_regime_id: str | None = None
    purpose: str = "tourism"  # tourism|work|study|family|other
    planned_stay_days: int | None = None
    planned_entry_date: date | None = None
    eaeu_member: bool = False
    invitation: bool = False
    host_type: str | None = None  # individual|org|none
    region_code: str | None = None
    special_statuses: list[str] = field(default_factory=list)
    plans_extension_or_change: bool = False
    timezone: str = "Europe/Moscow"
    draft_consent: bool = False


@dataclass
class StepResult:
    rule_id: str
    rule_version: str
    stage: str
    title: str
    actor: str
    prepare: str
    deadline: dict[str, Any]
    authority: str
    official_sources: list[dict[str, Any]]
    as_of: str
    exceptions: str
    needs_review: bool
    activated_by: dict[str, Any]
    outcome: str
    fee: dict[str, Any] | None
    freshness_blocked: bool = False


@dataclass
class EvaluationSnapshot:
    id: UUID
    created_at: datetime
    pack_version: str
    questionnaire: dict[str, Any]
    stages: dict[str, list[StepResult]]
    activated_rule_ids: list[str]
    unknown_case: bool
    disclaimer: str
    freshness_blocked_rules: list[str]


@dataclass
class DraftRecord:
    id: UUID
    user_id: UUID | None
    questionnaire: dict[str, Any]
    consent_at: datetime
    updated_at: datetime


class EntryWizardService:
    def __init__(self, sources: SourceRegistry) -> None:
        self.sources = sources
        self.drafts: dict[UUID, DraftRecord] = {}
        self.snapshots: dict[UUID, EvaluationSnapshot] = {}
        # Optional fee table bound to approved snapshots only (no invented amounts)
        self.fee_catalog: dict[str, dict[str, Any]] = {}

    def visa_regime_catalog(self) -> list[dict[str, Any]]:
        return [{"id": k, **v} for k, v in APPROVED_VISA_REGIMES.items()]

    def save_draft(self, q: Questionnaire, *, user_id: UUID | None) -> DraftRecord:
        if not q.draft_consent:
            raise EntryError("consent_required", "Draft save requires explicit consent", http_status=403)
        # Do not persist unnecessary sensitive extras
        payload = self._serialize_q(q)
        rec = DraftRecord(
            id=uuid4(),
            user_id=user_id,
            questionnaire=payload,
            consent_at=utcnow(),
            updated_at=utcnow(),
        )
        self.drafts[rec.id] = rec
        return rec

    def _serialize_q(self, q: Questionnaire) -> dict[str, Any]:
        return {
            "citizenship": q.citizenship,
            "second_citizenship": q.second_citizenship,
            "second_citizenship_code": q.second_citizenship_code if q.second_citizenship else None,
            "age_band": q.age_band,
            "visa_regime_id": q.visa_regime_id,
            "purpose": q.purpose,
            "planned_stay_days": q.planned_stay_days,
            "planned_entry_date": q.planned_entry_date.isoformat() if q.planned_entry_date else None,
            "eaeu_member": q.eaeu_member,
            "invitation": q.invitation,
            "host_type": q.host_type,
            "region_code": q.region_code,
            "special_statuses": list(q.special_statuses),
            "plans_extension_or_change": q.plans_extension_or_change,
            "timezone": q.timezone,
        }

    def _match(self, rule: DecisionRule, q: Questionnaire) -> tuple[bool, dict[str, Any]]:
        activated: dict[str, Any] = {}
        c = rule.conditions
        for key, expected in c.items():
            if key == "citizenship":
                if q.citizenship != expected:
                    return False, {}
                activated["citizenship"] = q.citizenship
            elif key == "citizenship_not":
                if q.citizenship == expected:
                    return False, {}
                activated["citizenship"] = q.citizenship
            elif key == "visa_regime_id":
                if q.visa_regime_id != expected:
                    return False, {}
                activated["visa_regime_id"] = q.visa_regime_id
            elif key == "purpose":
                if q.purpose != expected:
                    return False, {}
                activated["purpose"] = q.purpose
            elif key == "eaeu_member":
                if bool(q.eaeu_member) != bool(expected):
                    return False, {}
                activated["eaeu_member"] = q.eaeu_member
            elif key == "age_band":
                if q.age_band != expected:
                    return False, {}
                activated["age_band"] = q.age_band
            elif key == "max_stay_days_lte":
                if q.planned_stay_days is None or q.planned_stay_days > int(expected):
                    return False, {}
                activated["planned_stay_days"] = q.planned_stay_days
            elif key == "has_planned_entry_date":
                if bool(q.planned_entry_date) != bool(expected):
                    return False, {}
                activated["planned_entry_date"] = q.planned_entry_date.isoformat() if q.planned_entry_date else None
            elif key == "plans_extension_or_change":
                if bool(q.plans_extension_or_change) != bool(expected):
                    return False, {}
                activated["plans_extension_or_change"] = q.plans_extension_or_change
            elif key == "has_invitation_or_host":
                ok = q.invitation or (q.host_type not in {None, "none"})
                if bool(ok) != bool(expected):
                    return False, {}
                activated["invitation"] = q.invitation
                activated["host_type"] = q.host_type
            elif key == "special_statuses_contains":
                if expected not in q.special_statuses:
                    return False, {}
                activated["special_statuses"] = list(q.special_statuses)
            else:
                return False, {}
        return True, activated

    def _sources_ok(self, slugs: tuple[str, ...], on: date) -> tuple[bool, list[dict[str, Any]], bool]:
        """Returns (all_approved_and_fresh, source payloads, freshness_blocked)."""
        payloads = []
        freshness_blocked = False
        all_ok = True
        for slug in slugs:
            sid = self.sources.by_slug.get(slug)
            if not sid:
                all_ok = False
                payloads.append({"slug": slug, "status": "missing", "usable_as_basis": False})
                continue
            src = self.sources.sources[sid]
            # Freshness: stale latest snapshot blocks
            latest = self.sources.latest_snapshot(sid)
            if latest and latest.link_status in {"stale", "broken"}:
                freshness_blocked = True
                all_ok = False
            approved = self.sources.approved_snapshot(sid)
            if not approved:
                all_ok = False
                payloads.append(
                    {
                        "slug": slug,
                        "organ": src.organ,
                        "status": src.state.value,
                        "usable_as_basis": False,
                    },
                )
                continue
            if not self.sources.applicable_on(approved.id, on):
                all_ok = False
                payloads.append(
                    {
                        "slug": slug,
                        "organ": src.organ,
                        "status": "not_applicable_on_date",
                        "usable_as_basis": False,
                        "snapshot_id": str(approved.id),
                    },
                )
                continue
            # Conflict: multiple approved with overlapping different hashes for same slug N/A (one approved)
            payloads.append(
                {
                    "slug": slug,
                    "organ": src.organ,
                    "official_url": approved.final_url,
                    "snapshot_id": str(approved.id),
                    "content_hash": approved.content_hash,
                    "usable_as_basis": True,
                    "as_of": on.isoformat(),
                },
            )
        return all_ok, payloads, freshness_blocked

    def _fee(self, rule: DecisionRule, on: date) -> dict[str, Any] | None:
        if not rule.fee_source_slug:
            return None
        sid = self.sources.by_slug.get(rule.fee_source_slug)
        if not sid:
            return {"available": False, "message": "уточните на официальном ресурсе"}
        approved = self.sources.approved_snapshot(sid)
        if not approved or not self.sources.applicable_on(approved.id, on):
            return {"available": False, "message": "уточните на официальном ресурсе"}
        entry = self.fee_catalog.get(rule.fee_source_slug)
        if not entry:
            return {"available": False, "message": "уточните на официальном ресурсе"}
        # Fee must declare effective date from approved editorial data
        eff = entry.get("effective_date")
        if not eff or date.fromisoformat(eff) > on:
            return {"available": False, "message": "уточните на официальном ресурсе"}
        return {
            "available": True,
            "amount": entry.get("amount"),
            "currency": entry.get("currency"),
            "effective_date": eff,
            "source_snapshot_id": str(approved.id),
            "official_url": approved.final_url,
        }

    def _rule_valid_on(self, rule: DecisionRule, on: date) -> bool:
        if on < rule.valid_from:
            return False
        if rule.valid_to and on > rule.valid_to:
            return False
        return True

    def evaluate(self, q: Questionnaire, *, as_of: date | None = None) -> EvaluationSnapshot:
        on = as_of or date.today()
        # Visa regime must be from approved catalog when provided
        if q.visa_regime_id and q.visa_regime_id not in APPROVED_VISA_REGIMES:
            raise EntryError("visa_regime_not_approved", "Visa regime must come from approved catalog")

        stages: dict[str, list[StepResult]] = {s.value: [] for s in Stage}
        activated_ids: list[str] = []
        freshness_blocked_rules: list[str] = []
        unknown_case = q.citizenship == "unknown"

        # Source conflict detection: if a slug has awaiting_review newer than approved with different hash
        conflict = self._detect_source_conflicts()
        if conflict:
            # Block production-like certainty
            freshness_blocked_rules.append("source_conflict")

        ordered = sorted(DECISION_RULES, key=lambda r: r.priority)
        for rule in ordered:
            if not self._rule_valid_on(rule, on):
                continue
            ok, activated = self._match(rule, q)
            if not ok:
                continue
            sources_ok, source_payloads, blocked = self._sources_ok(rule.official_source_slugs, on)
            if blocked or "source_conflict" in freshness_blocked_rules:
                freshness_blocked_rules.append(rule.rule_id)
            needs_review = (not sources_ok) or blocked or rule.outcome == "unknown_case"
            if rule.requires_approved_sources and not sources_ok:
                needs_review = True
            # Stale rule pack blocked by freshness policy
            freshness_blocked = blocked or (rule.rule_id in freshness_blocked_rules)

            dl = calculate_deadline(
                rule.deadline_expression,
                anchor=q.planned_entry_date,
                timezone=q.timezone,
                region_code=q.region_code,
            )
            deadline_payload = {
                "kind": dl.kind.value,
                "expression": dl.expression,
                "timezone": dl.timezone,
                "absolute_date": dl.absolute_date.isoformat() if dl.absolute_date else None,
                "explanation": dl.explanation,
                "needs_review": dl.needs_review,
                "certainty": dl.certainty,
            }
            if dl.needs_review:
                needs_review = True

            step = StepResult(
                rule_id=rule.rule_id,
                rule_version=rule.version,
                stage=rule.stage.value,
                title=rule.title,
                actor=rule.actor,
                prepare=rule.prepare,
                deadline=deadline_payload,
                authority=rule.authority,
                official_sources=source_payloads,
                as_of=on.isoformat(),
                exceptions=rule.exceptions,
                needs_review=needs_review or freshness_blocked,
                activated_by=activated,
                outcome=rule.outcome if not freshness_blocked else "blocked_freshness",
                fee=self._fee(rule, on),
                freshness_blocked=freshness_blocked,
            )
            # Unknown citizenship: only unknown_case rules (and maybe minor) — suppress invented lists
            if unknown_case and rule.outcome != "unknown_case" and rule.rule_id != "entry.minor.guardian":
                # Still allow minor guardian alongside unknown? Prefer only unknown_case
                if rule.rule_id != "entry.unknown_citizenship":
                    continue
            stages[rule.stage.value].append(step)
            activated_ids.append(rule.rule_id)

        if unknown_case and not any(r == "entry.unknown_citizenship" for r in activated_ids):
            # Force unknown outcome
            pass

        snap = EvaluationSnapshot(
            id=uuid4(),
            created_at=utcnow(),
            pack_version=PACK_VERSION,
            questionnaire=self._serialize_q(q),
            stages=stages,
            activated_rule_ids=activated_ids,
            unknown_case=unknown_case,
            disclaimer=DISCLAIMER,
            freshness_blocked_rules=sorted(set(freshness_blocked_rules)),
        )
        self.snapshots[snap.id] = snap
        return snap

    def _detect_source_conflicts(self) -> bool:
        for src in self.sources.sources.values():
            src_id = src.get("id") if isinstance(src, dict) else getattr(src, "id", None)
            if not src_id:
                continue
            approved = self.sources.approved_snapshot(src_id)
            latest = self.sources.latest_snapshot(src_id)
            latest_id = latest.get("id") if isinstance(latest, dict) else getattr(latest, "id", None)
            approved_id = approved.get("id") if isinstance(approved, dict) else getattr(approved, "id", None)
            latest_state = latest.get("state") if isinstance(latest, dict) else getattr(latest, "state", None)
            latest_hash = (
                latest.get("content_hash") if isinstance(latest, dict) else getattr(latest, "content_hash", None)
            )
            approved_hash = (
                approved.get("content_hash") if isinstance(approved, dict) else getattr(approved, "content_hash", None)
            )
            if (
                approved
                and latest
                and latest_id != approved_id
                and str(latest_state) == SourceState.AWAITING_REVIEW.value
                and latest_hash != approved_hash
            ):
                return True
        return False

    def refresh(self, snapshot_id: UUID) -> EvaluationSnapshot:
        old = self.snapshots.get(snapshot_id)
        if not old:
            raise EntryError("not_found", "Snapshot not found", http_status=404)
        qdict = old.questionnaire
        q = Questionnaire(
            citizenship=qdict["citizenship"],
            second_citizenship=bool(qdict.get("second_citizenship")),
            second_citizenship_code=qdict.get("second_citizenship_code"),
            age_band=qdict.get("age_band") or "adult",
            visa_regime_id=qdict.get("visa_regime_id"),
            purpose=qdict.get("purpose") or "tourism",
            planned_stay_days=qdict.get("planned_stay_days"),
            planned_entry_date=date.fromisoformat(qdict["planned_entry_date"])
            if qdict.get("planned_entry_date")
            else None,
            eaeu_member=bool(qdict.get("eaeu_member")),
            invitation=bool(qdict.get("invitation")),
            host_type=qdict.get("host_type"),
            region_code=qdict.get("region_code"),
            special_statuses=list(qdict.get("special_statuses") or []),
            plans_extension_or_change=bool(qdict.get("plans_extension_or_change")),
            timezone=qdict.get("timezone") or "Europe/Moscow",
            draft_consent=True,
        )
        return self.evaluate(q)
