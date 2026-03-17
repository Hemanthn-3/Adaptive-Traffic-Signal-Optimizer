"""
backend/app/services/optimizer.py
───────────────────────────────────
Adaptive signal-timing optimizer.

Algorithm
─────────
  total_density = lane_a_density + lane_b_density

  if total_density == 0:
      lane_a_green = 30   # equal split
      lane_b_green = 30
  else:
      lane_a_green = max(10, min(50, (lane_a_density / total_density) * 60))
      lane_b_green = 60 - lane_a_green

  Red time for each lane = the other lane's green time
  (simplified two-phase cycle, yellow ignored for brevity).

The dataclass SignalTiming captures the full output.  An
is_emergency_override flag lets emergency-corridor logic bypass the
normal algorithm and set arbitrary timings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# ── Defaults (override via constructor) ────────────────────────────────────────
BASE_CYCLE_SECONDS: float = 60.0
MIN_GREEN: float = 10.0
MAX_GREEN: float = 50.0
DEFAULT_GREEN: float = 30.0


# ── Dataclass ──────────────────────────────────────────────────────────────────

@dataclass
class SignalTiming:
    """Complete timing plan for one intersection cycle."""

    intersection_id: str

    lane_a_green_seconds: float
    lane_b_green_seconds: float

    # Red = the full time the other lane is green (two-phase model)
    lane_a_red_seconds: float
    lane_b_red_seconds: float

    cycle_time: float              # total cycle length in seconds

    optimization_reason: str       # plain-English explanation
    created_at: datetime

    is_emergency_override: bool = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_optimization_reason(lane_a_density: float, lane_b_density: float) -> str:
    """Return a plain-English explanation of the timing decision.

    Examples
    --------
    >>> get_optimization_reason(72.0, 34.0)
    "Lane A is 72.0% full vs Lane B at 34.0%. Extending Lane A green by 12s."

    >>> get_optimization_reason(0.0, 0.0)
    "No traffic detected. Defaulting to equal green time (30s each)."

    >>> get_optimization_reason(30.0, 30.0)
    "Equal congestion in both lanes (30.0% each). Splitting green time evenly."
    """
    total = lane_a_density + lane_b_density

    if total == 0.0:
        return "No traffic detected. Defaulting to equal green time (30s each)."

    if abs(lane_a_density - lane_b_density) < 1.0:
        return (
            f"Equal congestion in both lanes ({lane_a_density:.1f}% each). "
            "Splitting green time evenly."
        )

    # Compute how many extra seconds the denser lane gets vs the 30s baseline
    a_green = max(MIN_GREEN, min(MAX_GREEN, (lane_a_density / total) * BASE_CYCLE_SECONDS))
    extension = abs(a_green - DEFAULT_GREEN)

    if lane_a_density > lane_b_density:
        return (
            f"Lane A is {lane_a_density:.1f}% full vs Lane B at {lane_b_density:.1f}%. "
            f"Extending Lane A green by {extension:.0f}s."
        )
    else:
        return (
            f"Lane B is {lane_b_density:.1f}% full vs Lane A at {lane_a_density:.1f}%. "
            f"Extending Lane B green by {extension:.0f}s."
        )


# ── Main class ─────────────────────────────────────────────────────────────────

class SignalOptimizer:
    """Compute adaptive green-time splits from per-lane density scores.

    Parameters
    ----------
    base_cycle : float
        Total cycle time in seconds (default 60).
    min_green : float
        Floor for any single lane's green phase (default 10 s).
    max_green : float
        Ceiling for any single lane's green phase (default 50 s).
    """

    def __init__(
        self,
        base_cycle: float = BASE_CYCLE_SECONDS,
        min_green: float = MIN_GREEN,
        max_green: float = MAX_GREEN,
    ) -> None:
        self.base_cycle = base_cycle
        self.min_green = min_green
        self.max_green = max_green

    # ── Public API ─────────────────────────────────────────────────────────────

    def compute(
        self,
        intersection_id: str,
        lane_a_density: float,
        lane_b_density: float,
    ) -> SignalTiming:
        """Compute optimal signal timing for one intersection.

        Parameters
        ----------
        intersection_id : str
            Unique identifier for the intersection (used as a label in output).
        lane_a_density : float
            Smoothed density percentage for Lane A (0.0 – 100.0).
        lane_b_density : float
            Smoothed density percentage for Lane B (0.0 – 100.0).

        Returns
        -------
        SignalTiming
        """
        total = lane_a_density + lane_b_density

        if total == 0.0:
            a_green = DEFAULT_GREEN
        else:
            a_green = max(
                self.min_green,
                min(self.max_green, (lane_a_density / total) * self.base_cycle),
            )

        b_green = self.base_cycle - a_green

        # Clamp b_green symmetrically (in case of floating-point edge cases)
        b_green = max(self.min_green, min(self.max_green, b_green))

        reason = get_optimization_reason(lane_a_density, lane_b_density)

        return SignalTiming(
            intersection_id=intersection_id,
            lane_a_green_seconds=round(a_green, 2),
            lane_b_green_seconds=round(b_green, 2),
            lane_a_red_seconds=round(b_green, 2),   # Lane A is red while B is green
            lane_b_red_seconds=round(a_green, 2),   # Lane B is red while A is green
            cycle_time=round(a_green + b_green, 2),
            optimization_reason=reason,
            created_at=datetime.utcnow(),
            is_emergency_override=False,
        )

    def emergency_override(
        self,
        intersection_id: str,
        priority_lane: str = "a",
    ) -> SignalTiming:
        """Force maximum green to one lane for emergency-vehicle passage.

        Parameters
        ----------
        intersection_id : str
        priority_lane : str – "a" or "b" (case-insensitive)
        """
        lane = priority_lane.lower()
        if lane == "a":
            a_green, b_green = self.max_green, self.min_green
            reason = "Emergency override: Lane A has maximum green for vehicle passage."
        else:
            a_green, b_green = self.min_green, self.max_green
            reason = "Emergency override: Lane B has maximum green for vehicle passage."

        return SignalTiming(
            intersection_id=intersection_id,
            lane_a_green_seconds=a_green,
            lane_b_green_seconds=b_green,
            lane_a_red_seconds=b_green,
            lane_b_red_seconds=a_green,
            cycle_time=a_green + b_green,
            optimization_reason=reason,
            created_at=datetime.utcnow(),
            is_emergency_override=True,
        )

    def compute_with_wait_time(
        self,
        intersection_id: str,
        lane_a_density: float,
        lane_b_density: float,
        avg_wait_time_a: float = 0.0,
        avg_wait_time_b: float = 0.0,
    ) -> SignalTiming:
        """Compute adaptive signal timing considering both density and vehicle wait times.

        If average wait time > 2x cycle time for a lane, extend green time by 10s
        to help clear the queue.

        Parameters
        ----------
        intersection_id : str
            Unique identifier for the intersection.
        lane_a_density : float
            Density percentage for Lane A (0.0 – 100.0).
        lane_b_density : float
            Density percentage for Lane B (0.0 – 100.0).
        avg_wait_time_a : float
            Average wait time for vehicles in Lane A (seconds).
        avg_wait_time_b : float
            Average wait time for vehicles in Lane B (seconds).

        Returns
        -------
        SignalTiming
        """
        # Start with base density computation
        total = lane_a_density + lane_b_density

        if total == 0.0:
            a_green = DEFAULT_GREEN
        else:
            a_green = max(
                self.min_green,
                min(self.max_green, (lane_a_density / total) * self.base_cycle),
            )

        b_green = self.base_cycle - a_green
        b_green = max(self.min_green, min(self.max_green, b_green))

        # ── Apply wait-time adjustments ────────────────────────────────────────
        wait_time_adjustment_a = ""
        wait_time_adjustment_b = ""
        extension = 10.0  # Additional green time seconds

        # Check Lane A wait time
        if avg_wait_time_a > 2 * self.base_cycle:
            # Vehicles waiting too long; extend their green time
            a_green = min(self.max_green, a_green + extension)
            b_green = self.base_cycle - a_green
            b_green = max(self.min_green, b_green)
            wait_time_adjustment_a = f" Lane A wait={avg_wait_time_a:.1f}s > 2x cycle; extended by {extension:.0f}s."

        # Check Lane B wait time
        if avg_wait_time_b > 2 * self.base_cycle:
            # Vehicles waiting too long; extend their green time
            b_green = min(self.max_green, b_green + extension)
            a_green = self.base_cycle - b_green
            a_green = max(self.min_green, a_green)
            wait_time_adjustment_b = f" Lane B wait={avg_wait_time_b:.1f}s > 2x cycle; extended by {extension:.0f}s."

        reason = get_optimization_reason(lane_a_density, lane_b_density)
        if wait_time_adjustment_a or wait_time_adjustment_b:
            reason += wait_time_adjustment_a + wait_time_adjustment_b

        return SignalTiming(
            intersection_id=intersection_id,
            lane_a_green_seconds=round(a_green, 2),
            lane_b_green_seconds=round(b_green, 2),
            lane_a_red_seconds=round(b_green, 2),
            lane_b_red_seconds=round(a_green, 2),
            cycle_time=round(a_green + b_green, 2),
            optimization_reason=reason,
            created_at=datetime.utcnow(),
            is_emergency_override=False,
        )
