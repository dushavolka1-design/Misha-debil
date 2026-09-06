"""Write Prompt 6 results.md in UTF-8 from results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

LABELS = {
    "shortcut-invalid": "ярлык невалиден",
    "shortcut-does-not-launch": "ярлык не запускает приложение",
    "startup-requires-docker": "startup требует Docker",
    "startup-requires-postgres-redis": "startup требует PostgreSQL/Redis",
    "startup-requires-docker-postgres-redis": "startup требует Docker/PostgreSQL/Redis",
    "offline-start-failed": "запуск с отключённым интернетом не удался",
    "forms-api-500": "API /forms возвращает 500",
    "catalog-lost-after-restart": "каталог исчезает после restart",
    "synthetic-government-form": "генерация использует synthetic government form",
    "missing-font-hash-license": "отсутствует font/hash/license",
    "body-font-below-16px-or-500": "основной шрифт тоньше 500 или меньше 16 px",
    "screenshot-review-failed": "дизайн не прошёл screenshot review",
    "pixel-diff-changed-underlay": "pixel diff меняет подложку",
    "published-form-without-official-source": "опубликованная форма не имеет approved official source",
}


def main() -> None:
    src = Path(sys.argv[1])
    payload = json.loads(src.read_text(encoding="utf-8-sig"))
    blockers = [LABELS.get(str(b), str(b)) for b in payload.get("blockers") or []]
    lines = [
        "# Prompt 6 acceptance",
        "",
        f"Verdict: **{payload.get('verdict')}**",
        "",
        "| ID | Status | Command | Evidence | Issue |",
        "|----|--------|---------|----------|-------|",
    ]
    for row in payload.get("results") or []:
        cmd = str(row.get("command") or "").replace("|", "/")
        ev = str(row.get("evidence") or "").replace("|", "/")
        lines.append(
            f"| {row.get('id')} | {row.get('status')} | `{cmd}` | `{ev}` | {row.get('issue') or ''} |"
        )
    if blockers:
        lines += ["", "## Blockers"]
        lines += [f"- {b}" for b in blockers]
    dest = src.with_name("results.md")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload["blockers_ru"] = blockers
    src.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
