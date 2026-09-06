"""Official egress fetcher — tests inject FakeFetcher; production uses httpx with same policy."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.sources.registry import FetchResult
from app.services.sources.url_policy import UrlPolicyError, load_allowlist, validate_url


@dataclass
class FakeFetchScript:
    """Deterministic responses keyed by URL prefix."""

    responses: dict[str, FetchResult]
    calls: list[tuple[str, dict[str, str]]] | None = None

    def __call__(self, url: str, headers: dict[str, str]) -> FetchResult:
        if self.calls is not None:
            self.calls.append((url, headers))
        # Exact then prefix
        if url in self.responses:
            return self.responses[url]
        for key, resp in self.responses.items():
            if url.startswith(key):
                return resp
        return FetchResult(
            final_url=url,
            status_code=404,
            headers={},
            body=b"",
            redirect_chain=[url],
        )


def guarded_httpx_fetch(url: str, headers: dict[str, str]) -> FetchResult:
    """Production-shaped fetcher: validate URL before egress; re-check redirects."""
    import httpx

    cfg = load_allowlist()
    canonical = validate_url(url, cfg=cfg)
    chain = [canonical]
    with httpx.Client(follow_redirects=False, timeout=20.0) as client:
        current = canonical
        req_headers = dict(headers)
        body = b""
        status = 0
        resp_headers: dict[str, str] = {}
        for _ in range(cfg.max_redirects + 1):
            resp = client.get(current, headers=req_headers)
            status = resp.status_code
            resp_headers = {k: v for k, v in resp.headers.items()}
            if status in {301, 302, 303, 307, 308}:
                loc = resp.headers.get("location")
                if not loc:
                    raise UrlPolicyError("redirect_missing_location", "Redirect without Location")
                # Resolve relative
                next_url = str(httpx.URL(current).join(loc))
                next_url = validate_url(next_url, cfg=cfg)
                chain.append(next_url)
                current = next_url
                continue
            body = resp.content
            break
        else:
            raise UrlPolicyError("too_many_redirects", "Redirect limit exceeded")
    return FetchResult(
        final_url=current,
        status_code=status,
        headers=resp_headers,
        body=body,
        redirect_chain=chain,
    )
