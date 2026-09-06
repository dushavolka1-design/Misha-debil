# Official source policy

- Status: Binding for этап 8
- Related: ADR-0004, TM-S6

## Principles

1. **Deny by default.** Only hosts on the machine-readable allowlist may be fetched or cited as official.
2. **No norms from model memory.** Seed registry with official **domain metadata** only. Act texts, numbers, effective dates enter the system only via fetched+reviewed snapshots.
3. **Production claims and forms** may bind only to `approved` snapshots.
4. **Temporal applicability.** Every legal record has `valid_from` / `valid_to`. Do not auto-apply the current edition to a historical event date.
5. **No JavaScript execution** when parsing source pages.
6. **Broken/stale links stay visible** as marked degraded — never silently dropped.

## URL validation (allowlist)

- Scheme: `https` only
- Host: exact match or explicit subdomain rule from allowlist; IDN → punycode
- No `userinfo` (`user:pass@`)
- No private/reserved/link-local IPs (literal or resolved)
- Standard port only (`443` or omitted)
- Redirects: each hop re-validated; leaving allowlist = reject
- Max redirect count enforced

## Source lifecycle

`discovered → fetched → parsed → awaiting_review → approved → superseded | expired | rejected`

Hash change of a new snapshot vs last approved → create review task; dependents (norms/forms) move to `review`.

## Fetcher

Separate component: egress allowlist, rate/robots policy hooks, max size/type, SSRF protection, conditional requests (`If-None-Match` / `If-Modified-Since`).

## Snapshot immutability

Store: raw bytes, response headers, `fetched_at`, final URL, SHA-256, extracted text, parser version. Raw is never rewritten.

## Citation

User-facing citation must include: organ, document title, number/date (when present on snapshot), quote, official URL, verified flag, applicable-on date.
