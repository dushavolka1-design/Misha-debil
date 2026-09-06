"""Repair leftover app_state_blobs form catalogs: backup, validate, convert, rollback on error."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import delete, text

from app.models import AppStateBlob
from app.persistence.form_catalog_codec import catalog_fatal
from app.persistence.form_catalog_repo import backup_blob, catalog_tables_ready, convert_blob_forms
from app.persistence.serde import persistence_loads
from app.persistence.sync_db import sync_session

logger = logging.getLogger(__name__)


def _load_blob(namespace: str, blob_key: str) -> Any | None:
    with sync_session() as session:
        row = session.execute(
            text("SELECT value_json FROM app_state_blobs WHERE namespace = :ns AND blob_key = :key"),
            {"ns": namespace, "key": blob_key},
        ).first()
        if not row:
            return None
        val = row[0]
        if val is None:
            return None
        if isinstance(val, str):
            return persistence_loads(val)
        import json

        if isinstance(val, dict):
            return val
        return persistence_loads(json.dumps(val))


def _delete_blob(namespace: str, blob_key: str) -> None:
    with sync_session() as session:
        session.execute(
            delete(AppStateBlob).where(
                AppStateBlob.namespace == namespace,
                AppStateBlob.blob_key == blob_key,
            )
        )
        session.commit()


def repair_form_catalog_blobs() -> dict[str, Any]:
    """
    Convert legacy namespace=forms blobs into catalog_forms rows.
    On hard failure the original blob is left in place (rollback of conversion).
    Isolated records stay in quarantine; other rows still convert.
    """
    if not catalog_tables_ready():
        raise catalog_fatal("catalog_schema_missing")
    forms_blob = _load_blob("forms", "forms")
    if forms_blob is None:
        return {"converted": 0, "isolated": 0, "skipped": True}
    raw_blob = _load_blob("forms", "raw_store")
    backup_blob("forms", "forms", forms_blob)
    if raw_blob is not None:
        backup_blob("forms", "raw_store", raw_blob if isinstance(raw_blob, dict) else {"value": raw_blob})
    try:
        converted, isolated = convert_blob_forms(forms_blob, raw_blob)
    except Exception as exc:
        logger.error("form catalog blob convert failed; original blob kept: %s", exc)
        raise catalog_fatal("catalog_blob_convert_failed") from exc
    _delete_blob("forms", "forms")
    _delete_blob("forms", "raw_store")
    _delete_blob("forms", "by_slug")
    return {
        "converted": converted,
        "isolated": len(isolated),
        "skipped": False,
        "quarantine": isolated,
    }


def main() -> None:
    result = repair_form_catalog_blobs()
    logger.info("form catalog repair: %s", result)
    print(result)


if __name__ == "__main__":
    main()
