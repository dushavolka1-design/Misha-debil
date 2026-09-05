# Legal package placeholders

Do **not** invent owner details. Replace tokens before production approval.

| Token | Meaning |
|-------|---------|
| `OWNER_LEGAL_FORM` | ОПФ (ООО / ИП / …) |
| `OWNER_NAME` | Полное наименование / ФИО |
| `INN` | ИНН |
| `OGRN_OR_OGRNIP` | ОГРН или ОГРНИП |
| `ADDRESS` | Юридический / почтовый адрес |
| `SUPPORT_EMAIL` | Поддержка пользователей |
| `PRIVACY_EMAIL` | Запросы субъекта ПД |
| `PAYMENT_PROVIDER` | Платёжный провайдер (юр. имя + договор) |
| `TARIFFS` | Актуальные тарифы/ссылка на прайс |
| `TRIAL` | Условия пробного периода (или «не применяется») |
| `RENEWAL` | Автопродление: период, напоминание, отмена |
| `REFUNDS` | Возвраты (в пределах закона о защите прав потребителей) |
| `RETENTION` | Сроки хранения по категориям |
| `PROCESSORS` | Перечень обработчиков (OCR/LLM/хостинг) + DPA |
| `DATA_LOCATIONS` | Локализация / трансграничная передача |

Draft documents must keep these tokens until filled. Production boot fails if any remain.
