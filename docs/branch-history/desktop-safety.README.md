# Docly

Docly — монорепозиторий: Next.js, FastAPI, общие TypeScript/Python-пакеты и Windows desktop launcher.

> **Статус: кандидат, не подтверждённый production-релиз.** Успешная сборка интерфейса не равна проверенной установке. Готовность конкретного установщика подтверждается только журналом `Real installer lifecycle acceptance` для его исходного коммита. Открытые ограничения production перечислены в [staging-go-no-go.md](docs/ops/staging-go-no-go.md): юридические согласования, реальные провайдеры, security/privacy gates. Не используйте тестовые провайдеры для реальных платежей или чувствительных документов.

## Ветки и история

- Целевая основная ветка: `main`.
- Интеграция: `fix/docly-desktop-upgrade-safety`, [PR №1](https://github.com/dushavolka1-design/Misha-debil/pull/1).
- `backup-before-merge` сохраняет исходную `main` на `d4e6da60507efb3f6aed78a1dd8ccd294e453386`.
- Код `master`, `astra/docly-full-audit-20260906` и `astra/docly-windows-installer-20260906` имел общий коммит `7ab4830`. Ветка редизайна `astra/docly-modern-redesign-20260906` добавила три коммита поверх него.
- Независимые истории соединены merge-коммитом `25496b9`; исходный README из `main` сохранён в [docs/integration/legacy-main-README.md](docs/integration/legacy-main-README.md). История не переписывалась, старые ветки не удалялись.

## Windows: сборка из чистого клона

Среда сборки: Windows x64, **Python 3.12 x64**, Node.js 20, **pnpm 9.15.9**, Git, Windows PowerShell 5.1 и **Inno Setup 6.5+**. Интернет нужен машине сборки для получения зависимостей. Не копируйте готовую `.venv` с другого компьютера: она содержит абсолютные пути.

```powershell
git clone https://github.com/dushavolka1-design/Misha-debil.git
cd Misha-debil
git switch fix/docly-desktop-upgrade-safety
# После слияния PR используйте main.
corepack enable
corepack prepare pnpm@9.15.9 --activate
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/setup-desktop.ps1
if ($LASTEXITCODE -ne 0) { throw 'Source setup failed' }
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/build-installer.ps1 -Version 0.2.1
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
```

Сборщик берёт **закоммиченный HEAD** через `git archive`: незакоммиченные правки в установщик не попадут. Он использует отдельную staging-папку, hoisted layout зависимостей только в дистрибутиве, компилирует Next-конфигурацию и упаковывает Node, CPython, production JS-зависимости и Python wheelhouse. Виртуальное окружение создаётся на машине установки офлайн, а не переносится с CI.

Пути результата **после успешной сборки**:

```text
artifacts/installer/Docly-0.2.1-windows-x64-setup.exe
artifacts/installer/Docly-0.2.1-windows-x64-setup.exe.sha256
```

Проверка SHA-256:

```powershell
Get-FileHash artifacts/installer/Docly-0.2.1-windows-x64-setup.exe -Algorithm SHA256
Get-Content artifacts/installer/Docly-0.2.1-windows-x64-setup.exe.sha256
```

Папки `artifacts`, `.venv`, `node_modules`, wheelhouse и runtime из staging не коммитятся. Не добавляйте в Git реальные `.env`, пароли, токены, пользовательские базы или логи с персональными данными.

## Установка и запуск

Целевая платформа установщика — Windows 10/11 x64. GitHub Actions `windows-latest` проверяет Windows runner; это не отдельная сертификация каждой редакции Windows.

1. Используйте только кандидат с успешной проверкой installer lifecycle и совпадающим SHA-256.
2. Запустите `Docly-0.2.1-windows-x64-setup.exe` обычным пользователем. По умолчанию файлы программы находятся в `%LOCALAPPDATA%\Programs\Docly`.
3. Дождитесь завершения офлайн-установки Python-зависимостей. Ошибка этой операции считается ошибкой установки.
4. Запустите ярлык **Docly**. Он использует включённые в дистрибутив Node/Python; системные Python, Node, PostgreSQL, Redis и Docker для этого профиля не требуются.

Подпись Authenticode пока не настроена: установщик не следует представлять как подписанный или обходить предупреждения безопасности без проверки происхождения и хеша.

Пример тихой установки для тестового ПК:

```powershell
.\Docly-0.2.1-windows-x64-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="docly-install.log"
```

## Обновление и пользовательские данные

Desktop-профиль использует **SQLite и файловое хранилище**, а не portable PostgreSQL/Redis:

- база: `%LOCALAPPDATA%\Docly\data\docly.db`;
- каталог данных: `%LOCALAPPDATA%\Docly\data`, либо явно заданный `DOCLY_DATA_DIR`;
- runtime-маркеры: `%LOCALAPPDATA%\Docly\runtime`, либо `DOCLY_RUNTIME_DIR`;
- логи запуска: `artifacts\local-run` внутри каталога программы.

Перед обновлением завершите Docly и сохраните отдельную копию каталога данных и своих настроек окружения. Затем запускайте новый установщик поверх **того же каталога программы**; удалять старые данные не нужно. Не размещайте пользовательские данные внутри `.venv`, `node_modules` или каталога программы. Установщик не переносит произвольные внешние настройки окружения между учётными записями Windows.

При необходимости поддерживаемого изменения SQLite-схемы создаётся проверенный снимок в `data\backups\docly-before-schema-*.db`. SQLite backup API учитывает committed WAL-страницы. Если проверка или копирование не удались, миграция не начинается. Снимок базы не является полной резервной копией документов: сохраняйте весь каталог данных отдельно. Старые снимки автоматически не удаляются; контролируйте свободное место.

Исторические `setup-portable-db.ps1` / `start-dar.ps1` сохранены в репозитории, но не описывают текущий SQLite-профиль. Автоматическая миграция старой PostgreSQL-базы в SQLite **не реализована** — не заменяйте такую установку, рассчитывая на автоматический перенос.

## Удаление

Используйте штатное удаление Docly в настройках Windows либо `unins000.exe` из каталога установки. Перед удалением завершите приложение. Удаляются файлы программы и сгенерированное Python-окружение; `%LOCALAPPDATA%\Docly` и внешний `DOCLY_DATA_DIR` намеренно сохраняются. Полное удаление пользовательских данных — отдельное осознанное действие владельца, не часть обновления или стандартного uninstall.

## Проверки

Независимые регрессионные тесты резервирования SQLite:

```powershell
$env:PYTHONPATH = "$pwd\apps\api"
python -m unittest discover -s apps/api/tests -p test_desktop_backup.py -v
```

Проверка исходной desktop-сборки:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/test-launcher.ps1
```

Проверка настоящих установщиков (на отдельной тестовой Windows-машине):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/build-installer.ps1 -Version 0.2.0 -SourceRef 7ab48303efa92b2e52702256dcdd360c9540d273
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/build-installer.ps1 -Version 0.2.1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/test-installer.ps1 -OldInstaller "$pwd\artifacts\installer\Docly-0.2.0-windows-x64-setup.exe" -NewInstaller "$pwd\artifacts\installer\Docly-0.2.1-windows-x64-setup.exe"
```

`0.2.0` здесь — контрольный установщик, заново собранный из первоначального кода, **не найденный старый опубликованный релиз**. Проверка охватывает установку, запуск через установленный launcher без системных Node/Python в PATH, HTTP readiness, обновление, целостность реальной SQLite-базы и сохранение тестовых файлов настроек/документов, uninstall и установку новой версии с чистым профилем. Это не доказывает перенос любой исторической версии или всех production-настроек.

Windows workflow: [.github/workflows/docly-desktop-verification.yml](.github/workflows/docly-desktop-verification.yml). Кандидат загружается в артефакты только после успешного installer lifecycle. Не подменяйте ошибки `continue-on-error`, фиктивными ответами сервисов или отключением проверок.

## Разработка серверного профиля

Для PostgreSQL/Redis/MinIO/ClamAV нужен Docker Compose. Этот профиль отличается от desktop.

```bash
cp .env.example .env
# Заполните локальные параметры; не коммитьте .env.
pnpm install --frozen-lockfile
docker compose -f infra/docker-compose.yml up -d postgres redis minio minio-init clamav
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ../../packages/py_dar
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# В другом терминале, из корня:
pnpm --filter @dar/web dev
```

Основные проверки из корня: `pnpm format:check`, `pnpm lint`, `pnpm typecheck`, `pnpm contracts:check`, `pnpm test:unit`, `pnpm test:e2e`. Экспорт OpenAPI: `pnpm contracts:export`; генерация TypeScript: `pnpm contracts:generate`. Storybook: `pnpm storybook`.

## Структура и документация

| Каталог | Назначение |
|---|---|
| `apps/web` | Next.js UI |
| `apps/api` | FastAPI, модели, миграции, desktop boot |
| `apps/worker` | Обработка очереди |
| `packages/contracts`, `packages/ui`, `packages/py_dar` | Общие контракты, UI и Python-код |
| `scripts/windows` | Launcher, сборка установщика и проверки |
| `legal`, `sources` | Юридические документы и реестр источников |
| `infra` | Серверная инфраструктура |

- [Требования](docs/product/requirements.md), [ADR](docs/adr), [quality gates](docs/quality/quality-gates.md), [traceability](docs/quality/traceability.md).
- [Регистрация и согласия](docs/product/legal-and-consent-spec.md), [загрузка документов](docs/product/upload-lifecycle-spec.md), [анализ](docs/product/analysis-pipeline-spec.md).
- [Правила и отчёты](docs/product/rules-and-report-spec.md), [официальные источники](docs/product/official-source-policy.md), [мастер въезда](docs/product/entry-wizard-spec.md).
- [Формы](docs/product/forms-and-medical-spec.md), [заполнение PDF](docs/product/form-fill-pixel-spec.md), [подписки](docs/product/billing-spec.md).
- [Миграции серверной БД](infra/README.md), [runbooks](docs/ops/runbooks/), [clean-clone CI](scripts/ci-from-clean-clone.md).

Production по-прежнему требует реальных провайдеров, безопасных настроек и утверждённого legal package. Сборка `.exe` сама по себе не закрывает эти требования.
