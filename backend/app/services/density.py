"""
backend/app/services/density.py
────────────────────────────────
Vehicle density calculation with rolling-average smoothing.

Density score  = (vehicle_count / max_capacity) * 100   → 0.0 … 100.0

Level thresholds
────────────────
   0 – 30   → "low"      (green)
  31 – 60   → "medium"   (yellow)
  61 – 80   → "high"     (orange)
  81 – 100  → "critical" (red)

Rolling average: sliding window of the last 10 per-lane density scores is
maintained inside DensityCalculator so frame-to-frame noise is smoothed out.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Tuple


# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_MAX_CAPACITY: int = 20
WINDOW_SIZE: int = 10

# (upper_bound_inclusive, level_name, hex_color)
_THRESHOLDS: list[tuple[float, str, str]] = [
    (30.0,  "low",      "#22c55e"),   # green
    (60.0,  "medium",   "#eab308"),   # yellow
    (80.0,  "high",     "#f97316"),   # orange
    (100.0, "critical", "#ef4444"),   # red
]


# ── Dataclass ──────────────────────────────────────────────────────────────────

@dataclass
class DensityReport:
    """Snapshot of the density state for both lanes at one point in time."""

    lane_a_count: int
    lane_b_count: int

    # Smoothed (rolling-average) density scores, 0.0–100.0
    lane_a_density: float
    lane_b_density: float

    lane_a_level: str          # "low" | "medium" | "high" | "critical"
    lane_b_level: str

    # Human-readable colour hints (hex)
    lane_a_color: str
    lane_b_color: str

    timestamp: datetime

    # Fraction of total density contributed by Lane A.
    # Useful for deciding which lane has the larger share of congestion.
    congestion_ratio: float    # lane_a_density / (lane_a_density + lane_b_density + 0.01)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _classify(score: float) -> Tuple[str, str]:
    """Return (level_name, hex_color) for a density *score* in [0, 100]."""
    for upper, level, color in _THRESHOLDS:
        if score <= upper:
            return level, color
    return "critical", "#ef4444"


def _raw_density(count: int, max_capacity: int) -> float:
    """Convert a raw vehicle count to a density percentage."""
    if max_capacity <= 0:
        return 0.0
    return min((count / max_capacity) * 100.0, 100.0)


# ── Main class ─────────────────────────────────────────────────────────────────

class DensityCalculator:
    """Stateful density calculator that maintains a rolling average per lane.

    Parameters
    ----------
    max_capacity : int
        Maximum number of vehicles considered 100 % for each lane.
    window_size : int
        Number of past readings kept in the sliding window for smoothing.
    """

    def __init__(
        self,
        max_capacity: int = DEFAULT_MAX_CAPACITY,
        window_size: int = WINDOW_SIZE,
    ) -> None:
        self.max_capacity = max_capacity
        self.window_size = window_size

        # Sliding windows store raw density percentages (0–100)
        self._window_a: Deque[float] = deque(maxlen=window_size)
        self._window_b: Deque[float] = deque(maxlen=window_size)

    # ── Public API ─────────────────────────────────────────────────────────────

    def update(self, lane_a_count: int, lane_b_count: int) -> DensityReport:
        """Feed new vehicle counts and get back a smoothed :class:`DensityReport`.

        Parameters
        ----------
        lane_a_count : int  – vehicles detected in Lane A this frame
        lane_b_count : int  – vehicles detected in Lane B this frame

        Returns
        -------
        DensityReport
        """
        # Compute raw scores for this frame
        raw_a = _raw_density(lane_a_count, self.max_capacity)
        raw_b = _raw_density(lane_b_count, self.max_capacity)

        # Push into rolling windows
        self._window_a.append(raw_a)
        self._window_b.append(raw_b)

        # Smoothed averages
        smooth_a = sum(self._window_a) / len(self._window_a)
        smooth_b = sum(self._window_b) / len(self._window_b)

        level_a, color_a = _classify(smooth_a)
        level_b, color_b = _classify(smooth_b)

        congestion_ratio = smooth_a / (smooth_a + smooth_b + 0.01)

        return DensityReport(
            lane_a_count=lane_a_count,
            lane_b_count=lane_b_count,
            lane_a_density=round(smooth_a, 2),
            lane_b_density=round(smooth_b, 2),
            lane_a_level=level_a,
            lane_b_level=level_b,
            lane_a_color=color_a,
            lane_b_color=color_b,
            timestamp=datetime.utcnow(),
            congestion_ratio=round(congestion_ratio, 4),
        )

    def reset(self) -> None:
        """Clear the rolling windows (e.g. when switching video sources)."""
        self._window_a.clear()
        self._window_b.clear()

    # ── Read-only window introspection (useful for tests / debugging) ──────────

    @property
    def window_a(self) -> list[float]:
        return list(self._window_a)

    @property
    def window_b(self) -> list[float]:
        return list(self._window_b)
