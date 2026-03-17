"""
backend/tests/test_density.py
───────────────────────────────
Unit tests for DensityCalculator.

All tests use a fresh calculator instance (window_size=1) so the rolling
average equals the single raw reading — making assertions deterministic.
"""

from __future__ import annotations

import pytest
from app.services.density import DensityCalculator, _classify, _raw_density


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def calc():
    """Fresh calculator with window=1 so no smoothing distorts results."""
    return DensityCalculator(max_capacity=20, window_size=1)


# ── _raw_density helper ────────────────────────────────────────────────────────

class TestRawDensity:
    def test_zero_count_gives_zero(self):
        assert _raw_density(0, 20) == 0.0

    def test_full_capacity_gives_100(self):
        assert _raw_density(20, 20) == 100.0

    def test_over_capacity_clamped_to_100(self):
        assert _raw_density(25, 20) == 100.0

    def test_half_capacity(self):
        assert _raw_density(10, 20) == 50.0

    def test_zero_capacity_guard(self):
        assert _raw_density(5, 0) == 0.0


# ── _classify helper ───────────────────────────────────────────────────────────

class TestClassify:
    @pytest.mark.parametrize("score,expected_level", [
        (0.0,  "low"),
        (30.0, "low"),
        (30.1, "medium"),
        (60.0, "medium"),
        (60.1, "high"),
        (80.0, "high"),
        (80.1, "critical"),
        (100.0, "critical"),
    ])
    def test_thresholds(self, score, expected_level):
        level, _ = _classify(score)
        assert level == expected_level

    @pytest.mark.parametrize("score,expected_color_fragment", [
        (0.0,   "#22c55e"),   # green
        (45.0,  "#eab308"),   # yellow
        (70.0,  "#f97316"),   # orange
        (90.0,  "#ef4444"),   # red
    ])
    def test_colours(self, score, expected_color_fragment):
        _, color = _classify(score)
        assert color == expected_color_fragment


# ── DensityCalculator.update() ────────────────────────────────────────────────

class TestDensityCalculatorUpdate:
    """Each test uses max_capacity=20, window_size=1."""

    # ── Required spec cases ────────────────────────────────────────────────────

    def test_count_0_gives_low(self, calc):
        report = calc.update(0, 0)
        assert report.lane_a_density == pytest.approx(0.0)
        assert report.lane_a_level == "low"

    def test_count_6_gives_30_low(self, calc):
        report = calc.update(6, 6)
        assert report.lane_a_density == pytest.approx(30.0)
        assert report.lane_a_level == "low"

    def test_count_7_gives_35_medium(self, calc):
        report = calc.update(7, 7)
        assert report.lane_a_density == pytest.approx(35.0)
        assert report.lane_a_level == "medium"

    def test_count_12_gives_60_medium(self, calc):
        report = calc.update(12, 12)
        assert report.lane_a_density == pytest.approx(60.0)
        assert report.lane_a_level == "medium"

    def test_count_13_gives_65_high(self, calc):
        report = calc.update(13, 13)
        assert report.lane_a_density == pytest.approx(65.0)
        assert report.lane_a_level == "high"

    def test_count_20_gives_100_critical(self, calc):
        report = calc.update(20, 20)
        assert report.lane_a_density == pytest.approx(100.0)
        assert report.lane_a_level == "critical"

    # ── Lane B symmetry ────────────────────────────────────────────────────────

    def test_lane_b_independent(self, calc):
        report = calc.update(0, 13)
        assert report.lane_a_density == pytest.approx(0.0)
        assert report.lane_b_density == pytest.approx(65.0)
        assert report.lane_a_level == "low"
        assert report.lane_b_level == "high"

    # ── DensityReport fields ───────────────────────────────────────────────────

    def test_report_counts_preserved(self, calc):
        report = calc.update(8, 3)
        assert report.lane_a_count == 8
        assert report.lane_b_count == 3

    def test_congestion_ratio_lane_a_dominant(self, calc):
        report = calc.update(20, 0)
        # lane_a / (lane_a + lane_b + 0.01) ≈ 1.0
        assert report.congestion_ratio > 0.99

    def test_congestion_ratio_balanced(self, calc):
        report = calc.update(10, 10)
        assert report.congestion_ratio == pytest.approx(0.5, abs=0.01)

    def test_timestamp_present(self, calc):
        from datetime import datetime
        report = calc.update(5, 5)
        assert isinstance(report.timestamp, datetime)

    # ── Rolling average (window > 1) ───────────────────────────────────────────

    def test_rolling_average_smooths(self):
        """With window=3, three readings of 0/60/0 should average to ~20."""
        calc3 = DensityCalculator(max_capacity=20, window_size=3)
        calc3.update(0, 0)    # 0%
        calc3.update(12, 0)   # 60%
        r = calc3.update(0, 0)   # 0%
        # (0 + 60 + 0) / 3 = 20
        assert r.lane_a_density == pytest.approx(20.0, abs=0.1)

    def test_reset_clears_window(self, calc):
        calc.update(20, 20)
        calc.reset()
        assert calc.window_a == []
        assert calc.window_b == []

    def test_window_maxlen_respected(self):
        calc2 = DensityCalculator(max_capacity=20, window_size=2)
        for _ in range(10):
            calc2.update(5, 5)
        assert len(calc2.window_a) == 2
