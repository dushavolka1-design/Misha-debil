# Information architecture — proposed migration

Status: proposal except auth flow. No invented routes/tasks/notifications are shipped.

## Existing partial inventory
/, /auth/login, /auth/register, /app, /app/analyzer, /app/upload, /app/compare, /app/jobs, /app/reports, /app/generator, /app/entry-wizard, /app/forms, /app/sources, /app/profile, /app/billing. Dynamic routes not exhaustively mapped.

## Proposed grouping
- Главная: next real action, dashboard pending actual data inventory.
- Проверка документа: existing analyzer/upload/report journey.
- Переезд и пребывание: entry wizard with honest review/source states.
- Каталог форм: existing forms/generator; distinguish official blank, own draft and prohibited issued documents.
- Официальные источники: existing sources and evidence.
- Профиль и безопасность: existing profile/privacy/subscription.
- Мои задачи, Документы, История: pending object-level API and ownership review; backend jobs are not automatically user tasks.
- Уведомления/global search: only after confirmed API support, no invented counts/results.

## Navigation plan
Desktop compact collapsible sidebar with current-page labels, accessible tooltips and profile zone. Mobile3–4 real primary destinations plus accessible More drawer/focus return/safe area. Neither replacement is implemented in this increment.

## Implemented journey
Credentials → separate consents → honest next-step screen → existing login → analyzer. Required server display_name retained; optional avatar remains in profile. No server-authorization bypass or official-document authority introduced.
