"""Exercise real boto3 response shapes without contacting object storage."""

from io import BytesIO

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app.adapters.s3_storage import S3ObjectStorage


def storage() -> S3ObjectStorage:
    return S3ObjectStorage(
        endpoint_url="http://127.0.0.1:9",
        access_key="synthetic-test-access",
        secret_key="synthetic-test-secret",
        region="us-east-1",
    )


@pytest.mark.asyncio
async def test_put_retains_sdk_etag() -> None:
    adapter = storage()
    with Stubber(adapter._client) as stub:
        stub.add_response(
            "put_object",
            {"ETag": '"synthetic-etag"'},
            {"Bucket": "test-bucket", "Key": "test-key", "Body": b"payload", "ContentType": "application/pdf"},
        )
        result = await adapter.put_bytes(
            bucket="test-bucket", key="test-key", data=b"payload", content_type="application/pdf"
        )
        assert result.etag == '"synthetic-etag"'
        assert result.bucket == "test-bucket"
        assert result.key == "test-key"
        stub.assert_no_pending_responses()


@pytest.mark.asyncio
async def test_get_returns_bytes_and_closes_stream() -> None:
    adapter = storage()
    raw = BytesIO(b"payload")
    body = StreamingBody(raw, 7)
    with Stubber(adapter._client) as stub:
        stub.add_response(
            "get_object",
            {"Body": body},
            {"Bucket": "test-bucket", "Key": "test-key"},
        )
        assert await adapter.get_bytes(bucket="test-bucket", key="test-key") == b"payload"
        assert raw.closed
        stub.assert_no_pending_responses()


@pytest.mark.asyncio
async def test_get_closes_stream_after_sdk_read_error() -> None:
    from botocore.exceptions import IncompleteReadError

    adapter = storage()
    raw = BytesIO(b"short")
    body = StreamingBody(raw, 20)
    with Stubber(adapter._client) as stub:
        stub.add_response(
            "get_object",
            {"Body": body},
            {"Bucket": "test-bucket", "Key": "test-key"},
        )
        with pytest.raises(IncompleteReadError):
            await adapter.get_bytes(bucket="test-bucket", key="test-key")
        assert raw.closed
        stub.assert_no_pending_responses()
