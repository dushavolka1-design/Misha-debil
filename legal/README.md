# Legal artifacts

Versioned consent/policy bodies for «Анализатор документов РФ».

## Structure

- `manifest.json` — package status, approvals (lawyer / privacy officer), document index
- `placeholders.md` — tokens that must be filled before production
- `consents/<consent_id>/<version>.<locale>.md` — offer, terms, PD consent, medical, cookies, marketing, payment_recurring
- `policies/privacy_policy/...` — privacy policy (separate from consents)

## Rules

1. Documents stay **separate**; ordinary PD consent is never bundled with offer/terms.
2. Do **not** invent owner requisites — keep placeholders until real data is approved.
3. `publication_status` in manifest stays `draft` until lawyer + privacy officer approve and placeholders are filled.
4. Production boot requires `LEGAL_ROOT`, `manifest.status=approved`, both approvals, published docs, **zero** unresolved placeholders.
5. Users download the **exact** accepted version via `/legal/documents/{id}/text` and `/legal/events/{id}/proof` (hash match).

Local/test may seed draft texts for UX. CI asserts production gate **fails** on current drafts.
