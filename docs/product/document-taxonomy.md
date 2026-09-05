# Таксономия документов и схема проверок

Статус: этап 1. Расширяемая модель: новые типы и check packs добавляются без ломки общих сущностей.

Связано: [requirements.md](requirements.md), [glossary.md](glossary.md), ADR-0004.

---

## 1. Принципы

1. **Тип документа** (`document_type`) — классификация входного файла (model + rules); низкая уверенность → `needs_review` / ручной выбор пользователем.
2. **Общие сущности** извлекаются для всех типов в scope.
3. **Специализированные проверки** (`check_pack`) подключаются по типу; каждая проверка версионируется и имеет `review_status`.
4. Выход проверки — набор **facts** и/или **inferences** с uncertainty; никогда «вердикт юриста».

---

## 2. Типы документов MVP

| Code | Название | В MVP | Примечание |
|------|----------|-------|------------|
| `contract.sale_purchase` | Договор купли-продажи | yes | Вкл. ДКП движимого/типового; недвижимость — осторожные disclaimers |
| `contract.lease` | Договор аренды / найма | yes | |
| `contract.services` | Договор возмездного оказания услуг | yes | |
| `contract.nda` | Соглашение о конфиденциальности | yes | |
| `contract.employment_template` | Трудовой договор (шаблон общего вида) | yes | Не кадровая система работодателя |
| `contract.loan_private` | Договор займа (частные стороны) | yes | Без банковского скоринга |
| `contract.other` | Договор прочий | yes | Минимальный check pack |
| `user.doc.general` | Пользовательский документ общего назначения | yes | Структурирование + сущности без жёсткого шаблона |
| `form.application` | Заявление / анкета | yes | Связь с `form_version` |
| `entry.wizard_pack` | Пакет мастера въезда | yes | Мета-тип набора требований |
| `identity.scan` | Скан удостоверяющего документа | limited | Только если пользователь явно загрузил; усиленный privacy + минимизация хранения |
| `medical.clinical` | Медицинский клинический | **no** | Out of scope; отказ с пояснением |
| `legal.court_strategy` | Судебная стратегия / исковая работа | **no** | Out of scope как экспертиза |

Классификация вне allowlist → `document_type=unknown` + ограниченный general pack + предупреждение.

---

## 3. Общие извлекаемые сущности (core entity schema)

Каждая сущность: `entity_type`, `value`, `normalized_value?`, `span|coordinates`, `confidence`, `uncertainty_state`, `provenance`.

| entity_type | Описание |
|-------------|----------|
| `party.name` | Наименование / ФИО стороны |
| `party.role` | Роль: покупатель, арендодатель, … |
| `party.identifier` | ИНН/ОГРН/паспортный идентификатор — с маскированием в UI/логах по политике |
| `party.address` | Адрес стороны |
| `party.bank_details` | Платёжные реквизиты |
| `doc.title` | Заголовок |
| `doc.number` | Номер документа |
| `doc.date.sign` | Дата заключения/подписания |
| `doc.date.effective` | Дата вступления в силу |
| `doc.date.end` | Срок окончания / действия |
| `doc.place` | Место заключения |
| `subject.description` | Предмет |
| `amount.value` | Сумма |
| `amount.currency` | Валюта |
| `amount.payment_schedule` | График/порядок оплаты (структурировано по возможности) |
| `obligation.summary` | Краткое описание обязанности стороны (fact-уровень цитаты/парафраза с provenance) |
| `liability.clause_ref` | Ссылка на пункт об ответственности |
| `termination.clause_ref` | Расторжение |
| `dispute.clause_ref` | Споры / подсудность (как факт наличия пункта, не совет) |
| `signature.block` | Блок подписей (наличие/стороны) |
| `annex.ref` | Приложения |
| `ocr.page_quality` | Служебная мета-сущность качества |

Нормализация дат/сумм — deterministic parsers; при провале → raw + `ambiguous`.

---

## 4. Специализированные check packs (расширяемая схема)

### 4.1. Метамодель

```text
CheckPack {
  pack_id, pack_version, document_types[], review_status,
  checks: Check[]
}
Check {
  check_id, title, severity_hint,  # severity = UX priority, not legal verdict
  inputs: entity_type[] | source_snapshot_refs[],
  logic_ref,  # ruleset id or model adapter id
  outputs: (fact|inference)[],
  on_insufficient: insufficient_data|needs_review,
  disclaimer_key
}
```

Публикация pack только при `review_status=approved` (ADR-0004).

### 4.2. Packs MVP (черновик)

| pack_id | Типы | Примеры checks (не юридический вердикт) |
|---------|------|----------------------------------------|
| `core.entities.v1` | all in-scope | Полнота core entities; флаги missing |
| `contract.dates_amounts.v1` | contract.* | Согласованность сумм/дат между разделами; конфликты → inference `conflict_detected` |
| `contract.parties.v1` | contract.* | Разные написания одной стороны; missing role |
| `contract.lease.v1` | contract.lease | Объект аренды, срок, плата — покрытие полей |
| `contract.sale.v1` | contract.sale_purchase | Предмет, цена, порядок передачи — покрытие |
| `compare.entities.v1` | multi-doc | Diff party/amount/date/subject |
| `entry.wizard.v1` | entry.wizard_pack | Чеклист документов vs source snapshot; gaps |
| `form.fill_assist.v1` | form.application | Кандидаты полей из facts + confirmation gates |
| `safety.injection.v1` | all | Детект prompt-injection patterns в тексте документа (heuristic) |

Каждый check при нехватке данных **обязан** вернуть `insufficient_data` или `needs_review`, а не «всё в порядке».

### 4.3. Расширение

1. Редактор источников/проверок создаёт `draft` pack.
2. Юрист-рецензент / designated reviewer → `approved` или `rejected`.
3. Feature flag / canary на долю трафика (`ROLLOUT_POLICY_NEEDS_REVIEW`).
4. Старые отчёты сохраняют `pack_version` snapshot ids.

---

## 5. Связь с отчётом

Отчёт пользователя содержит:

- `document_type` (+ confidence)
- списки facts / inferences
- применённые `check_pack` + versions
- `source_snapshot` refs
- uncertainty summary
- disclaimers

Запрещённые секции отчёта: «Правовое заключение», «Рекомендация подписать», «Диагноз», «Вы обязаны…» как normative output модели.
