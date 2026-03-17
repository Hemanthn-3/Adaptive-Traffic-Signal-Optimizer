from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers import traffic


class FakeCapture:
    def __init__(self, _path: str):
        self.frame_index = 0

    def get(self, prop: int) -> float:
        if prop == 5:
            return 30.0
        return 0.0

    def read(self):
        self.frame_index += 1
        return True, f"frame-{self.frame_index}".encode()

    def set(self, prop: int, value: int):
        if prop == 1 and value == 0:
            self.frame_index = 0

    def release(self):
        return None


class FakeDetector:
    def process_frame(self, frame, frame_number: int = -1, fps: float = 30.0):
        return {
            "lane_a": {"total": frame_number},
            "lane_b": {"total": frame_number + 2},
        }


class FakeDensityCalculator:
    def update(self, lane_a_count: int, lane_b_count: int):
        return SimpleNamespace(
            lane_a_density=lane_a_count * 2.0,
            lane_b_density=lane_b_count * 2.0,
        )

    def reset(self):
        return None


@pytest.mark.asyncio
async def test_stream_video_broadcasts_density_every_30_frames(monkeypatch):
    fake_cv2 = SimpleNamespace(
        CAP_PROP_FPS=5,
        CAP_PROP_POS_FRAMES=1,
        IMWRITE_JPEG_QUALITY=1,
        VideoCapture=FakeCapture,
        imencode=lambda ext, frame, params: (True, SimpleNamespace(tobytes=lambda: b"jpeg-bytes")),
    )
    fake_detector_module = SimpleNamespace(VehicleDetector=FakeDetector)
    fake_density_module = SimpleNamespace(DensityCalculator=FakeDensityCalculator)

    broadcast = AsyncMock()
    active_transitions: list[bool] = []

    async def fake_set_video_stream_active(active: bool):
        active_transitions.append(active)

    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setitem(sys.modules, "app.services.detector", fake_detector_module)
    monkeypatch.setitem(sys.modules, "app.services.density", fake_density_module)
    monkeypatch.setattr(traffic, "find_video", lambda: "fake.avi")
    monkeypatch.setattr(traffic, "ws_manager", SimpleNamespace(broadcast=broadcast))
    monkeypatch.setattr(traffic, "_set_video_stream_active", fake_set_video_stream_active)

    response = await traffic.stream_video()

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
        if len(chunks) == 31:
            await response.body_iterator.aclose()
            break

    assert len(chunks) == 31
    assert active_transitions == [True, False]
    broadcast.assert_awaited_once()

    payload = broadcast.await_args.args[0]
    assert payload["type"] == "density_update"
    assert payload["intersection_id"] == traffic.STREAM_INTERSECTION_ID
    assert payload["data"]["lane_a_count"] == 30
    assert payload["data"]["lane_b_count"] == 32
    assert payload["data"]["lane_a_density"] == 60.0
    assert payload["data"]["lane_b_density"] == 64.0
    assert payload["data"]["source"] == "video_stream"
