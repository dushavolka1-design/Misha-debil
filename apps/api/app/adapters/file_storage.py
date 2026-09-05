from __future__ import annotations

from pathlib import Path

from dar.providers.ports import ObjectStorage, StoredObject


class FileObjectStorage(ObjectStorage):
    """Durable local object storage for desktop profile."""

    name = "file_object_storage"

    def __init__(self, *, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, bucket: str, key: str) -> Path:
        safe_key = key.replace("\\", "/").lstrip("/")
        path = (self._root / bucket / safe_key).resolve()
        if self._root.resolve() not in path.parents and path != self._root.resolve():
            raise ValueError("invalid_object_key")
        return path

    async def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        _ = content_type
        path = self._path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredObject(bucket=bucket, key=key, etag=str(len(data)))

    async def get_bytes(self, *, bucket: str, key: str) -> bytes:
        return self._path(bucket, key).read_bytes()

    async def delete_object(self, *, bucket: str, key: str) -> None:
        path = self._path(bucket, key)
        if path.is_file():
            path.unlink()

    async def head_bucket(self, *, bucket: str) -> bool:
        (self._root / bucket).mkdir(parents=True, exist_ok=True)
        return True
