"""Prompt 5: complete analyzer/generator user scenarios."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from dar.providers.unavailable_llm import UnavailableLLMProvider

from app.services.analysis.pipeline import AnalysisError, AnalysisPipelineService, AnalysisStore
from app.adapters.local_extract_ocr import LocalExtractOCRProvider


def _pdf(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_llm_unavailable_keeps_local_facts_and_capability_flag() -> None:
    pipeline = AnalysisPipelineService(
        AnalysisStore(),
        ocr=LocalExtractOCRProvider(),
        llm=UnavailableLLMProvider(),
    )
    run = pipeline.start_run(document_id=uuid4(), user_id=uuid4(), tenant_id=uuid4())

    async def _run() -> None:
        await pipeline.execute(
            run.id,
            file_bytes=_pdf("ДОГОВОР аренды 150 000 руб 01.09.2026"),
            detected_type="pdf",
            content_type="application/pdf",
            demo_mode=False,
        )

    asyncio.run(_run())
    stored = pipeline.store.runs[run.id]
    assert stored.llm_available is False
    local = [f for f in stored.findings if f.entity_type != "analysis.capability"]
    caps = [f for f in stored.findings if f.entity_type == "analysis.capability"]
    assert local, "локальное извлечение должно сохраниться"
    assert caps, "нужно отдельно показать недоступный расширенный анализ"
    assert stored.local_steps
    assert "ocr" in stored.local_steps
    assert stored.status.value == "ready"


def test_delete_purges_analysis_runs() -> None:
    store = AnalysisStore()
    pipeline = AnalysisPipelineService(
        store,
        ocr=LocalExtractOCRProvider(),
        llm=UnavailableLLMProvider(),
    )
    user = uuid4()
    doc = uuid4()
    run = pipeline.start_run(document_id=doc, user_id=user, tenant_id=uuid4())
    assert pipeline.get_run(run.id, user).id == run.id
    pipeline.purge_for_document(doc, user)
    with pytest.raises(AnalysisError) as exc:
        pipeline.get_run(run.id, user)
    assert exc.value.http_status == 404
    assert store.by_document.get(doc) in (None, [])


def test_evaluate_survives_dict_source_records() -> None:
    from app.services.entry.engine import EntryWizardService, Questionnaire
    from app.services.sources.registry import SourceRegistry

    registry = SourceRegistry()
    leftover_id = uuid4()
    registry.sources[leftover_id] = {"id": leftover_id, "snapshots": []}
    service = EntryWizardService(registry)
    snap = service.evaluate(Questionnaire(citizenship="UZ", purpose="tourism", planned_stay_days=30))
    assert snap.stages
    assert snap.disclaimer


def test_checklist_pdf_is_informational_with_marking() -> None:
    from app.services.entry.checklist_pdf import CHECKLIST_BANNER, render_checklist_pdf

    pdf = render_checklist_pdf(
        title="Чеклист уведомления о прибытии",
        steps=["Подготовить паспорт", "Заполнить уведомление"],
        documents=["Паспорт", "Миграционная карта"],
        official_source="https://publication.pravo.gov.ru/example",
        reviewed_at="2026-08-01",
    )
    assert pdf.startswith(b"%PDF")
    assert CHECKLIST_BANNER.encode("utf-8") in pdf or CHECKLIST_BANNER.encode("latin-1", "replace") in pdf
    lower = pdf.lower()
    assert b"informational" in lower or "информационн".encode("utf-8") in pdf
    assert b"/Encrypt" not in pdf


def test_forms_catalog_fatal_is_503_with_correlation(tmp_path) -> None:
    from pathlib import Path

    from fastapi.testclient import TestClient

    from app.desktop_boot import apply_desktop_env, migrate_sqlite
    from app.db import get_engine, get_session_factory
    from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
    from app.settings import get_settings

    data = Path(tmp_path) / "data"
    data.mkdir()
    apply_desktop_env(data_dir=data, instance_token="p5-token")
    migrate_sqlite(data)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as client:
        client.app.state.catalog_persistence_error = {
            "code": "catalog_load_failed",
            "detail": "Каталог шаблонов повреждён.",
            "correlation_id": "corr-p5",
        }
        res = client.get("/forms")
        assert res.status_code == 503
        assert res.status_code != 500
        body = res.json()["detail"]
        assert body["code"] == "catalog_load_failed"
        assert body["correlation_id"] == "corr-p5"
