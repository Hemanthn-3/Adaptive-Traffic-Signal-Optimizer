"""
backend/app/routers/signals.py
────────────────────────────────
Signal control endpoints.

  GET  /api/signals/all                      All signal states
  GET  /api/signals/{intersection_id}        Current state for one intersection
  POST /api/signals/{intersection_id}/manual Manually override signal timing
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request schema ─────────────────────────────────────────────────────────────
class ManualTimingRequest(BaseModel):
    lane_a_green_seconds: float
    lane_b_green_seconds: float
    reason: Optional[str] = "Manual admin override"


# ── GET /all ───────────────────────────────────────────────────────────────────
@router.get("/all", summary="All current signal states")
async def get_all_signal_states():
    """Return the latest cached signal state for every intersection."""
    redis = await get_redis()
    keys = await redis.keys("signal:state:*")
    states = []
    for key in keys:
        raw = await redis.get(key)
        if raw:
            states.append(json.loads(raw))
    return {"count": len(states), "data": states}


# ── GET /{intersection_id} ─────────────────────────────────────────────────────
@router.get("/{intersection_id}", summary="Current signal state for one intersection")
async def get_signal_state(intersection_id: str):
    """Return the latest signal timing stored in Redis for *intersection_id*."""
    redis = await get_redis()
    raw = await redis.get(f"signal:state:{intersection_id}")
    if not raw:
        raise HTTPException(
            status_code=404,
            detail=f"No signal state found for intersection '{intersection_id}'."
        )
    return json.loads(raw)


# ── POST /{intersection_id}/manual ────────────────────────────────────────────
@router.post("/{intersection_id}/manual", summary="Manually set signal timing (admin)")
async def set_manual_timing(
    intersection_id: str,
    body: ManualTimingRequest,
    request: Request,
):
    """
    Admin endpoint: override adaptive timing with explicit green durations.

    Stores in Redis, publishes MQTT command, and broadcasts a WebSocket
    ``signal_update`` event to the dashboard.
    """
    import datetime

    if body.lane_a_green_seconds + body.lane_b_green_seconds <= 0:
        raise HTTPException(status_code=400, detail="Green seconds must sum to a positive value.")

    cycle = body.lane_a_green_seconds + body.lane_b_green_seconds

    state = {
        "intersection_id": intersection_id,
        "lane_a_green_seconds": body.lane_a_green_seconds,
        "lane_b_green_seconds": body.lane_b_green_seconds,
        "lane_a_red_seconds": body.lane_b_green_seconds,
        "lane_b_red_seconds": body.lane_a_green_seconds,
        "cycle_time": cycle,
        "optimization_reason": body.reason,
        "is_emergency_override": False,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "source": "manual",
    }

    redis = await get_redis()
    await redis.set(f"signal:state:{intersection_id}", json.dumps(state), ex=600)

    # MQTT publish
    mqtt = request.app.state.mqtt
    mqtt.publish(
        f"traffic/signals/{intersection_id}/command",
        json.dumps({
            "command": "SET_TIMING",
            "lane_a_green": body.lane_a_green_seconds,
            "lane_b_green": body.lane_b_green_seconds,
        }),
    )

    # WebSocket broadcast
    ws_manager = request.app.state.ws_manager
    await ws_manager.broadcast({"type": "signal_update", "data": state})

    logger.info("Manual override applied to %s: A=%ss B=%ss", intersection_id,
                body.lane_a_green_seconds, body.lane_b_green_seconds)
    return {"status": "applied", "state": state}
