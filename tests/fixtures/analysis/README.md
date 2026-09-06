# Golden analysis fixtures

These are **logical** fixture ids consumed by `FakeOCRProvider` (deterministic layout/OCR).
Binary placeholders may be generated for packaging; content markers select the fixture.

| Id | Description |
|----|-------------|
| `digital_pdf` | Native-text PDF lease contract |
| `scan` | Scanned sale contract |
| `rotated_scan` | Page rotation=90 |
| `table` | Pipe-table specification |
| `docx` | NDA-like DOCX text |
| `poor_quality` | Low confidence + page 2 OCR failure (visible error) |
| `mixed_script` | Russian + Latin mixed |

Expected fields for metrics live in `expected.json`.
