"""Pydantic schemas for the health module."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class DependencyHealth(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: HealthStatus
    version: str
    dependencies: list[DependencyHealth] = Field(default_factory=list)


class LivenessResponse(BaseModel):
    status: HealthStatus = HealthStatus.OK
    app: str
    version: str