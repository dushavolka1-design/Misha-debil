# Объединённая версия Docly — работа начата 2026-09-08

Пользователь уточнил задачу: включить обновления ВСЕХ существующих веток, кроме main, а не только master + installer. Создана отдельная ветка release/docly-all-branches-20260908 от chore/docly-fast-windows-installer.

installer/integrate-branches.py содержит проверенные SHA всех семи веток. Обычное Git-слияние, без ours/theirs и без перезаписи исходных веток. Уже включённые коммиты фиксируются как предки; конфликты блокируют сборку и требуют разбора.

.github/workflows/windows-integrated.yml выполняет объединение, проверку предков, Windows launcher/profile regressions, сборку Inno Setup, первый и повторный запуск, HTTP /live /ready /app/analyzer, переустановку и удаление. Новый prerelease публикуется только после успешных проверок. Документационный коммит после объединения служит точным sourceCommit EXE.

Результаты: installer/INTEGRATION.md и installer/INTEGRATED-CI.md. Если эти файлы ещё не появились, проверить Actions; НЕ считать задачу завершённой. Старые installer/CI-RESULT.md, STATUS.md и RELEASE-VERIFICATION.md относятся к прежнему EXE и не доказывают успех объединённой версии.

Первый запуск по-прежнему требует интернета. Desktop SQLite сохраняется. Ручные GUI-проверки Windows 10/11 не подменяются Windows Server CI. Исходные ветки и старый релиз не удалять; main не включать как merge target.
