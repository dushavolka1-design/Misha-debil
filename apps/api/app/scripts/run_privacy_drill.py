"""Privacy deletion + log canary drill — writes evidence under artifacts/drills/."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.upload.safe_logging import DocumentSafeFilter


def _root() -> Path:
    return Path(__file__).resolve().parents[4]


def main() -> None:
    out_dir = _root() / "artifacts" / "drills"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Log canary: must not appear unredacted
    logger = logging.getLogger("dar.privacy_drill")
    logger.addFilter(DocumentSafeFilter())
    logger.setLevel(logging.INFO)
    records: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    h = Capture()
    logger.addHandler(h)
    canary = "CANARY_PASSPORT_4500_123456"
    logger.info("filename=secret.pdf extracted_text=%s", canary)
    logger.info("quote dump: «%s»", "x" * 40)

    leaked = any(canary in r for r in records) or any("extracted_text=" in r and canary in r for r in records)
    # Filter rewrites msg on extracted_text
    safe = (not leaked) and any("document_content_refused_in_logs" in r or "REDACTED" in r for r in records)

    evidence = {
        "drill": "privacy_deletion_and_log_canary",
        "at": datetime.now(UTC).isoformat(),
        "synthetic_user_id": str(uuid4()),
        "deletion_status_simulated": "deletion_requested",
        "export_status_simulated": "export_requested",
        "log_canary_safe": safe,
        "captured_log_samples": records[:5],
        "backup_deletion_policy": "BACKUP_DELETION_POLICY_NEEDS_REVIEW",
        "note": "Staging must attach signed ops evidence; this is local synthetic evidence only.",
    }
    path = out_dir / "deletion_log_canary.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path} log_canary_safe={safe}")
    raise SystemExit(0 if safe else 1)


if __name__ == "__main__":
    main()
