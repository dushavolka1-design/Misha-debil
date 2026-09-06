# ADR-0003 — Исходники отдельно от извлечённого текста и отчёта

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

Original PDF/DOCX/JPEG/PNG — максимальная чувствительность. Extracted text нужен workers; report — пользователю. Совместное хранение повышает blast radius утечки и усложняет erasure/retention раздельно.

## Decision

Три класса артефактов в **разных** storage prefixes/buckets и ключах доступа:

1. **Original object** — immutable blob, minimal metadata, encryption key class `KEK_ORIGINALS`.  
2. **Extracted text / OCR layout** — derived store, key class `KEK_DERIVED`.  
3. **Report + coordinate maps refs** — user-facing artifacts, key class `KEK_REPORTS` (или derived с отдельной ACL).

API выдаёт пользователю report; original — только через signed URL с TTL и authz. Workers получают short-lived scoped credentials.

## Alternatives

| Alternative | Why not |
|-------------|---------|
| Один bucket «всё подряд» | Проще ops, хуже blast radius и erasure |
| Хранить только extracted, originals удалять сразу | Ломает underlay/coordinate UX и споры о качестве OCR |
| Держать originals в DB bytea | Дорого, плохо для malware isolation |

## Consequences

- **+** Соответствует FR-01; упрощает crypto-erasure по классам.  
- **+** Логи могут ссылаться на IDs без текста.  
- **−** Сложнее транзакционная согласованность «всё создано».  
- **−** Нужны GC/orphan cleaners.

## Links

FR-01; TM-S4/S10; AT-FR-01, AT-THR-RECOVERY; ADR-0006, ADR-0007.
