"""
backend/tests/conftest.py
──────────────────────────
Shared pytest fixtures for the test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Ensure the backend package is importable from any working directory ────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Stub MQTT client (no broker needed in tests) ──────────────────────────────
@pytest.fixture()
def stub_mqtt():
    m = MagicMock()
    m.publish = MagicMock()
    m.connect = MagicMock()
    m.disconnect = MagicMock()
    return m


# ── Stub async Redis client ────────────────────────────────────────────────────
@pytest.fixture()
def stub_redis():
    r = AsyncMock()
    r.set    = AsyncMock(return_value=True)
    r.get    = AsyncMock(return_value=None)
    r.delete = AsyncMock(return_value=1)
    r.keys   = AsyncMock(return_value=[])
    r.incr   = AsyncMock(return_value=1)
    return r
