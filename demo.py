#!/usr/bin/env python3
"""
demo.py — Smart Traffic System end-to-end demo with multi-camera support
──────────────────────────────────────────────────────────────────────────
Run from the project root to process one or four cameras:

Single camera:
    python demo.py path/to/video.mp4

Four cameras (one per approach):
    python demo.py cam1.mp4 cam2.mp4 cam3.mp4 cam4.mp4

What it does
────────────
1. Verifies Redis and PostgreSQL are reachable
2. Ensures a test intersection exists in Redis
3. Processes 1 or 4 video files (one per camera or single feed)
4. Prints a live 4-camera summary table every 30 frames
5. Prints summary statistics at the end
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

# ── Path bootstrap ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

# ── Imports (after path bootstrap) ────────────────────────────────────────────
try:
    import redis.asyncio as aioredis
    import asyncpg
    import httpx
    from dotenv import load_dotenv
except ImportError as e:
    print(f"\n[ERROR] Missing dependency: {e}")
    print("Run:  pip install -r backend/requirements.txt\n")
    sys.exit(1)

from app.services.detector import VehicleDetector, get_video_metadata
from app.services.density import DensityCalculator
from app.services.optimizer import SignalOptimizer
from app.services.corridor import GreenCorridorService, simulate_ambulance_route

load_dotenv(ROOT / ".env")

# ── Config from env ────────────────────────────────────────────────────────────
REDIS_URL    = os.getenv("REDIS_URL",    "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://traffic_user:traffic_pass@localhost:5432/traffic_db")
BACKEND_API  = os.getenv("BACKEND_API",  "http://localhost:8000")
INTERSECTION  = "INT-DEMO-01"
EMERGENCY_AT_FRAME = 100
SUMMARY_EVERY      = 30
DENSITY_POST_EVERY = 5

# Camera configuration
CAMERA_DIRECTIONS = {
    "cam_1": "North",
    "cam_2": "South",
    "cam_3": "East",
    "cam_4": "West",
}


# ─────────────────────────────────────────────────────────────────────────────
# Console helpers
# ─────────────────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
DIM    = "\033[2m"

def _density_level(pct: float) -> str:
    """Convert percentage to level name."""
    if pct <= 30:   return "LOW"
    if pct <= 60:   return "MED"
    if pct <= 80:   return "HIGH"
    return "V.HIGH"

def _color_density(pct: float) -> str:
    if pct <= 30:   return f"{GREEN}{pct:6.1f}%{RESET}"
    if pct <= 60:   return f"{YELLOW}{pct:6.1f}%{RESET}"
    if pct <= 80:   return f"\033[33m{pct:6.1f}%{RESET}"
    return f"{RED}{pct:6.1f}%{RESET}"

def _print_header_single():
    """Header for single-camera mode."""
    print(f"\n{BOLD}{CYAN}{'─'*95}{RESET}")
    print(
        f"{BOLD}"
        f"{'Frame':>6} │ {'Lane A':>6} │ {'Lane B':>6} │ "
        f"{'A Density':>9} │ {'B Density':>9} │ "
        f"{'A Green':>7} │ {'B Green':>7} │ {'Emergency':>10}"
        f"{RESET}"
    )
    print(f"{DIM}{'─'*95}{RESET}")

def _print_header_multi():
    """Header for multi-camera mode."""
    print(f"\n{BOLD}{CYAN}{'─'*100}{RESET}")
    print(
        f"{BOLD}"
        f"{'Camera':>8} │ {'Direction':>9} │ {'Vehicles':>9} │ {'Density':>9} │ "
        f"{'Time to Clear':>15}"
        f"{RESET}"
    )
    print(f"{DIM}{'─'*100}{RESET}")

def _print_row_single(frame, a_count, b_count, a_pct, b_pct, a_green, b_green, emergency,
                      is_override=False):
    """Print single-camera row."""
    a_g = f"{RED}OVERRIDE{RESET}" if is_override else f"{a_green:6.1f}s"
    b_g = f"{GREEN} GREEN{RESET}" if is_override else f"{b_green:6.1f}s"
    emg = f"{RED}YES 🚨{RESET}" if emergency else f"{DIM}No{RESET}"
    print(
        f"{frame:>6} │ {a_count:>6} │ {b_count:>6} │ "
        f"{_color_density(a_pct):>9} │ {_color_density(b_pct):>9} │ "
        f"{a_g:>7} │ {b_g:>7} │ {emg:>10}"
    )

def _print_row_multi(cam_id: str, direction: str, vehicle_count: int, density_pct: float,
                     time_to_clear: float):
    """Print multi-camera row."""
    density_color = _color_density(density_pct)
    level = _density_level(density_pct)
    print(
        f"{cam_id:>8} │ {direction:>9} │ {vehicle_count:>9} │ "
        f"{density_color:>9} │ {time_to_clear:>7.1f}s ({level:>6})"
    )

def _calculate_time_to_clear(vehicle_count: int, density_pct: float) -> float:
    """Estimate time to clear a lane based on vehicle count and density."""
    if vehicle_count == 0:
        return 0.0
    # Simple model: multiply by density factor (higher density = longer clear time)
    base_time = vehicle_count * 1.5  # ~1.5s per vehicle
    density_factor = 1.0 + (density_pct / 100.0)
    return base_time * density_factor

def _print_emergency_row(frame, vehicle_id, route):
    msg = f"EMERGENCY ACTIVATED — {vehicle_id} — Route: {' → '.join(route)}"
    print(f"{RED}{BOLD}{frame:>6} │ {msg:^86}{RESET}")
    print(f"{DIM}{'─'*95}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure checks
# ─────────────────────────────────────────────────────────────────────────────

async def check_redis() -> Optional[aioredis.Redis]:
    print(f"  {CYAN}→ Redis{RESET}        ", end="", flush=True)
    try:
        r = aioredis.from_url("redis://:redis_pass@localhost:6379/0", decode_responses=True, socket_timeout=3)
        await r.ping()
        print(f"{GREEN}OK{RESET}  (redis://localhost:6379/0)")
        return r
    except Exception as e:
        print(f"{YELLOW}SKIPPED{RESET}  ({e})")
        return None

async def check_postgres() -> bool:
    # Use plain postgresql:// (not asyncpg-prefixed) for direct asyncpg.connect()
    pg_url = "postgresql://traffic_user:traffic_pass@localhost:5432/traffic_db"
    print(f"  {CYAN}→ PostgreSQL{RESET}   ", end="", flush=True)
    try:
        conn = await asyncpg.connect(pg_url, timeout=3)
        await conn.close()
        print(f"{GREEN}OK{RESET}  ({pg_url.split('@')[-1]})")
        return True
    except Exception as e:
        print(f"{YELLOW}SKIPPED{RESET}  ({e})")
        return False

async def seed_intersection(redis: Optional[aioredis.Redis]):
    if redis is None:
        return
    key = "intersections:all"
    if not await redis.exists(key):
        import json
        await redis.set(key, json.dumps([{
            "id": INTERSECTION,
            "name": "Demo Junction — Main St & 1st Ave",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "lane_count": 2,
            "max_capacity_per_lane": 20,
        }]), ex=86400)
        print(f"  {GREEN}Seeded{RESET} test intersection {INTERSECTION} in Redis\n")


# ─────────────────────────────────────────────────────────────────────────────
# Stub MQTT client for demo (no broker needed)
# ─────────────────────────────────────────────────────────────────────────────

class _StubMQTT:
    def publish(self, topic: str, payload, *args, **kwargs):
        pass   # silent in demo
    def connect(self): pass
    def disconnect(self): pass

class _StubCorridorService(GreenCorridorService):
    def __init__(self):
        super().__init__(
            signal_optimizer=SignalOptimizer(),
            mqtt_client=_StubMQTT(),
            redis_client=None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   Smart Traffic Management System — Demo     ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════╝{RESET}\n")

    # ── 1. Infrastructure checks ───────────────────────────────────────────────
    print(f"{BOLD}Checking infrastructure …{RESET}")
    redis = await check_redis()
    await check_postgres()
    await seed_intersection(redis)

    # ── 2. Determine camera mode (single or multi) ────────────────────────────
    if len(sys.argv) > 1:
        video_paths = sys.argv[1:]
        if len(video_paths) == 1:
            # Single camera mode
            video_path = video_paths[0]
            await run_single_camera_mode(video_path, redis)
        elif len(video_paths) == 4:
            # Multi-camera mode
            await run_multi_camera_mode(video_paths, redis)
        else:
            print(f"{RED}[ERROR] Provide either 1 or 4 video files{RESET}")
            sys.exit(1)
    else:
        # Prompt for video
        video_path = input(f"\n{BOLD}Enter path to a test video file:{RESET} ").strip()
        if not Path(video_path).exists():
            print(f"\n{RED}[ERROR] File not found: {video_path}{RESET}")
            sys.exit(1)
        await run_single_camera_mode(video_path, redis)

    if redis:
        await redis.aclose()


async def run_single_camera_mode(video_path: str, redis: Optional[aioredis.Redis]):
    """Process a single camera video with original summary display."""
    if not Path(video_path).exists():
        print(f"\n{RED}[ERROR] File not found: {video_path}{RESET}")
        sys.exit(1)

    meta = get_video_metadata(video_path)
    # Resolve model path (best.pt preferred, yolov8n.pt fallback)
    import os
    from pathlib import Path as _Path
    _model_path = os.getenv("YOLO_MODEL_PATH", "ml/models/best.pt")
    if not _Path(_model_path).exists():
        print(f"{YELLOW}[WARN] best.pt not found at '{_model_path}', using yolov8n.pt fallback{RESET}")
        _model_path = "yolov8n.pt"
    else:
        print(f"{GREEN}[INFO] Using fine-tuned best.pt model{RESET}")

    print(f"\n{BOLD}Video info:{RESET}")
    print(f"  File   : {video_path}")
    print(f"  Size   : {meta['width']} × {meta['height']}")
    print(f"  FPS    : {meta['fps']:.1f}  |  Frames: {meta['total_frames']}")
    print(f"  Model  : {_model_path}\n")

    # ── 3. Initialise services ─────────────────────────────────────────────────
    detector      = VehicleDetector(_model_path)
    density_calc  = DensityCalculator(max_capacity=20)
    optimizer     = SignalOptimizer()
    corridor_svc  = _StubCorridorService()

    # ── 4. Accumulators for summary stats ─────────────────────────────────────
    sum_a_density = sum_b_density = 0.0
    min_a_green = min_b_green = float("inf")
    max_a_green = max_b_green = 0.0
    total_emergency_events = 0
    total_frames = 0
    emergency_active = False
    emergency_event = None

    # ── 4b. Prepare annotated video writer ────────────────────────────────────
    import cv2 as _cv2
    _out_video_path = "ml/test_videos/processed_sample_video.avi"
    _out = None
    _writer_init = False

    _print_header_single()

    t_start = time.perf_counter()

    for frame_result in detector.process_video(video_path):
        fn      = frame_result["frame"]
        a_count = frame_result["lane_a"]["total"]
        b_count = frame_result["lane_b"]["total"]
        total_frames = fn

        # ── Write annotated frame to output video ───────────────────────────
        _annotated = frame_result.get("annotated_frame")
        if _annotated is not None:
            if not _writer_init:
                _h, _w = _annotated.shape[:2]
                _fourcc = _cv2.VideoWriter_fourcc(*"mp4v")
                _out = _cv2.VideoWriter(
                    _out_video_path, _fourcc,
                    meta["fps"] or 25, (_w, _h)
                )
                _writer_init = True
            if _out and _out.isOpened():
                _out.write(_annotated)

        # Density + signal
        density = density_calc.update(a_count, b_count)
        timing  = optimizer.compute(INTERSECTION, density.lane_a_density, density.lane_b_density)

        # Accumulators
        sum_a_density += density.lane_a_density
        sum_b_density += density.lane_b_density
        min_a_green = min(min_a_green, timing.lane_a_green_seconds)
        min_b_green = min(min_b_green, timing.lane_b_green_seconds)
        max_a_green = max(max_a_green, timing.lane_a_green_seconds)
        max_b_green = max(max_b_green, timing.lane_b_green_seconds)

        # ── POST density data to backend every DENSITY_POST_EVERY frames ───────
        if fn % DENSITY_POST_EVERY == 0:
            density_payload = {
                "intersection_id": INTERSECTION,
                "frame_number": fn,
                "lane_a_count": a_count,
                "lane_b_count": b_count,
                "lane_a_density": density.lane_a_density,
                "lane_b_density": density.lane_b_density,
            }
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.post(
                        f"{BACKEND_API}/api/traffic/density",
                        json=density_payload,
                    )
                    response.raise_for_status()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"{YELLOW}[⚠️  WARNING]{RESET} Failed to POST frame {fn} density to backend: {e}")

        # ── Trigger emergency at frame 100 ─────────────────────────────────────
        if fn == EMERGENCY_AT_FRAME and not emergency_active:
            emergency_event = simulate_ambulance_route(
                [INTERSECTION, "INT-02", "INT-03"],
                vehicle_id="AMB-001",
            )
            await corridor_svc.activate_corridor(emergency_event)
            emergency_active = True
            total_emergency_events += 1
            _print_emergency_row(fn, emergency_event.vehicle_id, emergency_event.route)

        # ── Print every SUMMARY_EVERY frames ──────────────────────────────────
        if fn % SUMMARY_EVERY == 0:
            is_override = emergency_active and timing.is_emergency_override
            _print_row_single(
                fn, a_count, b_count,
                density.lane_a_density, density.lane_b_density,
                timing.lane_a_green_seconds, timing.lane_b_green_seconds,
                emergency=emergency_active,
                is_override=is_override,
            )

        # ── Auto-clear emergency after 30 frames ───────────────────────────────
        if emergency_active and fn == EMERGENCY_AT_FRAME + 30:
            if emergency_event:
                await corridor_svc.deactivate_full_corridor(emergency_event.event_id)
            emergency_active = False
            print(f"{DIM}{'─'*95}{RESET}")
            print(f"{GREEN}      Corridor cleared — normal signals restored{RESET}")
            print(f"{DIM}{'─'*95}{RESET}")

    # ── Release video writer ────────────────────────────────────────────────
    if _out and _out.isOpened():
        _out.release()
        print(f"{GREEN}[INFO] Annotated video saved → {_out_video_path}{RESET}")

    # ── 5. Summary ─────────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - t_start
    avg_a = sum_a_density / max(total_frames, 1)
    avg_b = sum_b_density / max(total_frames, 1)

    print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
    print(f"{BOLD}  DEMO COMPLETE — Summary{RESET}")
    print(f"{CYAN}{'═'*60}{RESET}")
    print(f"  Total frames processed  : {BOLD}{total_frames}{RESET}")
    print(f"  Elapsed time            : {elapsed:.1f}s  "
          f"({elapsed/max(total_frames,1)*1000:.1f} ms/frame)")
    print(f"  Avg Lane A density      : {_color_density(avg_a)}")
    print(f"  Avg Lane B density      : {_color_density(avg_b)}")
    print(f"  Lane A green  min/max   : {min_a_green:.1f}s / {max_a_green:.1f}s")
    print(f"  Lane B green  min/max   : {min_b_green:.1f}s / {max_b_green:.1f}s")
    print(f"  Emergency events        : {RED if total_emergency_events else DIM}"
          f"{total_emergency_events}{RESET}")
    print(f"{CYAN}{'═'*60}{RESET}\n")

    # ── Dashboard info ──────────────────────────────────────────────────────
    if os.path.exists(_out_video_path):
        print(f"{GREEN}[INFO] Annotated video ready at : {_out_video_path}{RESET}")
    print(f"{CYAN}[INFO] View stream in dashboard : http://localhost:5173{RESET}")
    print(f"{CYAN}[INFO] Direct stream URL        : http://localhost:8000/api/traffic/video/stream{RESET}\n")


async def run_multi_camera_mode(video_paths: List[str], redis: Optional[aioredis.Redis]):
    """Process 4 camera videos with multi-camera summary display."""
    for i, path in enumerate(video_paths):
        if not Path(path).exists():
            print(f"\n{RED}[ERROR] Camera {i+1} file not found: {path}{RESET}")
            sys.exit(1)

    cameras = {
        "cam_1": video_paths[0],
        "cam_2": video_paths[1],
        "cam_3": video_paths[2],
        "cam_4": video_paths[3],
    }

    print(f"\n{BOLD}Multi-Camera Mode (4 approaches):{RESET}")
    for cam_id, path in cameras.items():
        direction = CAMERA_DIRECTIONS[cam_id]
        meta = get_video_metadata(path)
        print(f"  {cam_id} ({direction:>6}): {Path(path).name}  ({meta['width']}×{meta['height']}, "
              f"{meta['fps']:.1f}fps, {meta['total_frames']} frames)")
    print()

    # Resolve model path for multi-camera mode
    import os
    from pathlib import Path as _Path
    _model_path = os.getenv("YOLO_MODEL_PATH", "ml/models/best.pt")
    if not _Path(_model_path).exists():
        print(f"{YELLOW}[WARN] best.pt not found, using yolov8n.pt fallback{RESET}")
        _model_path = "yolov8n.pt"
    else:
        print(f"{GREEN}[INFO] Using fine-tuned best.pt model{RESET}")

    # Initialize detectors and calculators per camera
    detectors = {cam_id: VehicleDetector(_model_path) for cam_id in cameras}
    calcs = {cam_id: DensityCalculator(max_capacity=20) for cam_id in cameras}
    optimizer = SignalOptimizer()

    # Open all videos
    from app.services.detector import get_video_metadata
    video_readers = {}
    for cam_id, path in cameras.items():
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"{RED}[ERROR] Cannot open {path}{RESET}")
            sys.exit(1)
        video_readers[cam_id] = cap

    # Generators
    generators = {cam_id: detectors[cam_id].process_video(cameras[cam_id]) for cam_id in cameras}

    # Accumulators
    stats = {cam_id: {"total_vehicles": 0, "sum_density": 0.0, "frames": 0, "last_density": 0.0}
             for cam_id in cameras}

    _print_header_multi()
    t_start = time.perf_counter()
    current_frame = 0

    # Process frames from all cameras in lockstep
    all_generators = {cam_id: generators[cam_id] for cam_id in cameras}
    all_done = False

    while not all_done:
        frame_results = {}
        any_active = False

        for cam_id in cameras:
            try:
                result = next(all_generators[cam_id])
                frame_results[cam_id] = result
                any_active = True
            except StopIteration:
                frame_results[cam_id] = None

        if not any_active:
            break

        # Process frame results
        current_frame = max(
            [frame_results[cam_id]["frame"] for cam_id in cameras if frame_results[cam_id]],
            default=current_frame + 1
        )

        should_print = current_frame % SUMMARY_EVERY == 0

        for cam_id in cameras:
            result = frame_results[cam_id]
            if result is None:
                continue

            a_count = result["lane_a"]["total"]
            b_count = result["lane_b"]["total"]
            density = calcs[cam_id].update(a_count, b_count)

            vehicle_count = a_count + b_count
            avg_density = (density.lane_a_density + density.lane_b_density) / 2.0

            stats[cam_id]["total_vehicles"] += vehicle_count
            stats[cam_id]["sum_density"] += avg_density
            stats[cam_id]["frames"] += 1
            stats[cam_id]["last_density"] = avg_density

            if should_print:
                time_to_clear = _calculate_time_to_clear(vehicle_count, avg_density)
                _print_row_multi(
                    cam_id,
                    CAMERA_DIRECTIONS[cam_id],
                    vehicle_count,
                    avg_density,
                    time_to_clear
                )

        if should_print:
            print(f"{DIM}{'─'*100}{RESET}")

    # Cleanup
    for cap in video_readers.values():
        cap.release()

    elapsed = time.perf_counter() - t_start

    # Print summary
    print(f"\n{BOLD}{CYAN}{'═'*100}{RESET}")
    print(f"{BOLD}  MULTI-CAMERA DEMO COMPLETE{RESET}")
    print(f"{CYAN}{'═'*100}{RESET}")

    total_vehicles_all = 0
    avg_density_all = 0.0
    for cam_id in cameras:
        frames = stats[cam_id]["frames"]
        if frames > 0:
            avg_density = stats[cam_id]["sum_density"] / frames
            total_vehicles = stats[cam_id]["total_vehicles"]
            total_vehicles_all += total_vehicles
            avg_density_all += avg_density
            print(
                f"  {cam_id} ({CAMERA_DIRECTIONS[cam_id]:>6}): "
                f"{total_vehicles:>4} vehicles, "
                f"{_color_density(avg_density):>9} avg density"
            )

    if len([c for c in cameras if stats[c]["frames"] > 0]) > 0:
        avg_density_all /= len([c for c in cameras if stats[c]["frames"] > 0])

    print(f"{DIM}{'─'*100}{RESET}")
    print(f"  Total elapsed time      : {elapsed:.1f}s")
    print(f"  Aggregate vehicles      : {total_vehicles_all}")
    print(f"  Aggregate density       : {_color_density(avg_density_all)}")
    print(f"{CYAN}{'═'*100}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
