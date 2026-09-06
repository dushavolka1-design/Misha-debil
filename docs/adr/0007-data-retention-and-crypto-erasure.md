# ADR-0007 — Data retention и crypto-erasure

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

Нужны удаление аккаунта и прекращение доступа к данным. Конкретные календарные сроки retention **не фиксируем** (`RETENTION_*_NEEDS_REVIEW`). Soft-delete недостаточен против backup restore (TM-S10).

## Decision

1. Политика retention задаётся конфигом/legal pack с placeholders; продукт читает сроки из конфигурации, не из хардкода ТЗ.  
2. Удаление аккаунта / объектное erasure:  
   - revoke signed URLs;  
   - stop jobs;  
   - уничтожение DEK (data encryption keys) для originals/derived (**crypto-erasure**);  
   - пометка объектов `erased`;  
   - audit события.  
3. Backups используют иерархию ключей, согласованную с erasure; restore не «воскрешает» стёртые DEK без legal hold.  
4. **Legal hold** (`LEGAL_HOLD_POLICY_NEEDS_REVIEW`) может задержать физическое/криптографическое уничтожение; пользователю показывается `partial_hold`, не тишина.  
5. Минимальные billing/compliance stubs без содержимого документа — по отдельной схеме (`BILLING_STUB_SCHEMA_NEEDS_REVIEW`).

## Alternatives

| Alternative | Why not |
|-------------|---------|
| Только soft-delete строк БД | Данные остаются в object storage/backups |
| Немедленный overwrite GC без ключей | Медленно/ненадёжно на больших blobs; хуже для backups |
| Вечное хранение «на всякий случай» | Противоречит privacy целям и UC-ACCOUNT-DELETE |

## Consequences

- **+** Проверяемый AT-THR-RECOVERY / AT-FR-09.  
- **+** Не выдумываем нормативные сроки в ADR.  
- **−** Сложность key management.  
- **−** Нужны регулярные restore drills.

## Links

UC-ACCOUNT-DELETE; FR-09; TM-S10/TM-L7; ADR-0003/0005; decision-log DL-002..004.
