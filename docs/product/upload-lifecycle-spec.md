# Upload lifecycle and secure processing

- Status: Implemented (этап 5 scaffold)
- Spec aligns with ADR-0003, ADR-0007, TM-S1/S3/S4/S5/S10

## State machine

```
CREATED → UPLOADING → QUARANTINED → SCANNING → CLEAN → PROCESSING → READY
                                    ↘ REJECTED | INFECTED | FAILED
Any non-terminal → EXPIRED (retention) | DELETING → DELETED
```

| State | Meaning |
|-------|---------|
| CREATED | Upload intent issued; no bytes yet |
| UPLOADING | Client may PUT via single-purpose short-lived URL |
| QUARANTINED | Bytes received; not readable by app/user download |
| SCANNING | Malware scanner running |
| CLEAN | AV clean; format hardening next |
| PROCESSING | Sandboxed normalize/extract (no egress) |
| READY | Safe derived artifacts available |
| REJECTED | MIME/magic/size/extension/policy fail |
| INFECTED | Malware signature |
| FAILED | Processing error (retryable jobs are idempotent) |
| EXPIRED | Past retention; purge scheduled |
| DELETING / DELETED | Erasure in progress / done (tombstone) |

## Rules

1. Upload intent only for authenticated users within plan quotas.
2. Post-upload server validates size, extension, declared MIME, magic bytes, checksum. Allowlist: PDF, DOCX, JPEG, PNG.
3. Quarantine bucket/prefix is never served; processing starts only after CLEAN.
4. PDF: reject JS / Launch / EmbeddedFile / OpenAction heuristics; DOCX: zip-bomb, XXE, path traversal, external relationships; images: pixel/dimension caps.
5. Worker: no outbound network in sandbox mode; CPU/RAM/time limits enforced in process wrapper.
6. Storage keys are opaque UUIDs; display name is sanitized (control chars + bidi stripped) and never used as path/header key.
7. Envelope encryption: per-object DEK via KMS; destroy DEK on erasure. Presigned URLs: short TTL, single purpose (put vs get), bound to object.
8. Retention classes (config placeholders): `original`, `normalized_render`, `extracted_text`, `report`, `audit`. Scheduled purge + tombstone + verifiable delete of object/key/cache/derived.
9. Export excludes secrets, internal risk scores, other users' data.
10. Logs/APM/errors must not contain filename, extracted text, or quotes (see `SafeLogContext` / redacting filter).

## Plan limits (local defaults)

| Plan | Max uploads / day | Max size |
|------|-------------------|----------|
| free | 20 | 10 MiB |
| pro | 200 | 50 MiB |

Override via `PLAN_*` env when billing is real.
