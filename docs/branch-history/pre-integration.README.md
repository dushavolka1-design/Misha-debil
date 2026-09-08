# Docly

Monorepo (pnpm + Turborepo + FastAPI). Реализованы каркас, UI shell и безопасная регистрация с versioned legal / consent audit.

## Требования

- Node.js ≥ 20, pnpm 9.15.9 (`corepack enable` или `npx pnpm`)
- Python **3.12** (для API/worker; в Docker-образах зафиксирован 3.12)
- Docker + Docker Compose (Postgres, Redis, MinIO, ClamAV)

## Clean clone → локальный стенд

```bash
cp .env.example .env
pnpm install
docker compose -f infra/docker-compose.yml up -d postgres redis minio minio-init clamav

# Python API
cd apps/api
python3.12 -m venv .venv
# Windows: py -3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ../../packages/py_dar
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
alembic upgrade head
# rollback check:
alembic downgrade -1 && alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Web (другой терминал, из корня)
pnpm --filter @dar/web dev
```

Документированные детали миграций: [infra/README.md](infra/README.md).

## Desktop launcher (Windows) — Docly, без Docker

Ярлык **Docly** на рабочем столе. **Docker не нужен** — база и Redis встроены в папку проекта.

Переустановка ярлыка:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/create-desktop-shortcut.ps1
```

### Что нужно на любом ПК / моноблоке

- **Python 3.12+** (в PATH)
- **Node.js 20+** (в PATH)
- **Интернет только при первом запуске** (~300 MB: PostgreSQL + Redis скачиваются в `infra/portable/`)

Папку проекта можно копировать на флешку или другой компьютер — пути относительные, Docker не требуется.

### Первый запуск

1. Двойной клик **Docly** (или `scripts/windows/start-dar.ps1`)
2. Автоматически: venv + pip, скачивание PostgreSQL/Redis, миграции, API :8000, Web :3000
3. Откроется браузер на `http://127.0.0.1:3000/app/analyzer`

Логи: `artifacts/local-run/`. Данные БД: `infra/.data/`.

### Ручная установка БД (если нужно)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/setup-portable-db.ps1
```
3. Выполняет `alembic upgrade head`
4. Запускает API и ждёт **GET /live** и **GET /ready**
5. Запускает Next.js и ждёт HTTP 200
6. Открывает браузер только после готовности обоих сервисов

Логи: `artifacts/local-run/` (`launcher.log`, `launcher-diagnostic.txt`, `api.err.log`, `web.err.log`).

Проверка скрипта launcher: `powershell -File scripts/windows/test-launcher.ps1`

### Локальное хранение (не production)

В режиме launcher включены **fake-провайдеры** (`ALLOW_FAKE_PROVIDERS=true`): OCR/LLM/оплата/почта — заглушки для разработки.
**Основное состояние** (пользователи, документы, анализ, формы, billing) сохраняется в **PostgreSQL** через Alembic-схему.
Файлы документов — в fake object storage (in-memory); для полного S3 используйте Docker MinIO из compose.

Это **dev/local storage**, не production-ready конфигурация.

## Структура

| Путь | Назначение |
|------|------------|
| `apps/web` | Next.js UI |
| `apps/api` | FastAPI + Alembic |
| `apps/worker` | Очередь jobs |
| `packages/contracts` | OpenAPI → TypeScript |
| `packages/ui` | Shared UI |
| `packages/py_dar` | Provider ports + fake adapters |
| `infra` | Compose / CI helpers |
| `legal`, `sources` | Согласия и реестр источников |
| `docs` | Этап 1 (ТЗ, ADR, threat model) |

## Контракты

```bash
pnpm contracts:export    # FastAPI → packages/contracts/openapi/openapi.json
pnpm contracts:generate  # openapi-typescript
pnpm contracts:check     # fail on drift
```

Web вызывает API через единый клиент `apps/web/src/lib/apiClient.ts` (timeout, retry, типизированные ошибки).

## UI / UX (этап 3)

```bash
pnpm --filter @dar/web dev
pnpm storybook
pnpm test:e2e   # Playwright + axe + visual snapshots (нужен браузер Playwright)
```

Состояния экранов: `?state=loading|empty|error|forbidden|expired|offline`.

Порог a11y (черновик DL-014): Lighthouse Accessibility ≥ 90; axe без critical/serious.

Дизайн: нейтральный светлый UI, один сине-фиолетовый accent, без государственной символики.

## Auth / согласия (этап 4)

Спека: [docs/product/legal-and-consent-spec.md](docs/product/legal-and-consent-spec.md). Демо-тексты: `legal/consents/`.

- Регистрация `/auth/register`: обязательные terms + offer + ordinary PD (отдельно), marketing optional unchecked; medical — только перед upload.
- Сессии: Argon2id, email verify, rate limit, anti-enumeration, ротация/отзыв, cookie `httpOnly` + `SameSite=Lax` (+ `Secure` в production).
- Legal: immutable published versions + SHA-256; `ConsentEvent` append-only.
- Privacy dashboard: `/app/profile` — активные согласия, отзыв, export/delete (доступны даже без re-accept новой оферты).

```bash
cd apps/api && pytest tests/test_auth_consent.py tests/test_logging_redaction.py -q
pnpm --filter @dar/web test:e2e -- e2e/auth-consent.spec.ts
```

## Upload / lifecycle (этап 5)

Спека: [docs/product/upload-lifecycle-spec.md](docs/product/upload-lifecycle-spec.md).

FSM: `CREATED → UPLOADING → QUARANTINED → SCANNING → CLEAN → PROCESSING → READY` (+ `REJECTED/INFECTED/FAILED/EXPIRED/DELETING/DELETED`).

- Intent только для авторизованных с лимитами плана; short-lived single-purpose upload URL.
- Post-upload: size/extension/MIME/magic/checksum; quarantine не отдаётся; обработка только после CLEAN.
- Envelope encryption + opaque keys; retention/purge/tombstone; export без секретов/чужих данных.
- Fixtures: `tests/fixtures/upload/` (без реального malware).

```bash
cd apps/api && pytest tests/test_upload_lifecycle.py -q
```

## Analysis / OCR / facts (этап 6)

Спека: [docs/product/analysis-pipeline-spec.md](docs/product/analysis-pipeline-spec.md).

- Нормализация страниц (width/height/rotation) без изменения original.
- OCR words/lines/blocks + bbox; layout (heading/table/signature/annex); facts только с citation.
- JSON Schema reject extra fields; deterministic normalizers (даты/деньги/ИНН/ОГРН/СНИЛС — формат/checksum).
- Версии pipeline/prompt/schema/adapters; повторный анализ = новый run.
- Golden fixtures: `digital_pdf`, `scan`, `rotated_scan`, `table`, `docx`, `poor_quality`, `mixed_script`.

```bash
cd apps/api && pytest tests/test_analysis_pipeline.py -q
```

## Rules / compare / report (этап 7)

Спека: [docs/product/rules-and-report-spec.md](docs/product/rules-and-report-spec.md).

- Rule registry + general-purpose checks; severity = приоритет ручной проверки.
- Разделение `observed_text` / `structural_conflict` / `review_question` / `normative_claim`.
- Compare с dual citations; запрет cross-user; защита от prompt injection.
- Export PDF/JSON (версия, disclaimer, источники, unanalyzed pages).
- Feedback append-only, без авто-изменения результатов.

```bash
cd apps/api && pytest tests/test_rules_report.py -q
```

## Official sources (этап 8)

Спека: [docs/product/official-source-policy.md](docs/product/official-source-policy.md). Allowlist: `sources/allowlist.json`.

- Deny-by-default URL validator (HTTPS, IDN, no userinfo/private IP/odd ports, redirect re-check).
- FSM: discovered → fetched → parsed → awaiting_review → approved → superseded/expired/rejected.
- Immutable snapshots (raw, headers, hash, text, parser); hash change → review task + dependents to review.
- Citation API; seed только метаданными официальных доменов.

```bash
cd apps/api && pytest tests/test_source_registry.py -q
```

## Entry / stay wizard (этап 9)

Спека: [docs/product/entry-wizard-spec.md](docs/product/entry-wizard-spec.md).

- Rule-driven мастер (не универсальный список «для всех иностранцев»): анкета → decision pack отдельно от UI.
- Стадии: до поездки / граница / после въезда / работа·учёба / продление / мед·дактилоскопия.
- Deadline calculator (календарные/рабочие дни, событие, регион, договор, статус) + timezone + explanation.
- Пошлина только из approved fee catalog + snapshot; иначе «уточните на официальном ресурсе».
- Snapshot результата + refresh; черновик только с согласием; freshness policy блокирует устаревшие/конфликтные источники.
- API: `/entry/*`; UI: `/app/entry-wizard`.

```bash
cd apps/api && pytest tests/test_entry_wizard.py -q
```

## Forms catalog & medical (этап 10)

Спека: [docs/product/forms-and-medical-spec.md](docs/product/forms-and-medical-spec.md).

- Регистрация формы только с approved source + raw + SHA-256 + акт + valid interval + review.
- MVP МВД: без верифицированного официального raw → `needs_review`, не published.
- Медраздел: Минздрав/Роспотребнадзор; PDF только questionnaire/checklist/memo с баннером; запрещённые типы блокируются backend (не только UI).
- Медицинская загрузка: отдельное согласие, короткий retention, `medical_restricted`.
- Abuse/outdated: `POST /forms/abuse-reports`.
- API: `/forms/*`; UI: `/app/forms`.

```bash
cd apps/api && pytest tests/test_forms_medical.py -q
```

## Pixel-perfect form fill (этап 11)

Спека: [docs/product/form-fill-pixel-spec.md](docs/product/form-fill-pixel-spec.md).

- Immutable FormVersion: underlay hash, page geometry, coord-map hash, fonts, effective interval, four-eyes publish.
- Generator clones PDF underlay (no rasterize/reflow); text only in approved bboxes; signature/stamp empty.
- Preview: length, alphabet, wrap, required, organ/manual fields.
- GeneratedForm audit hashes + delete; superseded source → `blocked_for_new` (old outputs remain).
- Pixel-diff report → `artifacts/pixel-diff/` (CI artifact).
- API: `/forms/fill/*`.

```bash
cd apps/api && pytest tests/test_form_fill.py -q
```

## Legal package drafts (этап 12)

Спека: [docs/product/legal-and-consent-spec.md](docs/product/legal-and-consent-spec.md). Артефакты: [legal/](legal/).

- Раздельные черновики: оферта, соглашение, политика ПД, согласие на обычные ПД, спец. категории, cookies, маркетинг, рекуррентные списания.
- Placeholders без выдуманных реквизитов; `manifest.json` + approvals lawyer/privacy_officer.
- Production (`LEGAL_ROOT`) падает при draft/placeholders/без approve.
- Отмена подписки в UI без обязательного обращения в поддержку; disclaimer не снимает обязательную ответственность.
- Fixtures + `test_legal_package.py` + e2e auth-consent/billing.

```bash
cd apps/api && pytest tests/test_legal_package.py -q
```

## Subscription & payments (этап 13)

Спека: [docs/product/billing-spec.md](docs/product/billing-spec.md).

- `PaymentProvider` + `ru_payment_sandbox` (без production API до договора/credentials).
- Server `PRICE_TABLE`; webhook signature/timestamp/idempotency; dunning ≤3; trial notice; cancel + history in UI.
- Чеки/возвраты только через provider capabilities после legal/accounting review — фиктивные чеки не генерируются.
- Admin reconciliation + Alembic `0008_billing`.
- Production: live provider + `APPROVED_OFFER_VERSION`.

```bash
cd apps/api && pytest tests/test_billing.py -q
```

## Quality gates & launch hardening (этап 14)

**Verdict: NO-GO** — см. [docs/ops/staging-go-no-go.md](docs/ops/staging-go-no-go.md). Не объявлять production-ready при открытых critical gates.

- Gates: [docs/quality/quality-gates.md](docs/quality/quality-gates.md)
- Traceability: [docs/quality/traceability.md](docs/quality/traceability.md)
- Runbooks: [docs/ops/runbooks/](docs/ops/runbooks/)
- Clean-clone CI: [scripts/ci-from-clean-clone.md](scripts/ci-from-clean-clone.md)
- Staging synthetic: `infra/docker-compose.staging.yml` + `infra/staging/synthetic_seed.md`
- AI eval / drills: `python -m app.scripts.run_ai_eval` (+ privacy/restore drills) → `artifacts/`

```bash
cd apps/api && pytest tests/test_ai_eval.py tests/test_security_hardening.py tests/test_privacy_drills.py tests/test_reliability.py -q
```

При `APP_ENV=production` процесс **не стартует**, если:

- включены fake providers / `ALLOW_FAKE_PROVIDERS=true`
- `DATABASE_URL` содержит SQLite или `change_me`
- `SESSION_SECRET` локальный/дефолтный
- не задан `LEGAL_ROOT` или legal package с placeholders / draft / без approve юриста и privacy officer

См. `infra/docker-compose.prod.yml`.

## CI

`.github/workflows/ci.yml`: install (lockfile), format, lint, typecheck, unit, AI eval + privacy/restore drills, migration upgrade/downgrade, gitleaks, trivy, prod-config scan, JS critical audit.

Повторяемость: [scripts/ci-from-clean-clone.md](scripts/ci-from-clean-clone.md).

## Документация продукта

См. [docs/product/requirements.md](docs/product/requirements.md), [docs/quality/quality-gates.md](docs/quality/quality-gates.md) и [docs/adr](docs/adr).
