# ADR-0005 — Модель согласий

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

Обработка документов, передача в AI/OCR adapters и смена процессоров требуют доказуемого согласия без выдуманных нормативных сроков. Тексты политик версионируются.

## Decision

Модель **consent_version**:

1. Каждый юридически значимый текст согласия имеет `consent_id` + `consent_version` + `content_hash` + `effective_from`.  
2. Пользовательское принятие хранится как evidence record: user, version, accepted_at, channel; детали IP/device — по `DL-010`.  
3. **Consent gate**: OCR/analyze job не создаётся без актуальных обязательных consent_version.  
4. При публикации новой обязательной версии — re-consent до продолжения обработки; старые отчёты остаются читаемы по политике (`RECONSENT_READ_POLICY_NEEDS_REVIEW`).  
5. Отзыв/удаление аккаунта инициирует прекращение обработки + erasure workflow (ADR-0007).

Отдельно версионируются purpose: `processing_core`, `processor_ai_ocr`, `marketing` (marketing вне MVP core — `deferred`).

## Alternatives

| Alternative | Why not |
|-------------|---------|
| Один вечный чекбокс «согласен» | Не покрывает смену процессора/текста |
| Consent только в UI без серверной проверки | Обход API |
| Не хранить evidence | Слабая доказуемость для privacy officer |

## Consequences

- **+** Трассируемость и принудительный gate.  
- **+** Совместимо с glossary.  
- **−** UX friction при обновлениях.  
- **−** Нужна аккуратность с минимизацией evidence (LINDDUN L3).

## Links

FR-08/09; TM-L5/L7; AT-FR-08; decision-log DL-010.
