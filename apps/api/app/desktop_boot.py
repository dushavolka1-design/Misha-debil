from __future__ import annotations

import json
import os
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine

from app.desktop_backup import backup_before_schema_change


def default_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME") or str(Path.cwd())
    return Path(local) / "Docly" / "data"


def apply_desktop_env(*, data_dir: Path | None = None, instance_token: str | None = None) -> Path:
    """Configure process env for standalone desktop profile. Does not touch production."""
    root = Path(data_dir) if data_dir is not None else default_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    (root / "objects").mkdir(parents=True, exist_ok=True)
    token = instance_token or os.environ.get("DOCLY_INSTANCE_TOKEN") or uuid4().hex
    db_path = (root / "docly.db").resolve()
    # SQLAlchemy URL: four slashes for absolute Windows paths.
    db_url = "sqlite+aiosqlite:///" + db_path.as_posix()

    os.environ["APP_ENV"] = "desktop"
    os.environ["DOCLY_PROFILE"] = "desktop"
    os.environ["DOCLY_DATA_DIR"] = str(root)
    os.environ["DOCLY_INSTANCE_TOKEN"] = token
    os.environ["DATABASE_URL"] = db_url
    os.environ["QUEUE_BACKEND"] = "sqlite"
    os.environ["QUEUE_NAME"] = os.environ.get("QUEUE_NAME") or "dar-jobs"
    os.environ["REDIS_URL"] = os.environ.get("REDIS_URL") or "redis://127.0.0.1:0/0"
    os.environ["OBJECT_STORAGE_PROVIDER"] = "file_object_storage"
    os.environ["OCR_PROVIDER"] = os.environ.get("OCR_PROVIDER") or "local_extract"
    os.environ["LLM_PROVIDER"] = os.environ.get("LLM_PROVIDER") or "unavailable"
    os.environ["ALLOW_FAKE_PROVIDERS"] = "true"
    os.environ["DEMO_MODE"] = os.environ.get("DEMO_MODE") or "false"
    os.environ["MALWARE_SCANNER_PROVIDER"] = os.environ.get("MALWARE_SCANNER_PROVIDER") or "fake_malware"
    os.environ["PAYMENT_PROVIDER"] = os.environ.get("PAYMENT_PROVIDER") or "fake_payment"
    os.environ["EMAIL_PROVIDER"] = os.environ.get("EMAIL_PROVIDER") or "fake_email"
    os.environ["KMS_PROVIDER"] = os.environ.get("KMS_PROVIDER") or "fake_kms"
    os.environ["S3_ENDPOINT_URL"] = os.environ.get("S3_ENDPOINT_URL") or "file://local"
    os.environ["S3_ACCESS_KEY"] = os.environ.get("S3_ACCESS_KEY") or "desktop"
    os.environ["S3_SECRET_KEY"] = os.environ.get("S3_SECRET_KEY") or "desktop"
    os.environ["S3_BUCKET_ORIGINALS"] = os.environ.get("S3_BUCKET_ORIGINALS") or "originals"
    os.environ["S3_BUCKET_DERIVED"] = os.environ.get("S3_BUCKET_DERIVED") or "derived"
    os.environ["S3_BUCKET_REPORTS"] = os.environ.get("S3_BUCKET_REPORTS") or "reports"
    os.environ["S3_BUCKET_QUARANTINE"] = os.environ.get("S3_BUCKET_QUARANTINE") or "quarantine"
    if not os.environ.get("SESSION_SECRET"):
        os.environ["SESSION_SECRET"] = "desktop_session_" + token[:24]
    return root


def migrate_sqlite(data_dir: Path) -> Path:
    from app.models import Base

    db_path = (data_dir / "docly.db").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    # Fail closed before any DDL when validation or a required backup fails.
    backup_before_schema_change(
        db_path,
        required_tables=set(Base.metadata.tables),
        required_columns={"users": {"display_name", "avatar_jpeg"}},
    )
    engine = create_engine("sqlite:///" + db_path.as_posix(), future=True)
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")}
            if "display_name" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN display_name VARCHAR(80)")
            if "avatar_jpeg" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar_jpeg BLOB")
    finally:
        engine.dispose()
    return db_path


def find_free_port(start: int, *, is_open: Callable[[int], bool] | None = None, limit: int = 40) -> int:
    checker = is_open or _port_in_use
    for offset in range(limit):
        port = start + offset
        if not checker(port):
            return port
    raise RuntimeError(f"no_free_port_from_{start}")


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def parse_instance_payload(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def is_our_instance(payload: dict[str, Any], *, expected_token: str) -> bool:
    if not expected_token:
        return False
    return payload.get("product") == "docly" and str(payload.get("instance_token") or "") == expected_token
