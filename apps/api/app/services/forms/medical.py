from __future__ import annotations

"""Medical section — approved sources only; never forge medical org documents."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.services.forms.pdf_memo import (
    ALLOWED_MEDICAL_ARTIFACTS,
    FORBIDDEN_MEDICAL_ARTIFACTS,
    MEDICAL_PDF_BANNER,
    MedicalPdfError,
    render_medical_memo_pdf,
)
from app.services.sources.registry import SourceRegistry, SourceState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MedicalError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


MEDICAL_SOURCE_HOST_MARKERS = (
    "minzdrav.gov.ru",
    "rospotrebnadzor.gov.ru",
    "gosuslugi.ru",  # only if later allowlisted as official portal; still needs approved snap
)


@dataclass
class MedicalProcedure:
    id: UUID
    slug: str
    title: str
    explanation: str
    applicable_to: str
    deadline_text: str  # only copied from approved source — never invented
    source_snapshot_id: UUID
    checklist: list[str]
    questionnaire_fields: list[str]
    status: str  # published|needs_review
    reviewed_at: datetime


@dataclass
class AuthorizedOrg:
    id: UUID
    name: str
    region_code: str
    source_snapshot_id: UUID
    valid_from: date
    valid_to: date | None
    reviewed_at: datetime
    status: str = "published"


class MedicalSectionService:
    def __init__(self, sources: SourceRegistry) -> None:
        self.sources = sources
        self.procedures: dict[UUID, MedicalProcedure] = {}
        self.orgs: dict[UUID, AuthorizedOrg] = {}
        self.by_proc_slug: dict[str, UUID] = {}

    def _assert_medical_source(self, snapshot_id: UUID, on: date) -> Any:
        snap = self.sources.snapshots.get(snapshot_id)
        if not snap or snap.state != SourceState.APPROVED:
            raise MedicalError("source_not_approved", "Medical content requires approved source", http_status=403)
        if not self.sources.applicable_on(snapshot_id, on):
            raise MedicalError("source_not_applicable", "Source not applicable on date", http_status=403)
        src = self.sources.sources[snap.source_id]
        host = (src.host or "").lower()
        organ = (src.organ or "").lower()
        ok_host = any(m in host for m in ("minzdrav", "rospotrebnadzor")) or "регион" in organ or "minzdrav" in organ or "роспотреб" in organ
        if not ok_host and "минздрав" not in organ and "роспотребнадзор" not in organ:
            # Allow explicit regional official organs tagged in organ field
            if "official_regional" not in (src.criticality or "") and "regional" not in organ:
                raise MedicalError(
                    "source_not_medical_authority",
                    "Source must be Minzdrav / Rospotrebnadzor / official regional organ",
                    http_status=403,
                )
        return snap

    def register_procedure(
        self,
        *,
        slug: str,
        title: str,
        explanation: str,
        applicable_to: str,
        deadline_text: str,
        source_snapshot_id: UUID,
        checklist: list[str],
        questionnaire_fields: list[str],
        reviewed_at: datetime | None = None,
    ) -> MedicalProcedure:
        self._assert_medical_source(source_snapshot_id, date.today())
        if not deadline_text.strip():
            raise MedicalError("deadline_required", "Deadline text must come from approved source")
        if slug in self.by_proc_slug:
            raise MedicalError("slug_exists", "Procedure slug exists", http_status=409)
        proc = MedicalProcedure(
            id=uuid4(),
            slug=slug,
            title=title,
            explanation=explanation,
            applicable_to=applicable_to,
            deadline_text=deadline_text.strip(),
            source_snapshot_id=source_snapshot_id,
            checklist=list(checklist),
            questionnaire_fields=list(questionnaire_fields),
            status="published",
            reviewed_at=reviewed_at or utcnow(),
        )
        self.procedures[proc.id] = proc
        self.by_proc_slug[slug] = proc.id
        return proc

    def register_org(
        self,
        *,
        name: str,
        region_code: str,
        source_snapshot_id: UUID,
        valid_from: date,
        valid_to: date | None,
        reviewed_at: datetime | None = None,
    ) -> AuthorizedOrg:
        self._assert_medical_source(source_snapshot_id, date.today())
        org = AuthorizedOrg(
            id=uuid4(),
            name=name,
            region_code=region_code.upper(),
            source_snapshot_id=source_snapshot_id,
            valid_from=valid_from,
            valid_to=valid_to,
            reviewed_at=reviewed_at or utcnow(),
        )
        self.orgs[org.id] = org
        return org

    def list_procedures(self) -> list[dict[str, Any]]:
        out = []
        for p in self.procedures.values():
            cite = self.sources.citation(p.source_snapshot_id, quote=p.title, on_date=date.today())
            out.append(
                {
                    "id": str(p.id),
                    "slug": p.slug,
                    "title": p.title,
                    "explanation": p.explanation,
                    "applicable_to": p.applicable_to,
                    "deadline_text": p.deadline_text,
                    "checklist": p.checklist,
                    "questionnaire_fields": p.questionnaire_fields,
                    "status": p.status,
                    "reviewed_at": p.reviewed_at.isoformat(),
                    "source": cite,
                    "warning": MEDICAL_PDF_BANNER,
                },
            )
        return out

    def list_orgs(self, *, region_code: str | None = None, as_of: date | None = None) -> list[dict[str, Any]]:
        on = as_of or date.today()
        out = []
        for o in self.orgs.values():
            if region_code and o.region_code != region_code.upper():
                continue
            if on < o.valid_from:
                continue
            if o.valid_to and on > o.valid_to:
                continue
            # Source must still be approved & applicable
            if not self.sources.applicable_on(o.source_snapshot_id, on):
                continue
            cite = self.sources.citation(o.source_snapshot_id, quote=o.name, on_date=on)
            out.append(
                {
                    "id": str(o.id),
                    "name": o.name,
                    "region_code": o.region_code,
                    "valid_from": o.valid_from.isoformat(),
                    "valid_to": o.valid_to.isoformat() if o.valid_to else None,
                    "reviewed_at": o.reviewed_at.isoformat(),
                    "source": cite,
                },
            )
        return out

    def generate_artifact_pdf(
        self,
        *,
        kind: str,
        title: str,
        body_lines: list[str],
        answers: dict[str, str] | None = None,
    ) -> bytes:
        """Backend gate: forbidden medical document kinds cannot be created."""
        k = (kind or "").strip().lower()
        if k in FORBIDDEN_MEDICAL_ARTIFACTS or k.startswith("official_"):
            raise MedicalPdfError(
                "forbidden_medical_artifact",
                f"Forbidden medical artifact kind: {kind}",
                http_status=403,
            )
        if k not in ALLOWED_MEDICAL_ARTIFACTS:
            raise MedicalPdfError(
                "forbidden_medical_artifact",
                f"Only questionnaire/checklist/memo allowed; got: {kind}",
                http_status=403,
            )
        return render_medical_memo_pdf(kind=k, title=title, body_lines=body_lines, answers=answers or {})
