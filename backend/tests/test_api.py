"""
backend/tests/test_api.py
──────────────────────────
Integration tests for the FastAPI application using TestClient.

External dependencies (Redis, MQTT, YOLOv8) are patched so the tests
run without any running infrastructure.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

# ── Path bootstrap ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── App-level patches applied before importing the app ────────────────────────
# We patch Redis, MQTT connect, and the lifespan so no real connections needed.

@pytest.fixture(scope="module")
def client():
    """Create a TestClient with all infrastructure mocked."""

    # Patch Redis
    redis_mock = AsyncMock()
    redis_mock.ping       = AsyncMock(return_value=True)
    redis_mock.get        = AsyncMock(return_value=None)
    redis_mock.set        = AsyncMock(return_value=True)
    redis_mock.keys       = AsyncMock(return_value=[])
    redis_mock.lpush      = AsyncMock(return_value=1)
    redis_mock.ltrim      = AsyncMock(return_value=True)
    redis_mock.delete     = AsyncMock(return_value=1)
    redis_mock.incr       = AsyncMock(return_value=42)
    redis_mock.exists     = AsyncMock(return_value=0)

    # Patch MQTT connect (no broker)
    mqtt_mock = MagicMock()
    mqtt_mock.publish  = MagicMock()
    mqtt_mock.connect  = MagicMock()
    mqtt_mock.disconnect = MagicMock()

    with (
        patch("app.core.redis_client.init_redis",  AsyncMock()),
        patch("app.core.redis_client.close_redis", AsyncMock()),
        patch("app.core.redis_client.get_redis",   AsyncMock(return_value=redis_mock)),
        patch("app.core.mqtt_client.MQTTClient",   return_value=mqtt_mock),
        patch("app.core.mqtt_client.MQTTClient.get_instance", return_value=mqtt_mock),
    ):
        from app.main import app
        app.state.redis      = redis_mock
        app.state.mqtt       = mqtt_mock
        app.state.ws_manager = MagicMock(
            broadcast=AsyncMock(),
            send_personal=AsyncMock(),
            connection_count=0,
        )
        from app.services.density import DensityCalculator
        from app.services.optimizer import SignalOptimizer
        from app.services.corridor import GreenCorridorService

        app.state.density_calc = DensityCalculator()
        app.state.optimizer    = SignalOptimizer()
        app.state.corridor     = GreenCorridorService(
            signal_optimizer=app.state.optimizer,
            mqtt_client=mqtt_mock,
            redis_client=None,
        )

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ── GET /health ────────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_status_ok(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"

    def test_service_name(self, client):
        body = client.get("/health").json()
        assert "smart-traffic" in body["service"].lower()

    def test_ws_clients_field(self, client):
        body = client.get("/health").json()
        assert "ws_clients" in body


# ── GET /api/traffic/intersections ────────────────────────────────────────────

class TestIntersections:
    def test_returns_200(self, client):
        r = client.get("/api/traffic/intersections")
        assert r.status_code == 200

    def test_returns_list(self, client):
        body = client.get("/api/traffic/intersections").json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_count_field_present(self, client):
        body = client.get("/api/traffic/intersections").json()
        assert "count" in body


# ── GET /api/traffic/density ──────────────────────────────────────────────────

class TestDensityEndpoint:
    def test_returns_200(self, client):
        r = client.get("/api/traffic/density")
        assert r.status_code == 200

    def test_has_data_key(self, client):
        body = client.get("/api/traffic/density").json()
        assert "data" in body


# ── GET /api/signals/all ──────────────────────────────────────────────────────

class TestSignalsAll:
    def test_returns_200(self, client):
        r = client.get("/api/signals/all")
        assert r.status_code == 200

    def test_returns_dict_with_data(self, client):
        body = client.get("/api/signals/all").json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_count_field(self, client):
        body = client.get("/api/signals/all").json()
        assert "count" in body


# ── GET /api/signals/{id} – missing ───────────────────────────────────────────

class TestSignalNotFound:
    def test_missing_intersection_returns_404(self, client):
        r = client.get("/api/signals/NONEXISTENT-99")
        assert r.status_code == 404


# ── POST /api/emergency/simulate ─────────────────────────────────────────────

class TestEmergencySimulate:
    def test_returns_200(self, client):
        r = client.post("/api/emergency/simulate", json={})
        assert r.status_code == 200

    def test_returns_event(self, client):
        body = client.post("/api/emergency/simulate", json={}).json()
        assert body["status"] == "simulated"
        assert "event" in body

    def test_event_has_vehicle_id(self, client):
        body = client.post("/api/emergency/simulate", json={}).json()
        assert "vehicle_id" in body["event"]

    def test_event_has_route(self, client):
        body = client.post("/api/emergency/simulate", json={}).json()
        assert len(body["event"]["route"]) > 0

    def test_custom_vehicle_id(self, client):
        body = client.post(
            "/api/emergency/simulate",
            json={"vehicle_id": "AMB-XYZ"}
        ).json()
        assert body["event"]["vehicle_id"] == "AMB-XYZ"


# ── GET /api/emergency/active ─────────────────────────────────────────────────

class TestEmergencyActive:
    def test_returns_200(self, client):
        r = client.get("/api/emergency/active")
        assert r.status_code == 200

    def test_returns_list(self, client):
        body = client.get("/api/emergency/active").json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_simulated_emergency_appears(self, client):
        """Simulate, then verify it appears in the active list."""
        client.post("/api/emergency/simulate", json={"vehicle_id": "AMB-VIS-001"})
        body = client.get("/api/emergency/active").json()
        vehicle_ids = [e.get("vehicle_id") for e in body["data"]]
        assert "AMB-VIS-001" in vehicle_ids


# ── POST /api/traffic/video/process ──────────────────────────────────────────

class TestVideoProcess:
    def _make_fake_mp4(self) -> bytes:
        """Return a minimal valid (but tiny) file just to test the upload path."""
        import cv2, tempfile, os
        # Create a 10-frame 64×64 black video
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            path = tmp.name
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 5, (64, 64))
        for _ in range(10):
            out.write(np.zeros((64, 64, 3), dtype=np.uint8))
        out.release()
        with open(path, "rb") as f:
            data = f.read()
        os.unlink(path)
        return data

    def test_video_process_returns_200(self, client):
        """Patch the detector so no GPU/model loading is needed."""
        fake_result = {
            "frame_number": 1,
            "timestamp_ms": 33.3,
            "lane_a": {"vehicle_count": 2, "vehicle_positions": []},
            "lane_b": {"vehicle_count": 1, "vehicle_positions": []},
            "total_vehicles": 3,
            "annotated_frame": np.zeros((64, 64, 3), dtype=np.uint8),
        }

        with patch(
            "app.routers.traffic.VehicleDetector"
        ) as MockDetector:
            instance = MagicMock()
            instance.process_video.return_value = iter([fake_result])
            MockDetector.return_value = instance

            mp4_bytes = self._make_fake_mp4()
            r = client.post(
                "/api/traffic/video/process",
                data={"intersection_id": "INT-01"},
                files={"file": ("test.mp4", io.BytesIO(mp4_bytes), "video/mp4")},
            )
        assert r.status_code == 200

    def test_video_process_returns_summary(self, client):
        fake_result = {
            "frame_number": 1,
            "timestamp_ms": 33.3,
            "lane_a": {"vehicle_count": 4, "vehicle_positions": []},
            "lane_b": {"vehicle_count": 2, "vehicle_positions": []},
            "total_vehicles": 6,
            "annotated_frame": np.zeros((64, 64, 3), dtype=np.uint8),
        }

        with patch("app.routers.traffic.VehicleDetector") as MockDetector:
            instance = MagicMock()
            instance.process_video.return_value = iter([fake_result])
            MockDetector.return_value = instance

            mp4_bytes = self._make_fake_mp4()
            r = client.post(
                "/api/traffic/video/process",
                data={"intersection_id": "INT-01"},
                files={"file": ("test.mp4", io.BytesIO(mp4_bytes), "video/mp4")},
            )

        body = r.json()
        assert "frames_processed" in body
        assert body["status"] == "completed"

    def test_unsupported_format_returns_400(self, client):
        r = client.post(
            "/api/traffic/video/process",
            data={"intersection_id": "INT-01"},
            files={"file": ("image.jpg", io.BytesIO(b"fake"), "image/jpeg")},
        )
        assert r.status_code == 400
