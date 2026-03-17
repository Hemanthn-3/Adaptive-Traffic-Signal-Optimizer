"""
backend/app/models/schemas.py
───────────────────────────────
Pydantic v2 schemas for request validation and API responses.

Naming convention
─────────────────
  <Model>Base        – shared fields (no id, no server timestamps)
  <Model>Create      – what the client sends on POST
  <Model>Response    – what the API returns (includes id, timestamps)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Intersection
# ─────────────────────────────────────────────────────────────────────────────

class IntersectionBase(BaseModel):
    name: str = Field(..., example="Main St & 1st Ave")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    lane_count: int = Field(2, ge=1, le=10)
    max_capacity_per_lane: int = Field(20, ge=1)


class IntersectionCreate(IntersectionBase):
    pass


class IntersectionResponse(IntersectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class IntersectionListResponse(BaseModel):
    """Paginated list of intersections."""
    count: int
    page: int = 1
    page_size: int = 50
    data: List[IntersectionResponse]


# ─────────────────────────────────────────────────────────────────────────────
# DensityReading
# ─────────────────────────────────────────────────────────────────────────────

class DensityReadingBase(BaseModel):
    intersection_id: str
    lane_a_count: int = Field(..., ge=0)
    lane_b_count: int = Field(..., ge=0)
    lane_a_density: float = Field(..., ge=0.0, le=100.0)
    lane_b_density: float = Field(..., ge=0.0, le=100.0)
    lane_a_level: str = Field(..., pattern="^(low|medium|high|critical)$")
    lane_b_level: str = Field(..., pattern="^(low|medium|high|critical)$")


class DensityReadingCreate(DensityReadingBase):
    time: Optional[datetime] = None   # defaults to server time if omitted


class DensityReadingResponse(DensityReadingBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    time: datetime


class DensityDashboardResponse(BaseModel):
    """Latest density reading for every intersection – used by the dashboard."""
    total_intersections: int
    data: List[DensityReadingResponse]


# ─────────────────────────────────────────────────────────────────────────────
# SignalEvent
# ─────────────────────────────────────────────────────────────────────────────

class SignalEventBase(BaseModel):
    intersection_id: str
    lane_a_green_seconds: float = Field(..., ge=0)
    lane_b_green_seconds: float = Field(..., ge=0)
    is_emergency_override: bool = False
    optimization_reason: Optional[str] = None


class SignalEventCreate(SignalEventBase):
    time: Optional[datetime] = None


class SignalEventResponse(SignalEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    time: datetime


# ─────────────────────────────────────────────────────────────────────────────
# EmergencyRecord
# ─────────────────────────────────────────────────────────────────────────────

class EmergencyRecordBase(BaseModel):
    vehicle_id: str = Field(..., example="AMB-001")
    vehicle_type: str = Field("ambulance", example="ambulance")
    route: List[str] = Field(..., min_length=1, example=["INT-01", "INT-02", "INT-03"])


class EmergencyActivateRequest(EmergencyRecordBase):
    """Request body for POST /api/emergency/activate."""
    pass


class EmergencyRecordCreate(EmergencyRecordBase):
    dispatch_time: Optional[datetime] = None
    status: str = "active"


class EmergencyRecordResponse(EmergencyRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dispatch_time: datetime
    resolved_time: Optional[datetime] = None
    status: str


class EmergencyDeactivateRequest(BaseModel):
    event_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Generic paginated wrapper (reusable)
# ─────────────────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 50
    data: list
