# ADR-0006 — Неизменяемая PDF-подложка и coordinate maps

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

Пользователь должен видеть, **откуда** взялся fact (provenance), на визуале документа. DOCX/JPEG/PNG нужно привести к единому контуру отображения. Изменение underlay после анализа ломает координаты.

## Decision

1. После приёма файла pipeline строит **immutable PDF underlay** (конвертация/нормализация страниц).  
2. Underlay сохраняется как derived artifact с `content_hash`; перезапись запрещена (только новая версия job).  
3. **Coordinate map**: нормализованные координаты (page, bbox в underlay space) для spans сущностей.  
4. UI подсветки использует только underlay + maps; originals остаются для скачивания/споров о качестве.  
5. Если конвертация невозможна → `failed`/`needs_review`, без «плавающей» подсветки на нестабильном рендере.

## Alternatives

| Alternative | Why not |
|-------------|---------|
| Подсветка по «живому» PDF.js рендеру originals | Расхождение шрифтов/координат |
| Только текстовый отчёт без подсветки | Хуже trust и проверка фактов |
| Хранить screenshot PNG каждой страницы как underlay | Тяжелее storage; ок как fallback later |

## Consequences

- **+** Стабильный UX provenance (FR-11).  
- **+** Единый контур для сканов и DOCX.  
- **−** Стоимость конвертации и storage.  
- **−** Ошибки конвертера → отдельный failure mode.

## Links

FR-02/11; ADR-0003; AT-FR-11.
