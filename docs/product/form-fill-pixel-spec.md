# Pixel-perfect заполнение официального PDF

Статус: этап 11. Подложка immutable; текст только в утверждённых bbox.

Связано: [forms-and-medical-spec.md](forms-and-medical-spec.md), ADR-0006, AT-FR-11.

---

## 1. FormVersion (immutable)

| Поле | Назначение |
|------|------------|
| `original_pdf` + `original_hash` | Официальный PDF; hash проверяется до генерации |
| `page_geometry` | MediaBox/CropBox/Rotate на страницу |
| `coord_map` + `coord_map_version` + `coord_map_hash` | Карта полей |
| `allowed_fonts` + hashes + license | Только разрешённые шрифты |
| `field_schema` | Типы/форматтеры |
| `valid_from` / `valid_to` | Effective interval |
| `review_status` | draft → awaiting_second_review → published / rejected |

Публикация coordinate map — **four-eyes** (author ≠ second reviewer).

---

## 2. Coordinate map field

`field_id`, `page`, `bbox` [x0,y0,x1,y1] в PDF user space, `baseline`, `font`, `size`, `alignment`, `max_chars`, `max_lines`, `alphabet`/`regex`, `formatter`, `overflow_strategy` (`clip`|`reject`|`wrap` — без shrink-to-fit), `value_source`, `user_editable`, `required`, `prohibited_auto_fill`, `reserved_for` (`signature`|`stamp`|`organ`|null`).

Поля `signature`/`stamp` никогда не заполняются движком.

---

## 3. Генератор

1. Verify `original_hash`.
2. Clone pages (pypdf) — content streams подложки **не** переписываются.
3. Merge overlay text layer только в bbox разрешённым шрифтом.
4. Не rasterize/reflow подложки; точки, линии, labels, metadata source сохраняются.
5. Overflow: `reject` или `clip`/`wrap` внутри bbox; **запрещён** shrink шрифта до нечитаемого.

---

## 4. Preview / audit

Preview: длина, запрещённые символы, перенос, пустые required, manual/organ fields.

`GeneratedForm`: hashes template/map/input/output, `engine_version`, audit; пользователь может удалить.

Новая редакция official source → старая FormVersion `blocked_for_new`; ранее созданные GeneratedForm остаются доступны.

---

## 5. Pixel diff (CI)

Рендер original/output при одном DPI; mask = утверждённые fillable bboxes; вне mask diff≈0; внутри — baseline/clipping; page box / page count / static text extraction. Отчёт — CI artifact.
