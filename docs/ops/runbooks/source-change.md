# Runbook: Official source change

1. Detect: fetcher hash/mismatch, editor report, or upstream notice.
2. Mark affected snapshots `needs_review`; **stop** serving to user analysis/forms/entry.
3. Capture new snapshot via allowlisted fetcher; store hash + retrieved_at.
4. LegalReview / editor four-eyes approve before publish.
5. Re-run entry/forms regression; update decision pack if rules depend on text.
6. Communicate to users only if product UX depended on withdrawn text — no legal advice.

If source disappears: keep last approved snapshot with explicit staleness warning; never invent replacement norms.
