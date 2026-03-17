"""
backend/app/services/pipeline.py
───────────────────────────────────
TrafficPipeline orchestrates the full real-time processing loop:

  Video frame
     │
     ▼
  VehicleDetector  (YOLOv8)
     │  detections
     ▼
  DensityCalculator  (rolling average)
     │  DensityReport
     ▼
  SignalOptimizer  (proportional green-time)
     │  SignalTiming
     ▼
  ┌─────────────┬──────────────┐
  │  MQTT pub   │  WS broadcast│
  └─────────────┴──────────────┘
     │  every 5 frames
     ▼
  Redis  (latest density cache)
     │  every 10 frames
     ▼
  DB log (async, non-blocking)

MultiCameraPipeline aggregates results from multiple cameras (up to 4) per intersection:

  Camera 1      Camera 2      Camera 3      Camera 4
    │             │             │             │
    └─────────────┴─────────────┴─────────────┘
                      │
                      ▼
                 Aggregator
                      │
          ┌───────────┼───────────┐
          │           │           │
     Total Count  Avg Density  Busiest Cam
          │           │           │
          └───────────┴───────────┘
                      │
                      ▼
              Signal Optimization
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from app.core.mqtt_client import MQTTClient
from app.core.redis_client import get_redis
from app.core.websocket_manager import ConnectionManager
from app.services.density import DensityCalculator
from app.services.detector import VehicleDetector
from app.services.optimizer import SignalOptimizer

logger = logging.getLogger(__name__)


class TrafficPipeline:
    """Full-stack pipeline: video → detection → density → signal → broadcast.

    Parameters
    ----------
    intersection_id : str
        ID of the intersection being monitored (e.g. "INT-01").
    video_path : str
        Absolute or relative path to the input video file.
    frame_interval : int
        Process every Nth frame (default 1 = every frame).
    db_write_every : int
        Persist a density snapshot to Redis every N processed frames.
    signal_log_every : int
        Log signal timing every N processed frames.
    """

    def __init__(
        self,
        intersection_id: str,
        video_path: str,
        frame_interval: int = 1,
        db_write_every: int = 5,
        signal_log_every: int = 10,
    ) -> None:
        self.intersection_id = intersection_id
        self.video_path = video_path
        self.frame_interval = frame_interval
        self.db_write_every = db_write_every
        self.signal_log_every = signal_log_every

        # ── Service instances ──────────────────────────────────────────────────
        self.detector = VehicleDetector()
        self.density_service = DensityCalculator()
        self.optimizer = SignalOptimizer()
        self.mqtt = MQTTClient.get_instance()
        self.ws_manager = ConnectionManager.get_instance()

        # ── Runtime state ──────────────────────────────────────────────────────
        self._frames_processed: int = 0
        self._last_density = None
        self._last_timing = None
        self._running: bool = False

    # ── Public API ─────────────────────────────────────────────────────────────

    async def run(self) -> dict:
        """Process the full video and return a summary dict when done.

        Yields control to the event loop between frames so the FastAPI server
        stays responsive during long videos.
        """
        self._running = True
        logger.info(
            "Pipeline START  intersection=%s  video=%s",
            self.intersection_id, self.video_path,
        )

        async for frame_result in self._iter_frames():
            if not self._running:
                break
            await self.process_frame(frame_result)
            self._frames_processed += 1

            # Yield so the event-loop can handle incoming requests
            await asyncio.sleep(0)

        logger.info("Pipeline END  frames=%d", self._frames_processed)
        return self._build_summary()

    def stop(self) -> None:
        """Signal the pipeline to stop after the current frame."""
        self._running = False

    # ── Frame processing ───────────────────────────────────────────────────────

    async def process_frame(self, frame_data: dict) -> None:
        """Run the full processing chain for one frame.

        Parameters
        ----------
        frame_data : dict
            Output of ``VehicleDetector.process_frame()`` enriched with
            ``frame_number`` and ``timestamp_ms``.
        """
        fn = frame_data["frame_number"]
        a_count = frame_data["lane_a"]["vehicle_count"]
        b_count = frame_data["lane_b"]["vehicle_count"]

        # ── 1. Density ─────────────────────────────────────────────────────────
        density = self.density_service.update(a_count, b_count)
        self._last_density = density

        # ── 2. Signal timing ───────────────────────────────────────────────────
        timing = self.optimizer.compute(
            self.intersection_id,
            density.lane_a_density,
            density.lane_b_density,
        )
        self._last_timing = timing

        # ── 3. MQTT publish ────────────────────────────────────────────────────
        self.mqtt.publish(
            f"traffic/signals/{self.intersection_id}/command",
            json.dumps({
                "command": "SET_TIMING",
                "lane_a_green": timing.lane_a_green_seconds,
                "lane_b_green": timing.lane_b_green_seconds,
                "cycle": timing.cycle_time,
                "reason": timing.optimization_reason,
            }),
        )

        # ── 4. WebSocket broadcast ─────────────────────────────────────────────
        density_payload = {
            "intersection_id": self.intersection_id,
            "frame_number":    fn,
            "lane_a_count":    a_count,
            "lane_b_count":    b_count,
            "lane_a_density":  density.lane_a_density,
            "lane_b_density":  density.lane_b_density,
            "lane_a_level":    density.lane_a_level,
            "lane_b_level":    density.lane_b_level,
            "timestamp":       density.timestamp.isoformat(),
        }
        timing_payload = {
            "intersection_id":       timing.intersection_id,
            "lane_a_green_seconds":  timing.lane_a_green_seconds,
            "lane_b_green_seconds":  timing.lane_b_green_seconds,
            "lane_a_red_seconds":    timing.lane_a_red_seconds,
            "lane_b_red_seconds":    timing.lane_b_red_seconds,
            "cycle_time":            timing.cycle_time,
            "optimization_reason":   timing.optimization_reason,
            "is_emergency_override": timing.is_emergency_override,
            "created_at":            timing.created_at.isoformat(),
        }

        await self.ws_manager.broadcast({"type": "density_update", "data": density_payload})
        await self.ws_manager.broadcast({"type": "signal_update",  "data": timing_payload})

        # ── 5. Redis cache (every db_write_every frames) ───────────────────────
        if fn % self.db_write_every == 0:
            await self._cache_to_redis(density_payload)

        # ── 6. Signal timing log (every signal_log_every frames) ───────────────
        if fn % self.signal_log_every == 0:
            logger.info(
                "[Frame %04d] A=%.1f%% (%s) B=%.1f%% (%s) | "
                "Green A=%.1fs B=%.1fs",
                fn,
                density.lane_a_density, density.lane_a_level,
                density.lane_b_density, density.lane_b_level,
                timing.lane_a_green_seconds,
                timing.lane_b_green_seconds,
            )

    # ── Async frame iterator ───────────────────────────────────────────────────

    async def _iter_frames(self):
        """Wrap the synchronous generator in async-friendly iteration."""
        loop = asyncio.get_event_loop()

        def _gen():
            return self.detector.process_video(self.video_path)

        gen = await loop.run_in_executor(None, _gen)

        frame_idx = 0
        for frame_result in gen:
            frame_idx += 1
            if frame_idx % self.frame_interval != 0:
                continue
            yield frame_result

    # ── Redis helper ───────────────────────────────────────────────────────────

    async def _cache_to_redis(self, density_payload: dict) -> None:
        try:
            redis = await get_redis()
            key = f"density:lane:{self.intersection_id}:latest"
            await redis.set(key, json.dumps(density_payload), ex=300)
            await redis.lpush(f"density:history:{self.intersection_id}", json.dumps(density_payload))
            await redis.ltrim(f"density:history:{self.intersection_id}", 0, 999)
        except Exception as exc:
            logger.warning("Redis write failed: %s", exc)

    # ── Summary ────────────────────────────────────────────────────────────────

    def _build_summary(self) -> dict:
        return {
            "intersection_id":   self.intersection_id,
            "frames_processed":  self._frames_processed,
            "last_density":      asdict(self._last_density) if self._last_density else None,
            "last_timing": {
                "lane_a_green_seconds": self._last_timing.lane_a_green_seconds,
                "lane_b_green_seconds": self._last_timing.lane_b_green_seconds,
                "optimization_reason":  self._last_timing.optimization_reason,
            } if self._last_timing else None,
        }


# ── Multi-Camera Orchestrator ──────────────────────────────────────────────────

class MultiCameraPipeline:
    """Orchestrates processing of 1-4 camera feeds for a single intersection.

    Parameters
    ----------
    intersection_id : str
        ID of the intersection (e.g. "INT-01")
    camera_videos : Dict[str, str]
        Mapping of camera_id -> video_path
        Example: {"cam_1": "path/to/video1.mp4", "cam_2": "path/to/video2.mp4"}
    """

    CAMERA_DIRECTIONS = {
        "cam_1": "North",
        "cam_2": "South",
        "cam_3": "East",
        "cam_4": "West",
    }

    def __init__(self, intersection_id: str, camera_videos: Dict[str, str]) -> None:
        self.intersection_id = intersection_id
        self.camera_videos = camera_videos

        # One pipeline per camera
        self.pipelines: Dict[str, TrafficPipeline] = {}
        for cam_id, video_path in camera_videos.items():
            self.pipelines[cam_id] = TrafficPipeline(
                intersection_id=f"{intersection_id}:{cam_id}",
                video_path=video_path,
                frame_interval=1,
                db_write_every=5,
                signal_log_every=10,
            )

        self.ws_manager = ConnectionManager.get_instance()
        self.optimizer = SignalOptimizer()

    async def run(self) -> dict:
        """Process all camera videos in parallel and aggregate results."""
        logger.info("MultiCamera pipeline start: %s (cameras=%s)",
                   self.intersection_id, list(self.camera_videos.keys()))

        # Run all pipelines concurrently
        results = await asyncio.gather(
            *[self.pipelines[cam_id].run() for cam_id in self.camera_videos.keys()],
            return_exceptions=True,
        )

        # Aggregate results
        aggregated = await self._aggregate_results(results)
        logger.info("MultiCamera pipeline end: %s", self.intersection_id)
        return aggregated

    async def _aggregate_results(self, results: List) -> dict:
        """Aggregate results from all cameras."""
        total_vehicles = 0
        total_density = 0.0
        active_cameras = 0
        busiest_camera = None
        max_density = -1.0

        camera_summaries = {}

        for cam_id, result in zip(self.camera_videos.keys(), results):
            if isinstance(result, Exception):
                logger.error("Camera %s failed: %s", cam_id, result)
                camera_summaries[cam_id] = {"status": "error", "error": str(result)}
                continue

            last_density = result.get("last_density")
            if last_density:
                avg_density = (last_density.get("lane_a_density", 0) +
                              last_density.get("lane_b_density", 0)) / 2.0
                total_density += avg_density
                active_cameras += 1

                total_vehicles += (last_density.get("lane_a_count", 0) +
                                 last_density.get("lane_b_count", 0))

                if avg_density > max_density:
                    max_density = avg_density
                    busiest_camera = cam_id

                camera_summaries[cam_id] = {
                    "status": "completed",
                    "frames_processed": result.get("frames_processed", 0),
                    "density": avg_density,
                    "lane_a_count": last_density.get("lane_a_count", 0),
                    "lane_b_count": last_density.get("lane_b_count", 0),
                }
            else:
                camera_summaries[cam_id] = {"status": "no_data"}

        # Calculate aggregate density and signal timing
        avg_density = (total_density / active_cameras) if active_cameras > 0 else 0.0

        timing = self.optimizer.compute(
            self.intersection_id,
            avg_density,
            avg_density,  # Use same for both lanes as we're aggregating
        )

        # Broadcast aggregated update
        agg_payload = {
            "intersection_id": self.intersection_id,
            "timestamp": datetime.utcnow().isoformat(),
            "active_cameras": active_cameras,
            "total_vehicles": total_vehicles,
            "aggregate_density": avg_density,
            "busiest_camera": busiest_camera,
            "suggested_green_time": timing.lane_a_green_seconds,
            "camera_summaries": camera_summaries,
        }

        await self.ws_manager.broadcast({
            "type": "intersection_aggregate",
            "data": agg_payload,
        })

        return {
            "intersection_id": self.intersection_id,
            "total_vehicles": total_vehicles,
            "aggregate_density": avg_density,
            "active_cameras": active_cameras,
            "busiest_camera": busiest_camera,
            "camera_summaries": camera_summaries,
            "suggested_timing": {
                "lane_a_green_seconds": timing.lane_a_green_seconds,
                "lane_b_green_seconds": timing.lane_b_green_seconds,
                "cycle_time": timing.cycle_time,
            },
        }

