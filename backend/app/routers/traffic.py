"""
backend/app/routers/traffic.py
────────────────────────────────
Traffic data endpoints with multi-camera support.

  GET  /api/traffic/density          Latest density report for all intersections
  POST /api/traffic/density          Store density data from demo/external clients
  GET  /api/traffic/density/history  Last 100 density readings (paginated)
  POST /api/traffic/video/process    Upload + process a single camera video (multipart)
  POST /api/traffic/video/process-all Process all 4 cameras in parallel (multipart)
  GET  /api/traffic/cameras/{intersection_id}  Camera status snapshot for intersection
  GET  /api/traffic/intersections    List all intersections
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.core.websocket_manager import ws_manager
from app.services.optimizer import SignalOptimizer

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Absolute video paths (resolved from this file's location) ─────────────────
# This file lives at  backend/app/routers/traffic.py
# Three levels up lands at the project root.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

PROCESSED_VIDEO = os.path.join(
    PROJECT_ROOT, "ml", "test_videos", "processed_sample_video.avi"
)
SAMPLE_VIDEO = os.path.join(
    PROJECT_ROOT, "ml", "test_videos", "sample_video.mp4"
)

print(f"[INFO] Looking for video at: {PROCESSED_VIDEO}")


def find_video() -> str | None:
    """Return the best available video path, or None if neither exists."""
    if os.path.exists(PROCESSED_VIDEO):
        return PROCESSED_VIDEO
    if os.path.exists(SAMPLE_VIDEO):
        return SAMPLE_VIDEO
    return None



CAMERA_DIRECTIONS = {
    "cam_1": "North",
    "cam_2": "South",
    "cam_3": "East",
    "cam_4": "West",
}

CAMERA_IDS = set(CAMERA_DIRECTIONS.keys())

# ── In-memory camera state (camera_id -> {status, density, timestamp}) ────────
camera_state: Dict[str, Dict[str, Any]] = {}
for cam_id in CAMERA_IDS:
    camera_state[cam_id] = {
        "status": "idle",
        "density": None,
        "lane_a_count": 0,
        "lane_b_count": 0,
        "last_updated": None,
    }

# ── In-memory fallback state (used when Redis/DB is unavailable) ───────────────
current_density: Dict[str, Any] = {}
current_signal: Dict[str, Any] = {}
_density_history: List[Dict[str, Any]] = []   # keeps last 200 readings

_optimizer = SignalOptimizer()
STREAM_INTERSECTION_ID = "INT-VIDEO-STREAM"
STREAM_CAMERA_ID = "cam_1"
STREAM_BROADCAST_EVERY = 30
_video_stream_clients = 0
_video_stream_lock: asyncio.Lock | None = None


def _get_density_level(density: float) -> str:
    if density <= 30:
        return "low"
    if density <= 60:
        return "medium"
    if density <= 80:
        return "high"
    return "critical"


def _get_video_stream_lock() -> asyncio.Lock:
    global _video_stream_lock
    if _video_stream_lock is None:
        _video_stream_lock = asyncio.Lock()
    return _video_stream_lock


async def _set_video_stream_active(active: bool) -> None:
    """Pause simulator broadcasts while one or more MJPEG viewers are active."""
    global _video_stream_clients
    lock = _get_video_stream_lock()
    async with lock:
        from app.services.simulator import simulator as traffic_simulator

        if active:
            _video_stream_clients += 1
            if _video_stream_clients == 1:
                traffic_simulator.pause("video_stream")
        elif _video_stream_clients > 0:
            _video_stream_clients -= 1
            if _video_stream_clients == 0:
                traffic_simulator.resume("video_stream")


def _build_stream_density_payload(
    frame_number: int,
    lane_a_count: int,
    lane_b_count: int,
    lane_a_density: float,
    lane_b_density: float,
) -> Dict[str, Any]:
    timestamp = datetime.utcnow().isoformat()
    avg_density = (lane_a_density + lane_b_density) / 2.0
    return {
        "intersection_id": STREAM_INTERSECTION_ID,
        "camera_id": STREAM_CAMERA_ID,
        "direction": CAMERA_DIRECTIONS[STREAM_CAMERA_ID],
        "frame_number": frame_number,
        "lane_a_count": lane_a_count,
        "lane_b_count": lane_b_count,
        "lane_a_density": round(lane_a_density, 2),
        "lane_b_density": round(lane_b_density, 2),
        "lane_a_level": _get_density_level(lane_a_density),
        "lane_b_level": _get_density_level(lane_b_density),
        "density": round(avg_density, 2),
        "timestamp": timestamp,
        "source": "video_stream",
    }


# ── GET /density ───────────────────────────────────────────────────────────────
@router.get("/density", summary="Latest density report for all intersections")
async def get_density_all():
    """Return the most recent density reading stored in Redis for every lane.
    Falls back to in-memory state if Redis is unavailable."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        keys = await redis.keys("density:lane:*")
        result: List[Dict[str, Any]] = []
        for key in keys:
            raw = await redis.get(key)
            if raw:
                result.append(json.loads(raw))
        return {"count": len(result), "data": result}
    except Exception:
        if current_density:
            return {"count": 1, "data": [current_density]}
        return {"count": 0, "data": []}


# ── GET /density/history ───────────────────────────────────────────────────────
@router.get("/density/history", summary="Paginated density history (last 100)")
async def get_density_history(
    lane_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
):
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()

        if lane_id is not None:
            raw_items = await redis.lrange(f"density:history:{lane_id}", offset, offset + limit - 1)
        else:
            all_keys = await redis.keys("density:history:*")
            raw_items = []
            for k in all_keys:
                items = await redis.lrange(k, 0, limit - 1)
                raw_items.extend(items)
            raw_items = raw_items[offset: offset + limit]

        history = []
        for raw in raw_items:
            try:
                history.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        return {"count": len(history), "offset": offset, "data": history}
    except Exception:
        return {"count": 0, "offset": offset, "data": []}


# ── POST /density ──────────────────────────────────────────────────────────────
@router.post("/density", summary="Store density data from demo or external clients")
async def post_density(payload: Dict[str, Any]):
    """
    Accept density data from the demo script or other clients.
    Always returns 200. Falls back to in-memory state if Redis/DB is down.

    Expected payload:
    {
        "intersection_id": "INT-DEMO-01",
        "frame_number": 150,
        "lane_a_count": 12,
        "lane_b_count": 8,
        "lane_a_density": 60.0,
        "lane_b_density": 40.0,
    }
    """
    required = {"intersection_id", "frame_number", "lane_a_count", "lane_b_count",
                "lane_a_density", "lane_b_density"}
    if not required.issubset(payload.keys()):
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {required - set(payload.keys())}"
        )

    frame = payload.get("frame_number", 0)
    a_count = int(payload["lane_a_count"])
    b_count = int(payload["lane_b_count"])
    a_density = float(payload["lane_a_density"])
    b_density = float(payload["lane_b_density"])
    intersection_id = payload["intersection_id"]

    # Derive level from density
    def _level(d: float) -> str:
        if d <= 30: return "low"
        if d <= 60: return "medium"
        if d <= 80: return "high"
        return "critical"

    timestamp = datetime.utcnow().isoformat()

    # ── Try to save to Redis (silently skip if unavailable) ────────────────────
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        key_latest = f"density:lane:{intersection_id}:latest"
        key_history = f"density:history:{intersection_id}"
        await redis.set(key_latest, json.dumps(payload), ex=300)
        await redis.lpush(key_history, json.dumps(payload))
        await redis.ltrim(key_history, 0, 999)
    except Exception as exc:
        logger.debug("Redis unavailable, using in-memory state: %s", exc)

    # ── Always update in-memory state ─────────────────────────────────────────
    global current_density, current_signal, _density_history
    current_density = {
        "lane_a_count": a_count,
        "lane_b_count": b_count,
        "lane_a_density": a_density,
        "lane_b_density": b_density,
        "lane_a_level": _level(a_density),
        "lane_b_level": _level(b_density),
        "timestamp": timestamp,
    }

    # Append to history, cap at 200
    _density_history.append(current_density.copy())
    if len(_density_history) > 200:
        _density_history = _density_history[-200:]

    # ── Always broadcast density_update ───────────────────────────────────────
    await ws_manager.broadcast({
        "type": "density_update",
        "data": current_density,
    })

    # ── Calculate signal timing and broadcast signal_update ───────────────────
    timing = _optimizer.compute(intersection_id, a_density, b_density)
    current_signal = {
        "lane_a_green": timing.lane_a_green_seconds,
        "lane_b_green": timing.lane_b_green_seconds,
        "lane_a_red": timing.lane_a_red_seconds,
        "lane_b_red": timing.lane_b_red_seconds,
        "reason": timing.optimization_reason,
        "is_emergency": timing.is_emergency_override,
    }

    await ws_manager.broadcast({
        "type": "signal_update",
        "data": current_signal,
    })

    logger.info("Density received: intersection=%s frame=%d a=%.1f%% b=%.1f%%",
                intersection_id, frame, a_density, b_density)
    return {"status": "ok", "frame": frame}


# Track current processing status
processing_status = {
    "running": False,
    "filename": None,
    "progress": 0,
    "message": ""
}

# ── POST /video/upload ─────────────────────────────────────────────────────────
@router.post("/video/upload", summary="Upload a video and automatically run demo.py")
async def upload_and_process(file: UploadFile = File(...)):
    import subprocess
    import threading

    # Check if already processing
    if processing_status["running"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Already processing a video. Wait for it to finish."}
        )
    
    # Save uploaded file to ml/test_videos/
    save_dir = os.path.join(PROJECT_ROOT, "ml", "test_videos")
    os.makedirs(save_dir, exist_ok=True)
    
    # Save with original filename
    save_path = os.path.join(save_dir, file.filename)
    
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    logger.info(f"Video saved: {save_path}")
    
    # Run demo.py automatically in background thread
    def run_demo():
        processing_status["running"] = True
        processing_status["filename"] = file.filename
        processing_status["message"] = f"Processing {file.filename}..."
        
        demo_path = os.path.join(PROJECT_ROOT, "demo.py")
        video_path = f"ml/test_videos/{file.filename}"
        
        logger.info(f"Running: python {demo_path} {video_path}")
        
        try:
            result = subprocess.run(
                ["python", demo_path, video_path],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300  # 5 min max
            )
            processing_status["message"] = "Processing complete!"
            logger.info(f"Demo output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Demo errors: {result.stderr}")
        except subprocess.TimeoutExpired:
            processing_status["message"] = "Processing timed out"
        except Exception as e:
            processing_status["message"] = f"Error: {str(e)}"
        finally:
            processing_status["running"] = False
    
    thread = threading.Thread(target=run_demo, daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "filename": file.filename,
        "saved_to": save_path,
        "message": f"Video saved and demo.py started for {file.filename}"
    }

# ── GET /video/status ──────────────────────────────────────────────────────────
@router.get("/video/status", summary="Get status of background video processing")
async def get_processing_status():
    return processing_status


# ── GET /cameras/{intersection_id} ─────────────────────────────────────────────
@router.get("/cameras/{intersection_id}", summary="Get status of all cameras at intersection")
async def get_cameras(intersection_id: str):
    """Return the status of all 4 cameras for an intersection.
    
    Parameters
    ----------
    intersection_id : str
        The intersection ID
    
    Returns
    -------
    dict
        Camera statuses indexed by camera_id
    """
    result = {}
    for cam_id in CAMERA_IDS:
        state = camera_state[cam_id]
        result[cam_id] = {
            "status": state["status"],
            "direction": CAMERA_DIRECTIONS[cam_id],
            "density": state["density"],
            "lane_a_count": state["lane_a_count"],
            "lane_b_count": state["lane_b_count"],
            "last_updated": state["last_updated"],
        }
    return {"intersection_id": intersection_id, "cameras": result}


# ── POST /video/process-all ────────────────────────────────────────────────────
@router.post("/video/process-all", summary="Process all 4 camera videos in parallel")
async def process_all_cameras(
    request: Request,
    intersection_id: str = Form(...),
    cam1: Optional[UploadFile] = File(None),
    cam2: Optional[UploadFile] = File(None),
    cam3: Optional[UploadFile] = File(None),
    cam4: Optional[UploadFile] = File(None),
):
    """Process up to 4 camera videos in parallel for an intersection.
    
    Parameters
    ----------
    intersection_id : str
        The intersection ID
    cam1, cam2, cam3, cam4 : UploadFile (optional)
        Video files for each camera
    
    Returns
    -------
    dict
        Aggregated results and status
    """
    files = {
        "cam_1": cam1,
        "cam_2": cam2,
        "cam_3": cam3,
        "cam_4": cam4,
    }

    # Prepare tasks
    tasks = []
    temp_files = {}

    for cam_id, file in files.items():
        if file is None:
            logger.info("Camera %s not provided for %s", cam_id, intersection_id)
            continue

        if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format for {cam_id}: {file.filename}"
            )

        # Save temp file
        suffix = os.path.splitext(file.filename)[-1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await file.read())
        tmp.close()
        temp_files[cam_id] = tmp.name

        # Create processing task
        tasks.append((cam_id, tmp.name))

    # Process all in parallel
    results = {}
    if tasks:
        results = await asyncio.gather(
            *[
                _process_single_camera_async(request, intersection_id, cam_id, video_path)
                for cam_id, video_path in tasks
            ],
            return_exceptions=True,
        )
        results = {cam_id: res for (cam_id, _), res in zip(tasks, results)}

    # Cleanup
    for path in temp_files.values():
        try:
            os.unlink(path)
        except Exception:
            pass

    # Aggregate results
    total_vehicles = 0
    active_cameras = 0
    avg_density = 0.0

    for cam_id in CAMERA_IDS:
        if cam_id in results and isinstance(results[cam_id], dict):
            state = camera_state[cam_id]
            if state["density"] is not None:
                total_vehicles += state["lane_a_count"] + state["lane_b_count"]
                avg_density += state["density"]
                active_cameras += 1

    if active_cameras > 0:
        avg_density /= active_cameras

    return {
        "status": "processing_complete",
        "intersection_id": intersection_id,
        "cameras_processed": len(results),
        "total_vehicles": total_vehicles,
        "aggregate_density": avg_density,
        "busiest_camera": max(
            [(cam_id, camera_state[cam_id]["density"] or 0.0) for cam_id in CAMERA_IDS],
            key=lambda x: x[1],
        )[0] if active_cameras > 0 else None,
        "camera_results": {
            cam_id: {
                "status": camera_state[cam_id]["status"],
                "lane_a_count": camera_state[cam_id]["lane_a_count"],
                "lane_b_count": camera_state[cam_id]["lane_b_count"],
                "density": camera_state[cam_id]["density"],
            }
            for cam_id in CAMERA_IDS
        },
    }


async def _process_single_camera_async(
    request: Request,
    intersection_id: str,
    camera_id: str,
    video_path: str,
) -> dict:
    """Process a single camera video asynchronously.
    
    This is a helper for process_all_cameras.
    """
    camera_state[camera_id]["status"] = "processing"

    try:
        from app.services.detector import VehicleDetector
        from app.services.density import DensityCalculator

        detector = VehicleDetector()
        density_calc = DensityCalculator()

        ws_mgr = request.app.state.ws_manager
        frames_processed = 0
        total_a = total_b = 0
        last_avg_density = 0.0

        for frame_result in detector.process_video(video_path):
            fn = frame_result["frame"]
            a_count = frame_result["lane_a"]["total"]
            b_count = frame_result["lane_b"]["total"]

            report = density_calc.update(a_count, b_count)
            frames_processed += 1
            total_a += a_count
            total_b += b_count
            last_avg_density = (report.lane_a_density + report.lane_b_density) / 2.0

            if fn % 5 == 0:
                lane_data = {
                    "intersection_id": intersection_id,
                    "camera_id": camera_id,
                    "direction": CAMERA_DIRECTIONS[camera_id],
                    "frame": fn,
                    "lane_a_count": a_count,
                    "lane_b_count": b_count,
                    "density": last_avg_density,
                    "timestamp": report.timestamp.isoformat(),
                }
                await ws_mgr.broadcast({
                    "type": "camera_update",
                    "data": lane_data
                })

        camera_state[camera_id]["status"] = "active"
        camera_state[camera_id]["density"] = last_avg_density
        camera_state[camera_id]["lane_a_count"] = total_a
        camera_state[camera_id]["lane_b_count"] = total_b
        camera_state[camera_id]["last_updated"] = datetime.utcnow().isoformat()

        return {
            "camera_id": camera_id,
            "frames_processed": frames_processed,
        }

    except Exception as exc:
        logger.error("Camera %s processing failed: %s", camera_id, exc)
        camera_state[camera_id]["status"] = "error"
        return {"camera_id": camera_id, "error": str(exc)}


@router.get("/intersections", summary="List all known intersections")
async def list_intersections():
    """Return all intersections from Redis cache (populated on startup or seed)."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        raw = await redis.get("intersections:all")
        if raw:
            intersections = json.loads(raw)
        else:
            raise Exception("Not in Redis")
    except Exception:
        intersections = [
            {"id": "INT-01", "name": "MG Road & Brigade Road",    "latitude": 12.9757, "longitude": 77.6011},
            {"id": "INT-02", "name": "Silk Board Junction",        "latitude": 12.9174, "longitude": 77.6229},
            {"id": "INT-03", "name": "KR Circle",                  "latitude": 12.9762, "longitude": 77.5713},
            {"id": "INT-04", "name": "Hebbal Flyover",             "latitude": 13.0352, "longitude": 77.5969},
        ]

    return {"count": len(intersections), "data": intersections}


# ── GET /video/annotated ───────────────────────────────────────────────────────
@router.get("/video/annotated", summary="Download the YOLOv8-annotated video")
async def get_annotated_video():
    """Return the processed (annotated) video as a downloadable file."""
    video_path = find_video()
    if not video_path:
        raise HTTPException(status_code=404, detail="No video file found")
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename="annotated_traffic.mp4",
    )


# ── GET /video/stream ──────────────────────────────────────────────────────────
@router.get("/video/stream", summary="Stream annotated video as MJPEG")
async def stream_video():
    """
    Stream video frames as a looping MJPEG feed suitable for an <img> tag
    in the browser.  Converts AVI/MP4 frame-by-frame via OpenCV so the
    browser receives a standard multipart/x-mixed-replace stream.
    Falls back to sample_video.mp4 when the processed file is absent.
    """
    import cv2 as _cv2
    from app.services.density import DensityCalculator
    from app.services.detector import VehicleDetector

    video_path = find_video()
    if not video_path:
        raise HTTPException(status_code=404, detail="No video file found")

    detector = VehicleDetector()
    density_calc = DensityCalculator()

    async def generate_frames():
        global current_density

        cap = _cv2.VideoCapture(video_path)
        fps = cap.get(_cv2.CAP_PROP_FPS) or 25
        frame_delay = 1.0 / fps
        frame_number = 0

        try:
            await _set_video_stream_active(True)
            while True:
                ret, frame = cap.read()
                if not ret:
                    # Loop: seek back to the beginning
                    cap.set(_cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_number = 0
                    density_calc.reset()
                    continue

                frame_number += 1
                frame_result = detector.process_frame(frame, frame_number=frame_number, fps=fps)
                lane_a_count = int(frame_result["lane_a"]["total"])
                lane_b_count = int(frame_result["lane_b"]["total"])
                density_report = density_calc.update(lane_a_count, lane_b_count)

                if frame_number % STREAM_BROADCAST_EVERY == 0:
                    payload = _build_stream_density_payload(
                        frame_number=frame_number,
                        lane_a_count=lane_a_count,
                        lane_b_count=lane_b_count,
                        lane_a_density=density_report.lane_a_density,
                        lane_b_density=density_report.lane_b_density,
                    )
                    current_density = payload.copy()
                    camera_state[STREAM_CAMERA_ID].update(
                        {
                            "status": "active",
                            "density": payload["density"],
                            "lane_a_count": lane_a_count,
                            "lane_b_count": lane_b_count,
                            "last_updated": payload["timestamp"],
                        }
                    )
                    await ws_manager.broadcast(
                        {
                            "type": "density_update",
                            "intersection_id": STREAM_INTERSECTION_ID,
                            "data": payload,
                        }
                    )

                _, buffer = _cv2.imencode(
                    ".jpg", frame,
                    [_cv2.IMWRITE_JPEG_QUALITY, 85],
                )
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )
                await asyncio.sleep(frame_delay)
        finally:
            cap.release()
            await _set_video_stream_active(False)

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
