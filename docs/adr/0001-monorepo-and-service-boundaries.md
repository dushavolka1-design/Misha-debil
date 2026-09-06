# ADR-0001 — Monorepo и границы сервисов

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

Нужны web UI, API, workers OCR/анализа, source registry, billing adapter, admin tools. Команда на старте небольшая; важны единые контракты fact/inference и согласованные политики безопасности.

## Decision

Использовать **monorepo** с явными пакетами/сервисами и границами deployables:

| Deployable | Ответственность |
|------------|-----------------|
| `apps/web` | UI пользователя и редакторские экраны |
| `apps/api` | Authz, uploads metadata, jobs, consents, RBAC |
| `apps/worker-ocr` | OCR via adapters |
| `apps/worker-analyze` | Checks, facts/inferences, reports |
| `apps/worker-erasure` | Retention/crypto-erasure |
| `packages/contracts` | JSON schemas, glossary enums |
| `packages/adapters-*` | AI/OCR/billing/source-fetch interfaces |
| `infra/` | IaC, CI |

Сервисы общаются через API + очередь; workers не торчат публично.

## Alternatives

| Alternative | Why not (now) |
|-------------|----------------|
| Polyrepo per service | Выше координационные издержки на MVP; сложнее атомарно менять contracts |
| Modular monolith only | Проще старт, но хуже изоляция OCR malware blast radius |
| Serverless-only spaghetti | Сложнее единый threat model и локальная воспроизводимость |

## Consequences

- **+** Единые контракты и CI policy gates (IDOR, policy tests).  
- **+** Изоляция worker trust zone от API.  
- **−** Нужна дисциплина границ пакетов (запрет «достать чужую DB»).  
- **−** CI monorepo должен уметь affected builds (`CI_AFFECTED_NEEDS_REVIEW`).

## Links

requirements FR-01/05/07; threat-model TM-S1/S9; acceptance AT-FR-01, AT-FR-05.
