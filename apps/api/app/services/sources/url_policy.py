"""Deny-by-default official URL validator (SSRF / redirect / IDN safe)."""

from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Optional IDNA
try:
    import idna
except ImportError:  # pragma: no cover
    idna = None  # type: ignore


class UrlPolicyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class HostRule:
    host: str
    include_subdomains: bool
    organ: str
    criticality: str
    fetch_interval_hours: int


@dataclass(frozen=True)
class AllowlistConfig:
    version: str
    max_redirects: int
    max_bytes: int
    allowed_ports: frozenset[int]
    allowed_content_types: frozenset[str]
    hosts: tuple[HostRule, ...]


def _default_allowlist_path() -> Path:
    # apps/api/app/services/sources/url_policy.py -> repo root
    return Path(__file__).resolve().parents[5] / "sources" / "allowlist.json"


@lru_cache
def load_allowlist(path: str | None = None) -> AllowlistConfig:
    p = Path(path) if path else _default_allowlist_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    hosts = tuple(
        HostRule(
            host=h["host"].lower(),
            include_subdomains=bool(h.get("include_subdomains", False)),
            organ=h.get("organ", ""),
            criticality=h.get("criticality", "medium"),
            fetch_interval_hours=int(h.get("fetch_interval_hours", 72)),
        )
        for h in data.get("hosts", [])
    )
    return AllowlistConfig(
        version=data.get("version", "unknown"),
        max_redirects=int(data.get("max_redirects", 3)),
        max_bytes=int(data.get("max_bytes", 5_000_000)),
        allowed_ports=frozenset(int(x) for x in data.get("allowed_ports", [443])),
        allowed_content_types=frozenset(data.get("allowed_content_types", [])),
        hosts=hosts,
    )


def to_punycode(host: str) -> str:
    host = host.strip().rstrip(".").lower()
    if not host:
        raise UrlPolicyError("empty_host", "Empty host")
    # Strip brackets for IPv6 literals — will be rejected later if private
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1]
    labels = host.split(".")
    out = []
    for label in labels:
        try:
            label.encode("ascii")
            out.append(label)
        except UnicodeEncodeError:
            if idna is None:
                # Fallback: encode via built-in
                out.append(label.encode("idna").decode("ascii"))
            else:
                out.append(idna.encode(label).decode("ascii"))
    return ".".join(out)


_PRIVATE_NETS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in _PRIVATE_NETS)


def host_allowed(host: str, cfg: AllowlistConfig) -> HostRule | None:
    host = to_punycode(host)
    if is_blocked_ip(host):
        return None
    for rule in cfg.hosts:
        if host == rule.host:
            return rule
        if rule.include_subdomains and host.endswith("." + rule.host):
            return rule
    return None


def validate_url(url: str, *, cfg: AllowlistConfig | None = None, allow_resolve_check: bool = True) -> str:
    """Validate and normalize URL. Returns canonical https URL without userinfo/fragment."""
    cfg = cfg or load_allowlist()
    raw = (url or "").strip()
    if not raw:
        raise UrlPolicyError("empty_url", "Empty URL")
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise UrlPolicyError("https_only", "Only HTTPS URLs are allowed")
    if parsed.username or parsed.password:
        raise UrlPolicyError("userinfo_forbidden", "URL userinfo is forbidden")
    if not parsed.hostname:
        raise UrlPolicyError("missing_host", "Missing host")
    host = to_punycode(parsed.hostname)
    if is_blocked_ip(host):
        raise UrlPolicyError("private_ip", "Private/reserved IP literal is forbidden")
    port = parsed.port
    if port is not None and port not in cfg.allowed_ports:
        raise UrlPolicyError("port_forbidden", f"Port {port} is not allowed")
    rule = host_allowed(host, cfg)
    if rule is None:
        raise UrlPolicyError("host_not_allowlisted", f"Host not on official allowlist: {host}")
    # Path/query kept; fragment stripped
    path = parsed.path or "/"
    query = parsed.query
    netloc = host if port is None or port == 443 else f"{host}:{port}"
    canonical = urlunparse(("https", netloc, path, "", query, ""))
    _ = allow_resolve_check  # DNS resolve reserved for fetcher with same checks
    return canonical


def validate_redirect_chain(urls: list[str], *, cfg: AllowlistConfig | None = None) -> str:
    cfg = cfg or load_allowlist()
    if not urls:
        raise UrlPolicyError("empty_chain", "Empty redirect chain")
    if len(urls) - 1 > cfg.max_redirects:
        raise UrlPolicyError("too_many_redirects", "Redirect limit exceeded")
    final = ""
    for u in urls:
        final = validate_url(u, cfg=cfg)
    return final


_JS_HINT = re.compile(r"<script[\s>]|javascript:", re.I)


def extract_text_no_js(raw: bytes, *, content_type: str, parser_version: str = "html.strip.v1") -> tuple[str, str]:
    """Extract plain text without executing JS. Returns (text, parser_version)."""
    _ = content_type
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    # Strip script blocks and tags naively — no JS runtime
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?i)javascript:", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, parser_version
