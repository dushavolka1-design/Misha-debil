# ADR-0004 — Source registry и редакторское утверждение

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

Ссылки на нормы/правила/чеклисты въезда не должны браться «с живого интернета» в момент ответа модели. Нужен контролируемый реестр с версиями и review_status.

## Decision

Ввести **Source Registry**:

- сущности: source, source_snapshot (content_hash, captured_at), check_pack versions, form_version bindings;
- роли: редактор создаёт `draft` → `in_review`; утверждающий переводит в `approved` / `rejected` / `retired`;
- пользовательский анализ читает **только** `approved` snapshots;
- fetch новых материалов — через SSRF-safe fetcher (TM-S6), результат становится snapshot после review.

Four-eyes: один и тот же субъект не approve свои критичные изменения без override admin + audit (`FOUR_EYES_NEEDS_REVIEW`).

## Alternatives

| Alternative | Why not |
|-------------|---------|
| RAG напрямую по вебу | Нестабильность, SSRF, нет audit trail |
| Хардкод законов в репозитории | Медленные обновления, путаница версий |
| Пользователь сам вставляет «норму» | Риск injection и ложной легитимности |

## Consequences

- **+** Прослеживаемость: отчёт → snapshot ids.  
- **+** Снижение галлюцинаций «актуального закона».  
- **−** Операционная нагрузка на редакцию.  
- **−** Задержка публикации обновлений.

## Links

glossary source snapshot / review status; FR-04/10; TM-S6/S8; AT-FR-04, AT-THR-SSRF.
