"""Create initial tables and TimescaleDB hypertables

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-16 00:00:00.000000 UTC

What this migration does
────────────────────────
1. Creates tables: intersections, density_readings, signal_events,
   emergency_records
2. Converts density_readings and signal_events into TimescaleDB
   hypertables (partitioned on the `time` column).
3. Adds a performance index on intersection_id + time for both
   hypertables.

TimescaleDB note
────────────────
  create_hypertable() is idempotent when if_not_exists=TRUE.
  If the extension is not installed the op.execute() call will raise;
  ensure `CREATE EXTENSION IF NOT EXISTS timescaledb;` has been run
  (the TimescaleDB Docker image does this automatically).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ─────────────────────────────────────────────────────────────────────────────
def upgrade() -> None:

    # ── 1. intersections ──────────────────────────────────────────────────────
    op.create_table(
        "intersections",
        sa.Column(
            "id",
            sa.String(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("lane_count", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_capacity_per_lane", sa.Integer(), nullable=False, server_default="20"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── 2. density_readings ───────────────────────────────────────────────────
    op.create_table(
        "density_readings",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column(
            "intersection_id",
            sa.String(),
            sa.ForeignKey("intersections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "time",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("lane_a_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lane_b_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lane_a_density", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lane_b_density", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lane_a_level", sa.String(20), nullable=False, server_default=sa.text("'low'")),
        sa.Column("lane_b_level", sa.String(20), nullable=False, server_default=sa.text("'low'")),
        sa.PrimaryKeyConstraint("id", "time"),
    )
    op.create_index(
        "ix_density_readings_intersection_time",
        "density_readings",
        ["intersection_id", "time"],
    )

    # ── 3. signal_events ──────────────────────────────────────────────────────
    op.create_table(
        "signal_events",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column(
            "intersection_id",
            sa.String(),
            sa.ForeignKey("intersections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "time",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("lane_a_green_seconds", sa.Float(), nullable=False),
        sa.Column("lane_b_green_seconds", sa.Float(), nullable=False),
        sa.Column(
            "is_emergency_override",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("optimization_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", "time"),
    )
    op.create_index(
        "ix_signal_events_intersection_time",
        "signal_events",
        ["intersection_id", "time"],
    )

    # ── 4. emergency_records ──────────────────────────────────────────────────
    op.create_table(
        "emergency_records",
        sa.Column(
            "id",
            sa.String(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("vehicle_id", sa.String(100), nullable=False),
        sa.Column("vehicle_type", sa.String(50), nullable=False, server_default=sa.text("'ambulance'")),
        sa.Column(
            "route",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "dispatch_time",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("resolved_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
    )
    op.create_index("ix_emergency_records_status", "emergency_records", ["status"])

    # ── 5. TimescaleDB hypertables ────────────────────────────────────────────
    # Requires TimescaleDB extension (pre-installed in timescale/timescaledb Docker image)
    op.execute(
        """
        SELECT create_hypertable(
            'density_readings',
            'time',
            if_not_exists => TRUE,
            migrate_data   => TRUE
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'signal_events',
            'time',
            if_not_exists => TRUE,
            migrate_data   => TRUE
        );
        """
    )

    # ── 6. Seed default intersections ─────────────────────────────────────────
    op.execute(
        """
        INSERT INTO intersections (id, name, latitude, longitude, lane_count, max_capacity_per_lane)
        VALUES
          ('INT-01', 'MG Road & Brigade Road',  12.9757, 77.6011, 2, 20),
          ('INT-02', 'Silk Board Junction',      12.9174, 77.6229, 2, 20),
          ('INT-03', 'KR Circle',               12.9762, 77.5713, 2, 20),
          ('INT-04', 'Hebbal Flyover',           13.0352, 77.5969, 2, 20)
        ON CONFLICT (id) DO NOTHING;
        """
    )


# ─────────────────────────────────────────────────────────────────────────────
def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("emergency_records")
    op.drop_table("signal_events")
    op.drop_table("density_readings")
    op.drop_table("intersections")
