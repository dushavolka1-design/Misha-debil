from __future__ import annotations

import asyncio

import boto3
from botocore.client import Config
from dar.providers.ports import ObjectStorage, StoredObject


class S3ObjectStorage(ObjectStorage):
    name = "s3"

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str,
    ) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    async def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        def _put() -> str | None:
            response = self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return response.get("ETag")

        etag = await asyncio.to_thread(_put)
        return StoredObject(bucket=bucket, key=key, etag=etag)

    async def get_bytes(self, *, bucket: str, key: str) -> bytes:
        def _get() -> bytes:
            obj = self._client.get_object(Bucket=bucket, Key=key)
            body = obj["Body"]
            try:
                data = body.read()
                if not isinstance(data, bytes):
                    raise TypeError("S3 object body must contain bytes")
                return data
            finally:
                body.close()

        return await asyncio.to_thread(_get)

    async def delete_object(self, *, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=bucket, Key=key)

    async def head_bucket(self, *, bucket: str) -> bool:
        def _head() -> bool:
            self._client.head_bucket(Bucket=bucket)
            return True

        try:
            return await asyncio.to_thread(_head)
        except Exception:
            return False
