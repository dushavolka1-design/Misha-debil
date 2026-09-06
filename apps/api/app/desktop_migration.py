"""Offline PostgreSQL -> new SQLite desktop profile. Never upgrades the source.

Only the current model schema is accepted. An exported *plaintext* local object
root is required; S3 downloads, KMS decryption and legacy schema adapters are not
implicit. Stop all writers before invoking; the read-only snapshot cannot freeze
an external object store. Failed staging/lock artifacts are retained for review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, UniqueConstraint, create_engine, inspect, select
from sqlalchemy.engine import Connection, make_url

from app.desktop_migration_files import MigrationError, copy_inventory, inventory, object_name
from app.models import Base


def _normalized(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return {"datetime_utc": value.isoformat(timespec="microseconds")}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, uuid.UUID):
        return {"uuid": value.hex}
    if isinstance(value, (bytes, memoryview)):
        return {"bytes": bytes(value).hex()}
    if isinstance(value, dict):
        return {str(k): _normalized(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normalized(v) for v in value]
    return value


def _row_digest(row: Any) -> int:
    # Order-independent table accumulation avoids PostgreSQL/SQLite collation differences.
    encoded = json.dumps(_normalized(dict(row)), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest(), "big")


def _fingerprint(conn: Connection, table: Table) -> tuple[int, str]:
    count, digest = 0, 0
    with conn.execute(select(table).execution_options(yield_per=256)) as rows:
        for row in rows.mappings():
            count += 1
            digest = (digest + _row_digest(row)) % (1 << 256)
    return count, f"{digest:064x}"


def _schema(conn: Connection, metadata: MetaData) -> None:
    """Reject drift, including extra columns/tables and missing FK/unique/indexes."""
    reader = inspect(conn)
    tables = set(reader.get_table_names(schema="public"))
    if tables - {"alembic_version"} != set(metadata.tables):
        raise MigrationError("unsupported_source_tables")
    if reader.get_view_names(schema="public") or reader.get_materialized_view_names(schema="public"):
        raise MigrationError("unsupported_source_views")
    for table in metadata.sorted_tables:
        columns = {c["name"]: c for c in reader.get_columns(table.name, schema="public")}
        if set(columns) != set(table.columns.keys()):
            raise MigrationError("unsupported_source_columns")
        for col in table.columns:
            actual = columns[col.name]
            expected_type = str(col.type.compile(dialect=conn.dialect)).replace("FLOAT", "DOUBLE PRECISION")
            actual_type = str(actual["type"].compile(dialect=conn.dialect)).replace("FLOAT", "DOUBLE PRECISION")
            if actual_type != expected_type or actual["nullable"] != col.nullable:
                raise MigrationError("unsupported_source_column_type")
            if actual.get("computed") or actual.get("identity"):
                raise MigrationError("unsupported_generated_column")
        actual_pk = reader.get_pk_constraint(table.name, schema="public")["constrained_columns"]
        if actual_pk != list(table.primary_key.columns.keys()):
            raise MigrationError("source_primary_key_mismatch")
        expected_unique = {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, UniqueConstraint)}
        actual_unique = {tuple(c["column_names"]) for c in reader.get_unique_constraints(table.name, schema="public")}
        if expected_unique != actual_unique:
            raise MigrationError("source_unique_constraint_mismatch")
        expected_fk = {(tuple(f.column_keys), next(iter(f.elements)).column.table.name,
                        tuple(e.column.name for e in f.elements), f.ondelete or "NO ACTION")
                       for f in table.foreign_key_constraints}
        reflected_fk = reader.get_foreign_keys(table.name, schema="public")
        actual_fk = {(tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]),
                      f.get("options", {}).get("ondelete", "NO ACTION")) for f in reflected_fk}
        if actual_fk != expected_fk or any(f.get("referred_schema") not in (None, "public") for f in reflected_fk):
            raise MigrationError("source_foreign_key_mismatch")
        if any(f.get("options", {}).get(k) for f in reflected_fk for k in ("onupdate", "deferrable", "initially")):
            raise MigrationError("unsupported_foreign_key_options")
        actual_indexes = {i["name"]: i for i in reader.get_indexes(table.name, schema="public")
                          if not i.get("duplicates_constraint")}
        if set(actual_indexes) != {i.name for i in table.indexes}:
            raise MigrationError("source_index_mismatch")
        for index in table.indexes:
            if index.name is None:
                raise MigrationError("unnamed_model_index")
            actual_index = actual_indexes[index.name]
            if (list(index.columns.keys()) != actual_index["column_names"]
                    or bool(index.unique) != bool(actual_index["unique"])):
                raise MigrationError("source_index_columns_mismatch")
            sorting = actual_index.get("column_sorting", {})
            for column, expression in zip(index.columns, index.expressions, strict=True):
                name = column.name
                expected_desc = str(expression).endswith(" DESC")
                if ("desc" in sorting.get(name, ())) != expected_desc:
                    raise MigrationError("source_index_order_mismatch")
            options = actual_index.get("dialect_options", {})
            if any(options.get(k) for k in ("postgresql_where", "postgresql_include", "postgresql_ops")):
                raise MigrationError("unsupported_source_index")
        if reader.get_check_constraints(table.name, schema="public"):
            raise MigrationError("unsupported_source_check_constraint")
    # Hidden RLS rows must not appear to be a complete successful migration.
    if conn.exec_driver_sql("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                            "WHERE n.nspname='public' AND (c.relrowsecurity OR c.relforcerowsecurity)").scalar_one():
        raise MigrationError("row_level_security_rejected")
    triggers = conn.exec_driver_sql(
        "SELECT c.relname, t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal"
    ).all()
    if any(tuple(t) != ("consent_events", "trg_consent_events_no_update") for t in triggers):
        raise MigrationError("unsupported_source_trigger")


def _references(conn: Connection, objects: dict[str, tuple[int, str]]) -> None:
    def require(bucket: str, key: str, digest: str, size: int | None = None) -> None:
        path = object_name(bucket + "/" + key)
        if path not in objects:
            raise MigrationError("referenced_object_missing")
        fingerprint = objects[path]
        if fingerprint[1] != digest or (size is not None and fingerprint[0] != size):
            raise MigrationError("referenced_object_mismatch")

    files = Base.metadata.tables["document_files"]
    for row in conn.execute(select(files)).mappings():
        if row["erased_at"] is not None:
            continue  # Preserve both metadata and any orphan bytes; never erase here.
        if row["dek_id"] or row["wrapped_dek"]:
            raise MigrationError("encrypted_object_requires_explicit_adapter")
        require(row["bucket"], row["object_key"], row["content_hash"], row["size_bytes"])
    snapshots = Base.metadata.tables["source_snapshots"]
    for row in conn.execute(select(snapshots)).mappings():
        require(row["storage_bucket"], row["storage_key"], row["content_hash"])
    legal = Base.metadata.tables["legal_documents"]
    for row in conn.execute(select(legal)).mappings():
        path = object_name(row["body_path"])
        if path not in objects or objects[path][1] != row["content_hash"]:
            raise MigrationError("legal_body_missing_or_mismatched")


def _fsync_directory(path: Path) -> None:
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def migrate_postgres(source_url: str, source_objects: Path, destination: Path, *, offline: bool = False) -> Path:
    """Activate a new profile only after full validation; never replace any profile.

    Caller must stop DB/object writers and desktop readers. `offline=True` is an
    explicit operational acknowledgement, not a distributed lock. Retry after a
    crash fails closed on the retained lock; inspect/quarantine staging manually.
    """
    if not offline:
        raise MigrationError("offline_acknowledgement_required")
    url = make_url(source_url)
    if url.drivername != "postgresql+psycopg" or url.query:
        raise MigrationError("plain_psycopg_postgresql_url_required")
    source_objects = Path(source_objects).absolute()
    destination = Path(destination).absolute()
    # Resolve ancestors, not just the leaf, to reject path aliases/reparse roots.
    for root in (source_objects, destination.parent):
        if root.resolve() != root or not root.is_dir():
            raise MigrationError("plain_existing_parent_required")
    if (source_objects == destination or source_objects in destination.parents
            or destination in source_objects.parents):
        raise MigrationError("source_destination_overlap")
    if destination.exists() or destination.is_symlink():
        raise MigrationError("destination_already_exists")
    lock = destination.with_name(destination.name + ".migration.lock")
    stage = destination.with_name(destination.name + ".staging-" + uuid.uuid4().hex)
    # Never automatically steal a stale lock or delete unverified staging files.
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(stage.name + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    stage.mkdir(mode=0o700)
    _fsync_directory(stage.parent)
    source = create_engine(url, isolation_level="REPEATABLE READ",
                           connect_args={"options": "-c default_transaction_read_only=on -c timezone=UTC"})
    target = create_engine("sqlite:///" + (stage / "docly.db").as_posix())
    try:
        with source.connect() as src, src.begin():
            src.exec_driver_sql("SET TRANSACTION READ ONLY")
            src.exec_driver_sql("SET LOCAL search_path TO public, pg_catalog")
            if src.exec_driver_sql("SHOW transaction_read_only").scalar_one() != "on":
                raise MigrationError("source_not_read_only")
            _schema(src, Base.metadata)
            objects = inventory(source_objects)
            _references(src, objects)
            copy_inventory(source_objects, stage / "objects", objects)
            Base.metadata.create_all(target)
            manifest: dict[str, Any] = {"format": 1, "state": "verified", "timestamp_policy": "UTC-naive SQLite",
                                        "objects": objects, "tables": {}, "source_read_only": True}
            if "alembic_version" in inspect(src).get_table_names(schema="public"):
                revisions = src.exec_driver_sql("SELECT version_num FROM public.alembic_version").scalars()
                manifest["source_alembic_versions"] = list(revisions)
            with target.begin() as dst:
                dst.exec_driver_sql("PRAGMA foreign_keys=OFF")
                for table in Base.metadata.sorted_tables:
                    with src.execute(select(table).execution_options(yield_per=256)) as rows:
                        for batch in rows.mappings().partitions(256):
                            values = []
                            for row in batch:
                                converted = dict(row)
                                for key, value in converted.items():
                                    if isinstance(value, datetime) and value.tzinfo is not None:
                                        converted[key] = value.astimezone(UTC).replace(tzinfo=None)
                                values.append(converted)
                            dst.execute(table.insert(), values)
                    expected = _fingerprint(src, table)
                    if _fingerprint(dst, table) != expected:
                        raise MigrationError("table_content_mismatch")
                    manifest["tables"][table.name] = expected
                if dst.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                    raise MigrationError("target_foreign_key_violation")
                if dst.exec_driver_sql("PRAGMA integrity_check").scalar_one() != "ok":
                    raise MigrationError("target_integrity_failed")
                for operation in ("UPDATE", "DELETE"):
                    dst.exec_driver_sql(f"CREATE TRIGGER consent_no_{operation.lower()} BEFORE {operation} "
                                        "ON consent_events BEGIN SELECT RAISE(ABORT, 'consent_events are append-only'); END")
            # Reopen after commit; validate durable rows, not only uncommitted buffers.
            with target.connect() as dst:
                for table in Base.metadata.sorted_tables:
                    if _fingerprint(dst, table) != manifest["tables"][table.name]:
                        raise MigrationError("committed_content_mismatch")
                if dst.exec_driver_sql("PRAGMA integrity_check").scalar_one() != "ok":
                    raise MigrationError("committed_integrity_failed")
            if inventory(source_objects) != objects or inventory(stage / "objects") != objects:
                raise MigrationError("final_object_inventory_changed")
        target.dispose()
        with (stage / "migration-manifest.json").open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, sort_keys=True, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        with (stage / "docly.db").open("rb") as db:
            os.fsync(db.fileno())
        for directory, _, _ in os.walk(stage, topdown=False):
            _fsync_directory(Path(directory))
        if destination.exists() or destination.is_symlink():
            raise MigrationError("destination_appeared_during_migration")
        stage.rename(destination)  # Same filesystem, all DB+object bytes become visible together.
        _fsync_directory(destination.parent)
        lock.unlink()
        _fsync_directory(destination.parent)
        return destination
    finally:
        source.dispose()
        target.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-objects", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    # Credentials never enter command arguments, manifests or printed exceptions.
    try:
        migrate_postgres(os.environ["DOCLY_MIGRATION_SOURCE_URL"], args.source_objects, args.destination,
                         offline=args.offline)
    except Exception:
        raise SystemExit("migration_failed; source untouched; inspect retained staging and lock") from None
    print("migration_verified_and_activated")


if __name__ == "__main__":
    main()
