# Объединённая версия Docly — опубликована 2026-09-08

## Готовый результат
- Релиз: https://github.com/dushavolka1-design/Misha-debil/releases/tag/docly-integrated-20260908.3.1
- EXE: https://github.com/dushavolka1-design/Misha-debil/releases/download/docly-integrated-20260908.3.1/Docly-Setup-x64.exe
- Путь сборки: release/Docly-Setup-x64.exe. Файл опубликован во вложениях релиза, не в Git-истории.
- Размер: 3 082 080 байт.
- SHA256: 6acbc851855761527fa088f9c0e6f317face84682a305462ec7f511f4b56c088 (совпадает с GitHub asset digest).
- Коммит исходников EXE: 183cad0d86760445799f24b0dd914d4e528936f4.
- Windows CI: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34266940257
- PR: https://github.com/dushavolka1-design/Misha-debil/pull/3 — база master, слияние в master не выполнялось.

## Включённые ветки
Проверка git merge-base --is-ancestor подтвердила включение каждого снимка:
- master: 7ab48303efa92b2e52702256dcdd360c9540d273
- astra/docly-full-audit-20260906: 7ab48303efa92b2e52702256dcdd360c9540d273
- astra/docly-windows-installer-20260906: 7ab48303efa92b2e52702256dcdd360c9540d273
- backup-before-merge: d4e6da60507efb3f6aed78a1dd8ccd294e453386
- astra/docly-modern-redesign-20260906: db099db89d57a24a1255a545463cdd65e76c839c
- fix/docly-desktop-upgrade-safety: 59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d
- chore/docly-fast-windows-installer: 04372810841cf9839f1c97afec2b7690b3fa684b

main не использовалась как входная ветка или основа сборки. Её текущий коммит совпадал с backup-before-merge; общая история поэтому присутствует через запрошенную backup-ветку (и историческую интеграцию desktop-safety). Исключение имени main не означает удаление общих коммитов.

Редизайн и desktop-safety объединены обычными merge-коммитами. Код с конфликтами не отбрасывался. Конфликты README разобраны: заглушка backup и обе документации сохранены в docs/branch-history, основной README различает текущий online-installer и альтернативную offline-сборку scripts/windows. Все исходные ветки и прежний релиз сохранены.

## Проверено в этой работе
Windows Server 2022, Node 22, Python 3.12:
- включение снимков всех веток;
- синтаксис installer PowerShell;
- unittest launcher safety, Windows kernel, profile restore, profile backup;
- Inno Setup EXE compilation;
- чистая установка в LOCALAPPDATA/Programs/Docly;
- оба ярлыка, запись установленных программ;
- отсутствие .git, реальной .env, готовых node_modules и venv в payload;
- полный first-run bootstrap, venv, production Next.js build;
- локальная .env, случайный SESSION_SECRET, ALLOW_FAKE_PROVIDERS=true;
- SQLite migration;
- HTTP 200 /live, /ready и /app/analyzer на 8000/3000;
- повторный запуск без новых API/Web PID и без смены секрета;
- остановка API/Web;
- переустановка с сохранением конфигурации и базы;
- штатное удаление с сохранением пользовательских данных.

Доказательства: installer/INTEGRATION.md (все SHA и изменённые пути), installer/INTEGRATED-CI.md (итог), installer/INTEGRATED-PROGRESS.md (этапы), release assets smoke-results.txt, build-info.json и SHA256.
Локально также прошли тестовые Git-сценарии обычного объединения, отдельной backup-истории, сохранения обеих README и отказа от неразрешённых конфликтов кода.

## Повторная сборка
Windows x64, Git, Inno Setup 6.3+, pnpm:
```powershell
git switch release/docly-all-branches-20260908
pnpm installer:windows
```
Для точно тех исходников: git switch --detach 183cad0d86760445799f24b0dd914d4e528936f4, затем та же команда. Побитовое совпадение EXE не обещается.

## Ограничения
Неподписанный prerelease; не production-ready и не offline-дистрибутив. Node 20+ и Python 3.12+ не встроены; установщик проверяет наличие и предлагает winget/официальный сайт. При первом запуске загружаются pnpm 9.15.9, JS и Python зависимости, при необходимости Noto Sans. Desktop SQLite/файлы, без Docker/PostgreSQL/Redis.

Ручные Windows 10/11 GUI/winget и полноценная визуальная приёмка редизайна не выполнялись. Smoke проверяет HTTP маршрута, не открытие браузера человеком. Повторная установка той же объединённой версии проверена; перенос данных из любого старого релиза и альтернативный offline-инсталлятор не объявляются проверенными этим smoke.

Полный монорепозиторий не объявляется прошедшим проверки; unrelated CI failures не замаскированы. Старые installer/CI-RESULT.md, STATUS.md, RELEASE-VERIFICATION.md относятся к предыдущему EXE. Новые документационные коммиты после 183cad0d не требуют переиздания приложения.
