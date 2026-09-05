from __future__ import annotations

import pytest
from dar.providers.factory import ProductionFakeProviderError, assert_providers_allowed


def test_fake_providers_forbidden_in_production() -> None:
    with pytest.raises(ProductionFakeProviderError):
        assert_providers_allowed(
            app_env="production",
            allow_fake=False,
            selected=["fake_ocr", "s3"],
        )


def test_fake_providers_allowed_in_local() -> None:
    assert_providers_allowed(
        app_env="local",
        allow_fake=True,
        selected=["fake_ocr", "fake_llm", "fake_malware"],
    )
