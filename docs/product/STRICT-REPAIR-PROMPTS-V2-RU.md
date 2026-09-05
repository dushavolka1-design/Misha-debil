# Строгие промпты исправления Docly — версия 2

Репозиторий:

`C:\Users\GariPotov1\Projects\document-analyzer-rf`

Выполнять по одному промпту строго по порядку. После каждого промпта приложение должно запускаться, а относящиеся тесты — проходить. Запрещено переходить к следующему этапу, маскируя ошибку заглушкой.

## Факты повторного аудита

1. Ярлык `Docly.lnk` запускает `scripts/windows/start-dar.ps1`, но последний запуск остановился после записи `starting bundled postgres/redis`.
2. `infra/portable/pgsql` и `infra/portable/redis` пусты; остался `redis.zip`, сервисные порты не слушаются.
3. Первый запуск зависит от скачивания около 300 МБ PostgreSQL и отдельного архива Redis. Ошибка происходит в скрытом окне и воспринимается как отсутствие запуска.
4. API каталога падает:
   `AttributeError: 'dict' object has no attribute 'status'`.
   Generic persistence загружает `form_catalog.forms` как словари вместо `FormRecord`.
5. Генератор не может получить каталог, когда API не работает, и поэтому показывает только ошибку соединения.
6. В `fill/assets` нет файла `NotoSans-Regular.ttf`; `expected_sha256` в manifest равен `null`.
7. Seed публикует синтетическую A4-подложку уведомления о прибытии, хотя это не официальный бланк МВД.
8. Body использует размер `0.9375rem` и обычный вес шрифта; большинство вспомогательного текста ещё меньше. Интерфейс визуально слишком тонкий и пустой.
9. Большая часть экранов состоит из белых прямоугольников, тонких рамок и текста. Визуальной иерархии, иконок, плотной композиции и выразительных состояний почти нет.
10. Две основные вкладки уже появились. Их необходимо сохранить: «Анализатор» и «Генерация».

---

# Промпт 0. Непереговорные правила

```text
Ты исправляешь существующий продукт Docly, а не создаёшь новый макет рядом.

Рабочий каталог:
C:\Users\GariPotov1\Projects\document-analyzer-rf

Запрещено:
- объявлять задачу выполненной без запуска через реальный desktop shortcut;
- заменять ошибку API пустым массивом;
- использовать fixture/demo как результат пользовательского действия;
- публиковать синтетическую подложку как официальную форму;
- автоматически ставить статус published без approved official source;
- оставлять кнопку, которая визуально работает, но не вызывает backend;
- сохранять dataclass-объекты как dict и потом передавать их в доменный сервис без восстановления типа;
- требовать Docker, установленный PostgreSQL, Redis, глобальный pnpm или ручной запуск терминалов для desktop-режима;
- скачивать сотни мегабайт в скрытом окне без прогресса, отмены и понятной ошибки;
- использовать тонкий основной текст меньше 16 px;
- использовать emoji вместо единого набора SVG-иконок;
- показывать внутренние слова raw, fixture, fill version, needs_review, approved;
- ослаблять правила персональных данных и медицинских документов.

Обязательный порядок работы:
1. Сначала воспроизведи проблему.
2. Напиши regression test, который падает на текущем коде.
3. Исправь корневую причину.
4. Выполни tests.
5. Запусти приложение через ярлык.
6. Сделай screenshots и приложи их к отчёту.

Любой этап завершается только отчётом:
- изменённые файлы;
- команды;
- результаты тестов;
- screenshot paths;
- что осталось неработающим;
- GO или NO-GO.

Если хотя бы один критерий этапа не выполнен — результат NO-GO.
```

---

# Промпт 1. Сделать запуск с ярлыка гарантированно рабочим

```text
Примени Промпт 0. Исправь desktop-запуск прежде любых изменений дизайна.

Текущая проблема:
- Docly.lnk запускает скрытый PowerShell;
- launcher зависает/завершается на Ensure-BundledDatabase;
- portable PostgreSQL/Redis загружаются при первом старте;
- пользователь не видит прогресс;
- папки binaries остаются пустыми;
- icon shortcut указывает на отсутствующий docly-icon.ico.

Цель: двойной клик открывает полностью рабочий Docly максимум за 15 секунд после завершённой установки и показывает понятный первый запуск.

1. Создай отдельные режимы:
   - `desktop`: автономная локальная программа;
   - `development`: текущий dev stack;
   - `production`: PostgreSQL/Redis/российские providers.
2. Desktop-режим не должен зависеть от Docker, внешнего PostgreSQL и Redis.
3. Для desktop используй:
   - встроенную SQLite через SQLAlchemy/Alembic;
   - локальную durable job queue в той же БД;
   - файловое object storage внутри `%LOCALAPPDATA%\Docly\data`;
   - локальный lifecycle worker как отдельный дочерний процесс или безопасную background task.
4. Production PostgreSQL/Redis оставь отдельным профилем. Не меняй production на SQLite.
5. Удали обязательное скачивание PostgreSQL/Redis из обычного ярлыка. `setup-portable-db.ps1` не должен запускаться в desktop profile.
6. Добавь setup/build script, который заранее подготавливает:
   - Python runtime либо проверенный project venv;
   - зависимости API;
   - production build Next.js;
   - локальные fonts/assets;
   - SQLite migrations.
7. Не запускай `next dev` из пользовательского ярлыка. Для desktop используй стабильный production build (`next start`) либо упакованную desktop shell.
8. Сделай видимое окно запуска Docly:
   - логотип;
   - этапы «Проверка файлов», «Запуск хранилища», «Запуск сервиса», «Открытие приложения»;
   - progress indicator;
   - кнопка «Показать подробности»;
   - кнопка «Повторить»;
   - кнопка «Скопировать диагностику».
9. Ошибки выводи по-русски. Окно не должно исчезать само при ошибке.
10. Добавь lock, запрещающий параллельный запуск нескольких launcher.
11. Не убивай произвольный процесс на порту 3000/8000. Если порт занят чужой программой:
    - выбери свободный порт;
    - передай его web/API;
    - открой правильный URL.
12. Проверяй принадлежность уже запущенного процесса через service identity endpoint с instance token.
13. Shortcut:
    - пересоздай `Docly.lnk`;
    - проверь Target, Arguments, WorkingDirectory;
    - добавь реально существующий `.ico`;
    - исключи устаревшие ярлыки;
    - shortcut smoke test обязан прочитать lnk и проверить все пути.
14. Добавь `scripts/windows/doctor.ps1`, который ничего не исправляет молча, а проверяет:
    - Node/runtime;
    - Python/runtime;
    - build;
    - writable data directory;
    - SQLite migration;
    - API start;
    - web start;
    - свободные/выбранные ports;
    - шрифты и шаблоны.
15. После старта браузер открывается только когда `/live`, `/ready` и web возвращают 200.

Автоматические тесты:
- clean desktop profile без Docker/PostgreSQL/Redis;
- offline повторный запуск;
- первый запуск;
- второй запуск;
- уже работающий Docly;
- занятые 3000/8000;
- отсутствующий build;
- повреждённая SQLite;
- путь с пробелами и кириллицей;
- ярлык содержит существующие target/icon/working directory;
- shutdown не оставляет orphan processes.

Критерии приёмки:
- Двойной клик по Docly.lnk запускает приложение без терминала и ручных действий.
- Docker, PostgreSQL и Redis отсутствуют — приложение всё равно запускается.
- Нет скрытого скачивания 300 МБ.
- При ошибке пользователь видит причину и кнопку исправления/повтора.
- После перезагрузки Windows данные сохраняются.
- Полный launcher e2e test зелёный.
```

---

# Промпт 2. Починить API, persistence и каталог форм

```text
Примени Промпт 0. Исправь текущий backend crash до работы над генератором.

Подтверждённая ошибка:
FormCatalogService.list_forms ожидает FormRecord, но получает dict после восстановления persistence:
AttributeError: 'dict' object has no attribute 'status'.

1. Добавь regression test:
   - записать восемь FormRecord;
   - остановить приложение;
   - поднять приложение;
   - вызвать GET /forms;
   - получить восемь валидных карточек без 500.
2. Исправь `_blob_store_specs`/`_deserialize_store`:
   - для forms использовать явный FormRecord serializer/deserializer;
   - восстановить UUID;
   - datetime/date;
   - enums/status;
   - source_snapshot_id;
   - fill_version_id;
   - raw bytes;
   - by_slug.
3. После загрузки проверяй invariants:
   - ключ dict равен FormRecord.id;
   - by_slug ссылается на существующий FormRecord;
   - fill_version_id ссылается на существующую version;
   - source_snapshot_id существует либо форма не published.
4. Не проглатывай persistence exception через warning и продолжение с частично повреждённым store.
   Для обязательного каталога readiness должен стать failed с понятным error code.
5. Создай миграцию/repair command для уже сохранённых `app_state_blobs`:
   - backup;
   - validate;
   - convert;
   - rollback при ошибке.
6. Удали смешение write-through dict и неотслеживаемых изменений полей dataclass.
   Изменение `rec.fill_ready`, `rec.status`, `rec.fill_version_id` должно сразу атомарно сохраняться.
7. Для desktop используй нормальные repository methods и transactions, а не сериализацию всего каталога одним JSON blob.
8. Добавь API contract tests:
   - `/forms`;
   - `/forms/{id}`;
   - `/forms/fill/by-catalog/{id}`;
   - `/forms/fill/preview`;
   - `/forms/fill/generate`;
   - generated PDF download;
   - restart between every major step.
9. Ошибка одной повреждённой записи не должна превращать весь каталог в пустой экран. Покажи admin diagnostic и изолируй запись.
10. `/ready` проверяет не только соединение с БД, но и возможность загрузить типизированный каталог.

Критерии приёмки:
- GET /forms не возвращает 500 после restart.
- В domain stores нет dict вместо dataclass/model.
- Восемь карточек видны после restart.
- Generated documents и drafts сохраняются.
- Ошибка persistence имеет стабильный русский user message и технический correlation ID.
```

---

# Промпт 3. Сделать генерацию настоящей и убрать опасные подделки

```text
Примени Промпт 0. Полностью исправь генерацию документов.

Критические текущие проблемы:
- NotoSans-Regular.ttf отсутствует;
- expected_sha256 отсутствует;
- генерация seed молча пропускается по FileNotFoundError;
- `seed_arrival_notice_published()` создаёт синтетическую A4-подложку;
- synthetic underlay получает review_status=published;
- source_snapshot_id отсутствует;
- карточка может стать fill_ready даже при status=needs_review.

1. Немедленно запрети генерацию государственной формы, если:
   - catalog status не `published`;
   - source snapshot не `approved`;
   - source_snapshot_id отсутствует;
   - официальный raw PDF отсутствует;
   - hash не совпадает;
   - act metadata неполны;
   - coordinate map не approved двумя редакторами;
   - font/hash/license отсутствуют;
   - форма superseded/stale.
2. Удали `seed_arrival_notice_published` с синтетической подложкой из пользовательского runtime.
3. Синтетическую подложку оставь только в tests с явным slug `test.synthetic.*`.
4. Не называй synthetic PDF «официальной подложкой» и не показывай его пользователю.
5. Для уведомления о прибытии:
   - найди действующую редакцию только на официальном российском источнике;
   - сохрани официальный файл без изменений;
   - сохрани URL, орган, акт, приложение, даты, hash;
   - отправь в editorial review;
   - попроси человека подтвердить визуальное соответствие;
   - только после двух approvals создай coordinate map и опубликуй.
6. Не используй коммерческие базы, случайные PDF, блоги или AI-память.
7. Для остальных семи карточек:
   - честный статус;
   - кнопка заполнения только после полного approval;
   - до approval доступен понятный checklist, но не поддельный бланк.
8. Медицинская памятка:
   - отдельный собственный шаблон;
   - крупная маркировка на каждой странице;
   - не является справкой/заключением;
   - не содержит печати, подписи, QR, номера учреждения и диагноза.
9. Шрифт:
   - добавь Noto Sans или другой OFL-шрифт в repository/distribution;
   - добавь LICENSE;
   - зафиксируй реальный SHA-256;
   - build проверяет hash;
   - launcher проверяет наличие;
   - отсутствие шрифта делает `/ready` failed для generation capability с понятной диагностикой.
10. Не используй Arial/system fallback для pixel-perfect результата.
11. Исправь `FormFillClient`:
   - все запросы credentials include;
   - проверка `res.ok` до JSON assumptions;
   - network timeout;
   - retry;
   - error boundary;
   - preview PDF не в маленьком iframe 360 px, а в полноценном responsive viewer;
   - пошаговая форма;
   - sticky actions;
   - подсветка обязательных/ручных полей;
   - автосохранение черновика.
12. Исправь sequencing:
   - `openDownloadDialog` обязан дождаться preview;
   - если preview failed, pre-download не вызывается;
   - generated download доступен только владельцу;
   - PDF download отдаёт корректный filename и content disposition.
13. Pixel-perfect tests:
   - byte/hash official underlay;
   - page boxes;
   - masked pixel diff;
   - static text diff;
   - font embedded;
   - clipping/overflow;
   - длинные ФИО/адреса;
   - кириллица/латиница;
   - печать на A4.
14. Сделай capability endpoint:
   - catalog_ready;
   - fill_engine_ready;
   - font_ready;
   - official_templates_count;
   - generation_ready.
   UI показывает конкретную причину, а не общее «API не работает».

Критерии приёмки:
- Нельзя создать ни одной государственной формы на synthetic underlay.
- Уведомление генерируется только после реального official source approval.
- При отсутствии approved формы пользователь видит checklist, а не fake PDF.
- Шрифт встроен, hash зафиксирован.
- Fill → preview → validate → generate → download работает после restart.
- Pixel diff не меняет статическую часть формы.
```

---

# Промпт 4. Полностью переделать визуальный дизайн и типографику

```text
Примени Промпт 0. Проведи полноценный визуальный редизайн, а не замену нескольких цветов.

Сохрани светлую тему и ровно два верхних раздела:
- Анализатор;
- Генерация.

Новый стиль: современный premium legal-tech, уверенный, чистый, визуально насыщенный, но не похожий на государственный портал.

1. Типографика:
   - один основной локальный кириллический variable font: Onest либо Golos Text;
   - никакой загрузки Google Fonts при runtime;
   - body: 16 px, weight 500, line-height 1.55;
   - secondary: минимум 14 px, weight 500;
   - labels/buttons/nav: 14–16 px, weight 600;
   - H1: 40/44 desktop, 30/36 mobile, weight 700;
   - H2: 28/34, weight 700;
   - H3: 20/26, weight 650–700;
   - не использовать Unbounded для длинных заголовков;
   - mono только для hash/ID в раскрываемых технических подробностях.
2. Удали визуальную «тонкость»:
   - text color не светлее #475569 для обычного вторичного текста;
   - border минимум различим на #CBD5E1;
   - кнопки имеют чёткую высоту 44–48 px;
   - интерактивные элементы имеют уверенный font-weight.
3. Дизайн-токены:
   - фон страницы: мягкий холодный #F4F7FB;
   - surface: #FFFFFF;
   - primary ink: #111827;
   - accent: насыщенный сине-фиолетовый;
   - отдельные semantic colors;
   - radius 14–20 px;
   - многослойные, но мягкие shadows;
   - spacing scale 4/8/12/16/24/32/48/64.
4. Подключи единый набор SVG-иконок, например Lucide.
   Удали emoji 📄, ✍️ и случайные символы.
5. Header:
   - логотип нормального размера;
   - две крупные segmented tabs;
   - активный раздел хорошо заметен;
   - avatar/menu;
   - тонкая тень при scroll;
   - высота 72 px desktop.
6. Landing:
   - сильный hero с двумя колонками;
   - выразительная иллюстрация процесса документа без гербов;
   - короткий заголовок;
   - главный CTA и secondary CTA;
   - две продуктовые карточки с иконками, преимуществами и hover;
   - trust strip;
   - три шага в карточках, не просто цифры и текст;
   - security block с визуальными badges;
   - финальный CTA;
   - max-width 1280;
   - не оставлять большие бесцельные промежутки.
7. Анализатор:
   - заметная hero-card upload;
   - dropzone с иконкой, состояниями drag/selected/scanning/error;
   - карточки последних документов;
   - progress timeline;
   - метрики результата;
   - risk cards с приоритетом;
   - split document viewer выглядит как рабочее пространство, не пустой лист.
8. Генерация:
   - grid карточек 3 колонки desktop, 2 tablet, 1 mobile;
   - у категории свой спокойный цвет/icon;
   - статус формы оформлен badge;
   - карточка содержит назначение, орган, дату проверки и действие;
   - поисковая строка с иконкой;
   - category chips;
   - skeleton cards;
   - красивое пустое состояние;
   - отдельный banner capability, если backend недоступен.
9. Убери большой повторяющийся onboarding-блок с четырьмя bullet на каждом экране.
   Замени компактной contextual help card или collapsible «Как это работает».
10. Панели:
    - не все блоки должны выглядеть одинаковой белой коробкой;
    - используй hierarchy: hero surface, cards, inset panels, tinted callouts;
    - избегай inline styles — перенеси всё в компоненты/variants.
11. Добавь состояния:
    - hover;
    - active;
    - pressed;
    - disabled;
    - loading;
    - success;
    - warning;
    - error;
    - empty;
    - offline.
12. Добавь тонкие анимации 150–220 ms, соблюдая reduced motion.
13. Accessibility:
    - WCAG 2.2 AA;
    - focus ring;
    - keyboard;
    - 200% zoom;
    - screen reader labels;
    - target size минимум 44×44.
14. Не копируй Госуслуги и не используй государственную символику.
15. Создай Storybook страницы:
    - Typography;
    - Colors;
    - Buttons;
    - Cards;
    - TemplateCard;
    - UploadZone;
    - Progress;
    - DocumentViewer;
    - Empty/Error states.

Visual acceptance:
- 360×800;
- 768×1024;
- 1440×1000;
- 1920×1080;
- light Windows scaling 125% и 150%.

Критерии приёмки:
- Основной текст визуально не тонкий и не меньше 16 px.
- Интерфейс больше не выглядит как набор пустых белых блоков.
- На первом экране Анализатора и Генерации есть понятная визуальная иерархия.
- Нет emoji и случайных inline styles.
- Ровно две основные вкладки сохранены.
- Screenshots утверждены человеком до обновления visual snapshots.
```

---

# Промпт 5. Довести Analyzer и Generator до законченных пользовательских сценариев

```text
Примени Промпт 0. После исправления startup/backend/design заверши пользовательские сценарии.

Анализатор:
1. Новый анализ:
   - реальный файл;
   - реальный upload lifecycle;
   - scan;
   - extraction/OCR;
   - progress;
   - report.
2. Не показывай успешный анализ, если LLM недоступна.
   Отдельно покажи локально выполненные функции и недоступный расширенный анализ.
3. Мои документы используют API/SQLite, а не fixtures.
4. Сравнение использует реальные results и ownership check.
5. Feedback вызывает backend.
6. Удаление очищает производные данные.

Генератор:
1. Каталог загружается после старта без 500.
2. Восемь карточек всегда имеют честный статус.
3. Search не вызывает API на каждый символ без debounce/cancel.
4. Мастер рекомендует применимые формы и объясняет почему.
5. Созданные документы загружаются из durable storage.
6. Ошибки разделяй:
   - backend недоступен;
   - каталог повреждён;
   - шаблон не утверждён;
   - шрифт отсутствует;
   - поля невалидны;
   - генератор временно недоступен.
7. Не показывай кнопку «Заполнить», если полный e2e generation невозможен.
8. Если доступен checklist, сделай его полезным:
   - список шагов;
   - документы;
   - официальный источник;
   - дата проверки;
   - export в обычный информационный PDF с маркировкой.

Общие требования:
- session/auth работает после desktop restart;
- API client единый и типизированный;
- credentials include в защищённых запросах;
- timeout/retry/cancel;
- toast только после реального ответа;
- correlation ID в ошибке;
- русский язык без внутренних терминов.

Критерии приёмки:
- Fresh install → ярлык → регистрация → анализ synthetic test PDF → результат.
- Fresh install → ярлык → Генерация → восемь карточек.
- Approved test template → fill → preview → PDF → restart → история → повторное скачивание.
- Unapproved government template никогда не генерируется.
```

---

# Промпт 6. Жёсткая финальная приёмка

```text
Примени Промпт 0. Проведи финальную приёмку на чистой Windows-машине или чистом Windows user profile.

Не используй уже запущенные dev-процессы, установленный вручную PostgreSQL/Redis или состояние разработчика.

Обязательные тесты:

Startup:
1. Docly.lnk существует и имеет валидные target, working directory, icon.
2. Docker отсутствует.
3. PostgreSQL/Redis отсутствуют.
4. Интернет отключён после установки.
5. Первый и повторный запуск успешны.
6. Заняты 3000/8000 — Docly выбирает другие порты.
7. Повторный двойной клик не создаёт дубликаты.
8. Закрытие корректно завершает дочерние процессы.

Backend:
9. SQLite migrations с нуля.
10. Restart persistence.
11. GET /forms после restart.
12. Ни одного dict вместо domain record.
13. Corrupt catalog record isolation.

Generator:
14. Восемь карточек.
15. Честные статусы.
16. Нет synthetic government underlay в пользовательском runtime.
17. Font exists/hash/license.
18. Approved form full flow.
19. Unapproved form blocked.
20. Medical certificate direct API blocked.
21. Pixel diff.

Analyzer:
22. Upload реального synthetic PDF.
23. Результат зависит от его содержимого.
24. Citation соответствует странице.
25. Restart сохраняет результат.
26. Compare и feedback работают.

Visual:
27. Body computed font-size >= 16 px.
28. Body computed font-weight >= 500.
29. Secondary important text >= 14 px / 500.
30. Две основные вкладки.
31. Нет sidebar.
32. Нет emoji.
33. Нет horizontal overflow.
34. Axe без serious/critical.
35. Visual screenshots 360, 768, 1440, 1920.

Security:
36. IDOR.
37. CSRF.
38. Upload MIME/magic.
39. Prompt injection.
40. Logs не содержат документ.
41. Generated PDF доступен только владельцу.

Сформируй итоговую таблицу:
- ID теста;
- статус;
- команда;
- evidence path;
- issue ID при провале.

Автоматический NO-GO:
- ярлык не запускает приложение;
- startup требует Docker/PostgreSQL/Redis;
- API /forms возвращает 500;
- каталог исчезает после restart;
- генерация использует synthetic government form;
- отсутствует font/hash/license;
- основной шрифт тоньше 500 или меньше 16 px;
- дизайн не прошёл screenshot review;
- есть неработающая кнопка;
- fixture показан как реальный результат;
- опубликованная форма не имеет approved official source;
- pixel diff меняет подложку.

Не писать «готово», если результат NO-GO. Верни точный список блокеров и продолжай исправление до GO.
```

## Как применять

1. Передай Cursor Промпт 0.
2. Выполни Промпт 1 и лично проверь ярлык.
3. Выполни Промпт 2 и проверь `/forms` после перезапуска.
4. Выполни Промпт 3 и вручную проверь официальный источник/подложку.
5. Только затем выполняй визуальный редизайн из Промпта 4.
6. Заверши сценарии Промптом 5.
7. Промпт 6 выполняется на чистом окружении.
