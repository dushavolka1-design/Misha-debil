# Decision log — неизвестные и открытые решения

Правило: неизвестное **не скрывается** в ТЗ как «уже решено». Статусы: `open` | `needs_review` | `decided` | `deferred`.

| ID | Тема | Статус | Заметка |
|----|------|--------|---------|
| DL-001 | Юрисдикция и контур хранения ПДн | `needs_review` | Placeholder `JURISDICTION_POLICY_NEEDS_REVIEW` |
| DL-002 | Срок retention originals | `needs_review` | `RETENTION_ORIGINALS_NEEDS_REVIEW` — не фиксировать без legal |
| DL-003 | Срок retention reports / derived | `needs_review` | `RETENTION_REPORTS_NEEDS_REVIEW` |
| DL-004 | Legal hold / исключения erasure | `needs_review` | `LEGAL_HOLD_POLICY_NEEDS_REVIEW` |
| DL-005 | Billing provider и оферта | `open` | `BILLING_PROVIDER_NEEDS_REVIEW`, `TARIFF_*` |
| DL-006 | Реквизиты владельца продукта | `open` | `OWNER_LEGAL_NAME`, `OWNER_INN`, `OWNER_SUPPORT_CONTACT` |
| DL-007 | Антивирусный/sandbox pipeline загрузок | `needs_review` | `AV_PIPELINE_NEEDS_REVIEW` |
| DL-008 | Политика паролированных загрузок | `open` | `ENCRYPTED_UPLOAD_POLICY_NEEDS_REVIEW` |
| DL-009 | Step-up auth для удаления аккаунта | `needs_review` | `STEP_UP_AUTH_NEEDS_REVIEW` |
| DL-010 | Evidence согласия (IP/device) | `needs_review` | Минимизация vs доказуемость |
| DL-011 | Конкретные вендоры AI/OCR РФ | `open` | Только adapter interface на этапе 1 |
| DL-012 | COMPARE_MAX_DOCS окончательно | `needs_review` | Черновик = 5 |
| DL-013 | DR RPO/RTO | `needs_review` | `DR_TARGETS_NEEDS_REVIEW` |
| DL-014 | A11Y target | `needs_review` | Черновик порога: Lighthouse Accessibility ≥ 90; axe без critical/serious на основных экранах |
| DL-015 | Maintenance window / error budget policy | `needs_review` | |
| DL-016 | Break-glass процедура support/admin | `needs_review` | Обязателен audit reason |
| DL-017 | Интеграция подачи в госсистемы | `deferred` | `GOV_SUBMIT_OUT_OF_SCOPE` для MVP |
| DL-018 | Порог confidence по типам сущностей | `open` | Нужны калибровочные наборы |
| DL-019 | Язык UI помимо ru-RU | `deferred` | MVP: ru-RU |
| DL-020 | Модель ответственности юриста-рецензента перед пользователем | `needs_review` | Внутренний QA ≠ услуга пользователю |

Обновлять этот файл при закрытии пунктов; в ТЗ оставлять ссылку на ID, а не «тихий» хардкод.
