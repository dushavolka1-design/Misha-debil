# Source registry working files

Policy: [docs/product/official-source-policy.md](../docs/product/official-source-policy.md)

- `allowlist.json` — machine-readable official hosts only (metadata). Deny by default.
- Do **not** store invented norms, deadlines, or act texts here from model memory.
- Editorial drafts and approved snapshot blobs may live under object storage; DB tracks lifecycle.

Only `lifecycle_state=approved` snapshots may back production assertions or forms (ADR-0004).
