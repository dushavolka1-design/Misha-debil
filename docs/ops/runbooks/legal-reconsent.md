# Runbook: Legal re-consent

1. Publish new legal document version (append-only); never mutate published text.
2. Bump `consent_version` / content_hash; feature gates require re-accept for material changes.
3. Preserve export/delete without forcing new offer accept (product rule).
4. Email/in-app notice with link to diff summary (human-written, LegalReview).
5. Monitor `consent_required` error rate; support macros for “как принять новую версию”.
6. Payment recurring: separate consent — never bundle with offer/PD.
