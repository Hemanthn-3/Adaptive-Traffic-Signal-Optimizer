"""
backend/app/models/database.py
────────────────────────────────
SQLAlchemy ORM models for the traffic management system.

TimescaleDB
───────────
DensityReading and SignalEvent are designed as TimescaleDB hypertables.
The `time` column is the partition key on both tables.  The hypertable
conversion is done inside the Alembic migration (not here) so the schema
is compatible with plain PostgreSQL during unit tests.

UUID primary keys
─────────────────
All tables use server-generated UUIDs (gen_random_uuid()) so IDs are
predictable-length strings and portable across environments.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


# ── Base ───────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Helper: generate UUID string on the Python side ───────────────────────────
def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# 1. Intersection
# ─────────────────────────────────────────────────────────────────────────────
class Intersection(Base):
    """A physical road intersection with two monitored lanes."""

    __tablename__ = "intersections"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
        server_default=func.gen_random_uuid().cast(String),
    )
    name = Column(String(200), nullable=False, comment="e.g. 'Main St & 1st Ave'")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    lane_count = Column(Integer, nullable=False, default=2)
    max_capacity_per_lane = Column(Integer, nullable=False, default=20)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships (lazy='dynamic' keeps subqueries efficient for large sets)
    density_readings = relationship(
        "DensityReading", back_populates="intersection", cascade="all, delete-orphan"
    )
    signal_events = relationship(
        "SignalEvent", back_populates="intersection", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Intersection id={self.id!r} name={self.name!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 2. DensityReading  ← TimescaleDB hypertable (partition on `time`)
# ─────────────────────────────────────────────────────────────────────────────
class DensityReading(Base):
    """
    Per-frame vehicle density snapshot.

    One row is inserted every N frames (configurable) by the video-processing
    pipeline.  The `time` column is the TimescaleDB partition key.
    """

    __tablename__ = "density_readings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    intersection_id = Column(
        UUID(as_uuid=False),
        ForeignKey("intersections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="TimescaleDB partition key",
    )

    lane_a_count = Column(Integer, nullable=False, default=0)
    lane_b_count = Column(Integer, nullable=False, default=0)
    lane_a_density = Column(Float, nullable=False, default=0.0)
    lane_b_density = Column(Float, nullable=False, default=0.0)
    lane_a_level = Column(String(20), nullable=False, default="low")   # low/medium/high/critical
    lane_b_level = Column(String(20), nullable=False, default="low")

    intersection = relationship("Intersection", back_populates="density_readings")

    def __repr__(self) -> str:
        return (
            f"<DensityReading intersection={self.intersection_id!r} "
            f"time={self.time} A={self.lane_a_density:.1f}% B={self.lane_b_density:.1f}%>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. SignalEvent  ← TimescaleDB hypertable (partition on `time`)
# ─────────────────────────────────────────────────────────────────────────────
class SignalEvent(Base):
    """
    Record of every signal-timing change at an intersection.

    Captured both from the adaptive optimizer and from manual admin overrides.
    The `time` column is the TimescaleDB partition key.
    """

    __tablename__ = "signal_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    intersection_id = Column(
        UUID(as_uuid=False),
        ForeignKey("intersections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="TimescaleDB partition key",
    )

    lane_a_green_seconds = Column(Float, nullable=False)
    lane_b_green_seconds = Column(Float, nullable=False)
    is_emergency_override = Column(Boolean, nullable=False, default=False)
    optimization_reason = Column(Text, nullable=True)

    intersection = relationship("Intersection", back_populates="signal_events")

    def __repr__(self) -> str:
        return (
            f"<SignalEvent intersection={self.intersection_id!r} "
            f"time={self.time} emergency={self.is_emergency_override}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. EmergencyRecord
# ─────────────────────────────────────────────────────────────────────────────
class EmergencyRecord(Base):
    """
    Persistent log of every emergency green-corridor event.

    The `id` field mirrors the `event_id` used by GreenCorridorService so
    records can be cross-referenced with Redis state without a join.
    """

    __tablename__ = "emergency_records"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
        comment="Matches GreenCorridorService event_id",
    )
    vehicle_id = Column(String(100), nullable=False)
    vehicle_type = Column(String(50), nullable=False, default="ambulance")
    route = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Ordered list of intersection IDs",
    )
    dispatch_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active/completed/cancelled

    def __repr__(self) -> str:
        return (
            f"<EmergencyRecord id={self.id!r} vehicle={self.vehicle_id!r} "
            f"status={self.status!r}>"
        )
