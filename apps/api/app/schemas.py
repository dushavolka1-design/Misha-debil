from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class InstanceResponse(BaseModel):
    product: str = "docly"
    instance_token: str
    pid: int
    profile: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    env: str


class ReadinessChecks(BaseModel):
    database: bool
    queue: bool
    object_storage: bool
    catalog: bool
    font: bool = True
    generation: bool = True


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks


class PublicConfigResponse(BaseModel):
    demo_mode: bool
    max_analysis_pages: int
    ocr_provider: str
    llm_provider: str
