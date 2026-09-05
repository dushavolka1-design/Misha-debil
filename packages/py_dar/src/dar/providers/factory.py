from __future__ import annotations

from dar.providers.fake import (
    FakeEmailProvider,
    FakeKMSProvider,
    FakeLLMProvider,
    FakeMalwareScanner,
    FakeOCRProvider,
    FakePaymentProvider,
    InMemoryObjectStorage,
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

FAKE_PROVIDER_NAMES = frozenset(
    {
        "fake_ocr",
        "fake_llm",
        "fake_object_storage",
        "fake_malware",
        "fake_payment",
        "fake_email",
        "fake_kms",
    },
)


class ProductionFakeProviderError(RuntimeError):
    """Raised when fake providers are requested outside local/test."""


def assert_providers_allowed(*, app_env: str, allow_fake: bool, selected: list[str]) -> None:
    fakes = [name for name in selected if name in FAKE_PROVIDER_NAMES or name.startswith("fake_")]
    if not fakes:
        return
    if app_env == "production" or not allow_fake:
        raise ProductionFakeProviderError(
            "Fake providers are forbidden in production (and when ALLOW_FAKE_PROVIDERS=false): "
            + ", ".join(sorted(set(fakes))),
        )


def build_ocr(name: str, *, demo_mode: bool = False) -> OCRProvider:
    if name == "fake_ocr":
        if not demo_mode:
            raise ValueError("fake_ocr requires DEMO_MODE=true")
        return FakeOCRProvider()
    if name == "ru_private_ocr":
        from dar.providers.ru_private_ocr import RuPrivateOCRProvider

        return RuPrivateOCRProvider()
    raise ValueError(f"Unknown OCR provider: {name}")


def build_llm(name: str, *, demo_mode: bool = False) -> LLMProvider:
    if name == "fake_llm":
        if not demo_mode:
            from dar.providers.unavailable_llm import UnavailableLLMProvider

            return UnavailableLLMProvider()
        return FakeLLMProvider()
    if name in {"unavailable", "local_rules", "none"}:
        from dar.providers.unavailable_llm import UnavailableLLMProvider

        return UnavailableLLMProvider()
    if name == "ru_private_llm":
        from dar.providers.ru_private_llm import RuPrivateLLMProvider

        return RuPrivateLLMProvider()
    raise ValueError(f"Unknown LLM provider: {name}")


def build_malware(name: str) -> MalwareScanner:
    if name == "fake_malware":
        return FakeMalwareScanner()
    raise ValueError(f"Unknown malware scanner: {name}")


def build_payment(name: str) -> PaymentProvider:
    if name == "fake_payment":
        return FakePaymentProvider()
    if name in {"ru_payment_sandbox", "ru_sandbox", "yookassa_sandbox"}:
        from dar.providers.ru_payment_sandbox import RuPaymentSandboxProvider

        return RuPaymentSandboxProvider(live_mode=False)
    if name in {"ru_payment_live", "yookassa"}:
        # Will raise until credentials + contract — intentional
        from dar.providers.ru_payment_sandbox import RuPaymentSandboxProvider

        return RuPaymentSandboxProvider(live_mode=True)
    raise ValueError(f"Unknown payment provider: {name}")


def build_email(name: str) -> EmailProvider:
    if name == "fake_email":
        return FakeEmailProvider()
    raise ValueError(f"Unknown email provider: {name}")


def build_kms(name: str) -> KMSProvider:
    if name == "fake_kms":
        return FakeKMSProvider()
    raise ValueError(f"Unknown KMS provider: {name}")


def build_object_storage(name: str) -> ObjectStorage:
    if name in {"fake_object_storage", "memory"}:
        return InMemoryObjectStorage()
    raise ValueError(
        f"Object storage '{name}' must be constructed by the app (e.g. s3 adapter)",
    )
