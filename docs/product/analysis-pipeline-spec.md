# Analysis pipeline (OCR, layout, traceable facts)

- Spec for этап 6. Aligns with ADR-0002, ADR-0006, taxonomy core entities.

## Pipeline stages

`queued → normalizing → ocr → layout → extracting → ready | failed`

Progress events carry stage/percent/page/error_code only — never document text.

## Versions

| Component | Constant |
|-----------|----------|
| Pipeline | `analysis.pipeline.v1` |
| Prompt | `facts.extract.v1` |
| Finding schema | `finding_schema.v1` |
| OCR/LLM adapters | provider `model_version` |

Re-analysis always creates a **new** `AnalysisRun`.

## Findings

Every fact requires `citation{page,bbox,quote}`. `raw_text` and `normalized_value` are separate. Schema rejects additional properties; invalid LLM payloads are rejected, not repaired.

## Normalizers

Deterministic format/checksum only for dates, money, ИНН, ОГРН/ОГРНИП, СНИЛС. No ownership or validity claims.

## Golden fixtures (`fixture_id`)

`digital_pdf`, `scan`, `rotated_scan`, `table`, `docx`, `poor_quality`, `mixed_script` — served by `FakeOCRProvider`.
