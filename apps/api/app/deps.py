from __future__ import annotations

import asyncio
from pathlib import Path

from dar.providers.factory import (
    build_email,
    build_kms,
    build_llm,
    build_malware,
    build_ocr,
    build_payment,
)
from dar.providers.ports import (
    EmailProvider,
    KMSProvider,
    LLMProvider,
    MalwareScanner,
    ObjectStorage,
    OCRProvider,
    PaymentProvider,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.file_storage import FileObjectStorage
from app.adapters.local_extract_ocr import LocalExtractOCRProvider
from app.adapters.s3_storage import S3ObjectStorage
from app.services.jobs.broker import JobBroker, RedisJobBroker, SqliteJobBroker
from app.settings import Settings


def _build_ocr(settings: Settings) -> OCRProvider:
    if settings.ocr_provider in {"local_extract", "local"}:
        return LocalExtractOCRProvider()
    return build_ocr(settings.ocr_provider, demo_mode=settings.demo_mode)


def _build_llm(settings: Settings) -> LLMProvider:
    return build_llm(settings.llm_provider, demo_mode=settings.demo_mode)


class ProviderBundle:
    def __init__(
        self,
        *,
        ocr: OCRProvider,
        llm: LLMProvider,
        storage: ObjectStorage,
        malware: MalwareScanner,
        payment: PaymentProvider,
        email: EmailProvider,
        kms: KMSProvider,
        queue: JobBroker,
        settings: Settings,
    ) -> None:
        self.ocr = ocr
        self.llm = llm
        self.storage = storage
        self.malware = malware
        self.payment = payment
        self.email = email
        self.kms = kms
        self.queue = queue
        self.redis = queue
        self.settings = settings


def _build_queue(settings: Settings) -> JobBroker:
    if settings.queue_backend == "sqlite" or settings.app_env == "desktop":
        data = Path(settings.data_dir or ".")
        return SqliteJobBroker(data / "docly.db", queue_name=settings.queue_name)
    import redis.asyncio as redis

    client = redis.from_url(settings.redis_url, decode_responses=True, protocol=2)
    return RedisJobBroker(client)


def build_providers(settings: Settings) -> ProviderBundle:
    storage: ObjectStorage
    if settings.object_storage_provider == "s3":
        storage = S3ObjectStorage(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )
    elif settings.object_storage_provider in {"file_object_storage", "file"}:
        root = Path(settings.data_dir or ".") / "objects"
        storage = FileObjectStorage(root=root)
    elif settings.object_storage_provider in {"fake_object_storage", "memory"}:
        from dar.providers.factory import build_object_storage

        storage = build_object_storage(settings.object_storage_provider)
    else:
        raise ValueError(f"Unsupported object storage: {settings.object_storage_provider}")

    return ProviderBundle(
        ocr=_build_ocr(settings),
        llm=_build_llm(settings),
        storage=storage,
        malware=build_malware(settings.malware_scanner_provider),
        payment=build_payment(settings.payment_provider),
        email=build_email(settings.email_provider),
        kms=build_kms(settings.kms_provider),
        queue=_build_queue(settings),
        settings=settings,
    )


async def check_database(session: AsyncSession) -> bool:
    result = await session.execute(text("SELECT 1"))
    return bool(result.scalar_one() == 1)


async def check_queue(bundle: ProviderBundle) -> bool:
    return bool(await bundle.queue.ping())


async def check_object_storage(bundle: ProviderBundle) -> bool:
    buckets = [
        bundle.settings.s3_bucket_originals,
        bundle.settings.s3_bucket_derived,
        bundle.settings.s3_bucket_reports,
        bundle.settings.s3_bucket_quarantine,
    ]
    results = await asyncio.gather(*(bundle.storage.head_bucket(bucket=b) for b in buckets))
    return all(results)
