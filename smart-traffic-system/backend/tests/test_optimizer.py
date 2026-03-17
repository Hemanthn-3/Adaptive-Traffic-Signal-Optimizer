"""
backend/tests/test_optimizer.py
─────────────────────────────────
Unit tests for SignalOptimizer and get_optimization_reason().
"""

from __future__ import annotations

import pytest
from app.services.optimizer import (
    SignalOptimizer,
    get_optimization_reason,
    MIN_GREEN,
    MAX_GREEN,
    DEFAULT_GREEN,
    BASE_CYCLE_SECONDS,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def opt():
    return SignalOptimizer()


# ── Equal density → equal split ────────────────────────────────────────────────

class TestEqualDensity:
    def test_both_zero_gives_30_30(self, opt):
        t = opt.compute("INT-01", 0.0, 0.0)
        assert t.lane_a_green_seconds == pytest.approx(DEFAULT_GREEN)
        assert t.lane_b_green_seconds == pytest.approx(DEFAULT_GREEN)

    def test_equal_nonzero_gives_30_30(self, opt):
        t = opt.compute("INT-01", 50.0, 50.0)
        assert t.lane_a_green_seconds == pytest.approx(DEFAULT_GREEN)
        assert t.lane_b_green_seconds == pytest.approx(DEFAULT_GREEN)

    def test_cycle_time_is_60(self, opt):
        t = opt.compute("INT-01", 0.0, 0.0)
        assert t.cycle_time == pytest.approx(BASE_CYCLE_SECONDS, abs=0.1)


# ── Spec: Lane A=80, Lane B=20 ────────────────────────────────────────────────

class TestLaneADominant:
    def test_lane_a_gets_more_green(self, opt):
        """A(80) + B(20) → A proportion = 80/100 = 0.8 → 48s, clamped to 48s."""
        t = opt.compute("INT-01", 80.0, 20.0)
        assert t.lane_a_green_seconds == pytest.approx(48.0, abs=0.5)
        assert t.lane_b_green_seconds == pytest.approx(12.0, abs=0.5)

    def test_a_green_gt_b_green(self, opt):
        t = opt.compute("INT-01", 80.0, 20.0)
        assert t.lane_a_green_seconds > t.lane_b_green_seconds

    def test_red_times_are_swapped(self, opt):
        t = opt.compute("INT-01", 80.0, 20.0)
        assert t.lane_a_red_seconds == pytest.approx(t.lane_b_green_seconds, abs=0.1)
        assert t.lane_b_red_seconds == pytest.approx(t.lane_a_green_seconds, abs=0.1)


# ── Spec: Lane A=0, Lane B=100  (hard clamp test) ────────────────────────────

class TestMinClamp:
    def test_lane_a_zero_lane_b_full(self, opt):
        """A gets minimum 10s, B gets maximum 50s."""
        t = opt.compute("INT-01", 0.0, 100.0)
        assert t.lane_a_green_seconds == pytest.approx(MIN_GREEN, abs=0.1)
        assert t.lane_b_green_seconds == pytest.approx(MAX_GREEN, abs=0.1)

    def test_reverse_full_a_zero_b(self, opt):
        t = opt.compute("INT-01", 100.0, 0.0)
        assert t.lane_a_green_seconds == pytest.approx(MAX_GREEN, abs=0.1)
        assert t.lane_b_green_seconds == pytest.approx(MIN_GREEN, abs=0.1)

    def test_green_never_below_min(self, opt):
        for a, b in [(0, 100), (5, 95), (10, 90)]:
            t = opt.compute("INT-01", float(a), float(b))
            assert t.lane_a_green_seconds >= MIN_GREEN
            assert t.lane_b_green_seconds >= MIN_GREEN

    def test_green_never_above_max(self, opt):
        for a, b in [(100, 0), (95, 5), (90, 10)]:
            t = opt.compute("INT-01", float(a), float(b))
            assert t.lane_a_green_seconds <= MAX_GREEN
            assert t.lane_b_green_seconds <= MAX_GREEN


# ── Emergency override ────────────────────────────────────────────────────────

class TestEmergencyOverride:
    def test_override_lane_a_gets_max_green(self, opt):
        t = opt.emergency_override("INT-01", priority_lane="a")
        assert t.lane_a_green_seconds == pytest.approx(MAX_GREEN)
        assert t.lane_b_green_seconds == pytest.approx(MIN_GREEN)

    def test_override_lane_b_gets_max_green(self, opt):
        t = opt.emergency_override("INT-01", priority_lane="b")
        assert t.lane_b_green_seconds == pytest.approx(MAX_GREEN)
        assert t.lane_a_green_seconds == pytest.approx(MIN_GREEN)

    def test_override_sets_flag(self, opt):
        t = opt.emergency_override("INT-01", priority_lane="a")
        assert t.is_emergency_override is True

    def test_normal_compute_flag_false(self, opt):
        t = opt.compute("INT-01", 50.0, 50.0)
        assert t.is_emergency_override is False

    def test_override_reason_contains_emergency(self, opt):
        t = opt.emergency_override("INT-01", priority_lane="a")
        assert "emergency" in t.optimization_reason.lower()

    def test_override_case_insensitive(self, opt):
        t_upper = opt.emergency_override("INT-01", priority_lane="A")
        t_lower = opt.emergency_override("INT-01", priority_lane="a")
        assert t_upper.lane_a_green_seconds == t_lower.lane_a_green_seconds


# ── get_optimization_reason ───────────────────────────────────────────────────

class TestOptimizationReason:
    def test_no_traffic(self):
        reason = get_optimization_reason(0.0, 0.0)
        assert "no traffic" in reason.lower()

    def test_equal_density(self):
        reason = get_optimization_reason(50.0, 50.0)
        assert "equal" in reason.lower()

    def test_lane_a_dominant_reason(self):
        reason = get_optimization_reason(72.0, 34.0)
        assert "lane a" in reason.lower()
        assert "72.0%" in reason
        assert "34.0%" in reason

    def test_lane_b_dominant_reason(self):
        reason = get_optimization_reason(20.0, 80.0)
        assert "lane b" in reason.lower()

    def test_reason_mentions_extension(self):
        reason = get_optimization_reason(80.0, 20.0)
        assert "extending" in reason.lower() or "green" in reason.lower()


# ── SignalTiming dataclass completeness ───────────────────────────────────────

class TestSignalTimingFields:
    def test_all_required_fields_present(self, opt):
        t = opt.compute("INT-TEST", 40.0, 60.0)
        assert t.intersection_id == "INT-TEST"
        assert t.lane_a_green_seconds is not None
        assert t.lane_b_green_seconds is not None
        assert t.lane_a_red_seconds is not None
        assert t.lane_b_red_seconds is not None
        assert t.cycle_time is not None
        assert t.optimization_reason is not None
        assert t.created_at is not None

    def test_custom_bounds_respected(self):
        custom = SignalOptimizer(base_cycle=120.0, min_green=20.0, max_green=100.0)
        t = custom.compute("INT-X", 0.0, 100.0)
        assert t.lane_a_green_seconds == pytest.approx(20.0)
        assert t.lane_b_green_seconds == pytest.approx(100.0)
