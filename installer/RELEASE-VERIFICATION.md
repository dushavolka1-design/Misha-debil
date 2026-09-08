# Проверка существующего релиза — 2026-09-08

При продолжении задачи рабочая ветка и опубликованный EXE уже существовали. Пересборка, изменение продукта и слияние в master в этой сессии не выполнялись.

## Подтверждено через GitHub
- master и astra/docly-windows-installer-20260906: 7ab48303efa92b2e52702256dcdd360c9540d273.
- fix/docly-desktop-upgrade-safety: 59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d.
- Проверенная рабочая ветка: chore/docly-fast-windows-installer, до этой записи — 6b3c55d709f0e4a9b58b3adaf95289bff45c4bd9.
- PR #2 открыт в master, не слит: https://github.com/dushavolka1-design/Misha-debil/pull/2
- Опубликован предварительный релиз: https://github.com/dushavolka1-design/Misha-debil/releases/tag/docly-windows-0.1.0-ci.5.1
- EXE присутствует среди загруженных assets: https://github.com/dushavolka1-design/Misha-debil/releases/download/docly-windows-0.1.0-ci.5.1/Docly-Setup-x64.exe
- Размер по GitHub API: 3053048 байт.
- SHA256 по GitHub asset digest: 936ceeb7b6a5bf652f09d7fd80e1e5eaa3ac3142240557ccae112723f845c549. Совпадает с сохранёнными build metadata. Повторное скачивание и локальное хеширование в этой сессии не выполнялись.
- Исходный коммит EXE: 47873cda75018ebc3c58bb78f138ce60e06308e4.
- installer/CI-RESULT.md содержит успешные build/smoke/publication и результаты установки, первого/повторного запуска, HTTP 200 /live, /ready, /app/analyzer, переустановки и удаления на Windows Server 2022.
- Ссылка на соответствующий запуск: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34258968767
- На текущем документационном HEAD PR список check runs пуст; это не новый запуск тестов и не опровержение отчёта для исходного коммита EXE.

## Отличие от задания
В master scripts/windows/start-dar.ps1 явно не загружает PostgreSQL/Redis. Существующий desktop-профиль использует SQLite/файловое хранилище; опубликованный установщик сохраняет его. PostgreSQL/Redis/Alembic не были добавлены ради соответствия описанию стека, поскольку это изменило бы архитектуру продукта.

## Продолжение и ограничения
Команда повторной сборки на Windows с Inno Setup 6.3+: pnpm installer:windows. Выход: release/Docly-Setup-x64.exe. EXE опубликован как release asset, не как файл Git-истории.

Первый запуск требует интернета: pnpm 9.15.9, JS-зависимости, Python-пакеты, при необходимости Noto Sans. Node/Python не встроены; установщик предлагает winget либо официальный сайт.

Ручные Windows 10/11 GUI-проверки, открытие браузера, отсутствующие зависимости и winget остаются непроверенными. Текущая среда Linux не содержит Windows/Inno Setup; прямой git-доступ не разрешил имя github.com. Доступ через подключённый GitHub работает. Никаких новых Windows smoke-тестов в этой сессии не выполнено.

Релиз остаётся unsigned prerelease. Конфигурация и пользовательские данные сохраняются после удаления. Полный монорепозиторий не объявляется прошедшим проверки. Подробный исходный конспект: installer/STATUS.md; инструкция: installer/README.md.
