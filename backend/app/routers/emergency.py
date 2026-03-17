"""
backend/app/routers/emergency.py
──────────────────────────────────
Emergency green-corridor endpoints.

  POST /api/emergency/activate    Start a green corridor
  POST /api/emergency/deactivate  End a green corridor
  GET  /api/emergency/active      List all active corridors
  POST /api/emergency/simulate    Trigger a test ambulance (demo)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.corridor import EmergencyEvent, simulate_ambulance_route

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / response schemas ─────────────────────────────────────────────────
class ActivateRequest(BaseModel):
    vehicle_id: str
    vehicle_type: str = "ambulance"
    route: List[str]                   # ordered list of intersection IDs

class DeactivateRequest(BaseModel):
    event_id: str

class SimulateRequest(BaseModel):
    intersection_ids: Optional[List[str]] = None
    vehicle_id: str = "AMB-SIM-001"
    vehicle_type: str = "ambulance"


# ── POST /activate ─────────────────────────────────────────────────────────────
@router.post("/activate", summary="Start a green corridor for an emergency vehicle")
async def activate_corridor(body: ActivateRequest, request: Request):
    """
    Pre-clears all intersections on the route to GREEN and stores the active
    event in Redis with a 90-second TTL.
    """
    if not body.route:
        raise HTTPException(status_code=400, detail="Route must contain at least one intersection ID.")

    corridor_svc = request.app.state.corridor
    ws_manager = request.app.state.ws_manager

    event = simulate_ambulance_route(
        intersection_ids=body.route,
        vehicle_id=body.vehicle_id,
        vehicle_type=body.vehicle_type,
    )

    await corridor_svc.activate_corridor(event)

    # Broadcast signal override — force both lanes GREEN
    await ws_manager.broadcast({
        "type": "signal_update",
        "data": {
            "lane_a_green": 90,
            "lane_b_green": 90,
            "lane_a_red": 0,
            "lane_b_red": 0,
            "lane_a_green_seconds": 90,
            "lane_b_green_seconds": 90,
            "lane_a_red_seconds": 0,
            "lane_b_red_seconds": 0,
            "lane_a_state": "green",
            "lane_b_state": "green",
            "cycle_time": 90,
            "reason": "EMERGENCY OVERRIDE — Ambulance corridor active. All signals GREEN.",
            "optimization_reason": "EMERGENCY OVERRIDE — Ambulance corridor active. All signals GREEN.",
            "is_emergency": True,
            "is_emergency_override": True,
        },
    })

    # Broadcast emergency alert to the dashboard
    await ws_manager.broadcast({
        "type": "emergency_alert",
        "data": {
            "vehicle_id": body.vehicle_id,
            "route": " → ".join(body.route),
            "status": "active",
            "start_time": datetime.utcnow().isoformat(),
            **event.to_dict(),
        },
    })

    logger.info("Green corridor activated: %s → %s", event.vehicle_id, event.route)
    return {"status": "activated", "event": event.to_dict()}


# ── POST /deactivate ───────────────────────────────────────────────────────────
@router.post("/deactivate", summary="End a green corridor")
async def deactivate_corridor(body: DeactivateRequest, request: Request):
    """
    Restores normal signal timing for all intersections on the route
    and publishes a clear event.
    """
    corridor_svc = request.app.state.corridor
    ws_manager = request.app.state.ws_manager

    # Verify event exists first
    active = await corridor_svc.get_active_corridors()
    match = next((e for e in active if e.event_id == body.event_id), None)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active corridor found with event_id='{body.event_id}'."
        )

    await corridor_svc.deactivate_full_corridor(body.event_id)

    # Restore normal signals
    await ws_manager.broadcast({
        "type": "signal_update",
        "data": {
            "lane_a_green": 30,
            "lane_b_green": 30,
            "lane_a_green_seconds": 30,
            "lane_b_green_seconds": 30,
            "lane_a_red": 30,
            "lane_b_red": 30,
            "lane_a_red_seconds": 30,
            "lane_b_red_seconds": 30,
            "cycle_time": 60,
            "reason": "Normal adaptive mode restored.",
            "optimization_reason": "Normal adaptive mode restored.",
            "is_emergency": False,
            "is_emergency_override": False,
        },
    })

    # Broadcast clear signal to dashboard
    await ws_manager.broadcast({
        "type": "emergency_clear",
        "data": {"event_id": body.event_id},
    })

    logger.info("Green corridor deactivated: %s", body.event_id)
    return {"status": "deactivated", "event_id": body.event_id}


# ── GET /active ────────────────────────────────────────────────────────────────
@router.get("/active", summary="List all active emergency corridors")
async def list_active_corridors(request: Request):
    """Return all currently active EmergencyEvents from Redis."""
    corridor_svc = request.app.state.corridor
    events = await corridor_svc.get_active_corridors()
    return {
        "count": len(events),
        "data": [e.to_dict() for e in events],
    }


# ── POST /simulate ─────────────────────────────────────────────────────────────
@router.post("/simulate", summary="Trigger a test ambulance route (demo)")
async def simulate_corridor(body: SimulateRequest, request: Request):
    """
    Creates a synthetic emergency event and activates a green corridor.
    Uses a default 4-intersection route if none is provided.
    """
    corridor_svc = request.app.state.corridor
    ws_manager = request.app.state.ws_manager

    route = body.intersection_ids or ["INT-01", "INT-02", "INT-03", "INT-04"]

    event = simulate_ambulance_route(
        intersection_ids=route,
        vehicle_id=body.vehicle_id,
        vehicle_type=body.vehicle_type,
    )

    await corridor_svc.activate_corridor(event)

    # Broadcast signal override — force both lanes GREEN
    await ws_manager.broadcast({
        "type": "signal_update",
        "data": {
            "lane_a_green": 90,
            "lane_b_green": 90,
            "lane_a_red": 0,
            "lane_b_red": 0,
            "lane_a_green_seconds": 90,
            "lane_b_green_seconds": 90,
            "lane_a_red_seconds": 0,
            "lane_b_red_seconds": 0,
            "lane_a_state": "green",
            "lane_b_state": "green",
            "cycle_time": 90,
            "reason": "EMERGENCY OVERRIDE — Ambulance corridor active. All signals GREEN.",
            "optimization_reason": "EMERGENCY OVERRIDE — Ambulance corridor active. All signals GREEN.",
            "is_emergency": True,
            "is_emergency_override": True,
        },
    })

    # Broadcast emergency alert
    await ws_manager.broadcast({
        "type": "emergency_alert",
        "data": {
            "vehicle_id": body.vehicle_id,
            "route": "INT-01 → INT-02 → INT-03 → INT-04",
            "status": "active",
            "start_time": datetime.utcnow().isoformat(),
            **event.to_dict(),
        },
    })

    logger.info("Simulated corridor: %s", event.event_id)
    return {
        "status": "simulated",
        "message": f"Test {body.vehicle_type} '{body.vehicle_id}' dispatched on route {route}.",
        "event": event.to_dict(),
    }


# ── POST /auto-detected ────────────────────────────────────────────────────────
class AutoDetectedEmergencyRequest(BaseModel):
    vehicle_id: str = "AUTO-DETECTED"
    vehicle_type: str = "ambulance"
    route: Optional[List[str]] = None
    auto_detected: bool = True
    confidence: float = 1.0  # 0.0-100.0


@router.post("/auto-detected", summary="Handle auto-detected emergency vehicles from ML pipeline")
async def handle_auto_detected_emergency(body: AutoDetectedEmergencyRequest, request: Request):
    """
    Process auto-detected emergency vehicles from the YOLOv8 ML pipeline.
    
    Activates a green corridor if confidence > EMERGENCY_DETECTION_CONFIDENCE threshold.
    Auto-clears after EMERGENCY_AUTO_CLEAR_SECONDS.
    """
    from app.config import settings
    
    # Normalize confidence to 0.0-1.0 if it's 0.0-100.0
    confidence = body.confidence / 100.0 if body.confidence > 1.0 else body.confidence
    
    # Check confidence threshold
    if confidence < settings.EMERGENCY_DETECTION_CONFIDENCE:
        logger.info(
            "Auto-detected emergency rejected: confidence %.2f < threshold %.2f",
            confidence,
            settings.EMERGENCY_DETECTION_CONFIDENCE
        )
        return {
            "status": "rejected",
            "reason": f"Confidence {confidence:.2f} below threshold {settings.EMERGENCY_DETECTION_CONFIDENCE:.2f}",
            "vehicle_id": body.vehicle_id,
        }
    
    corridor_svc = request.app.state.corridor
    ws_manager = request.app.state.ws_manager
    
    # Default route if not provided
    route = body.route or ["INT-01", "INT-02", "INT-03", "INT-04"]
    
    # Create and activate the emergency event
    event = simulate_ambulance_route(
        intersection_ids=route,
        vehicle_id=body.vehicle_id,
        vehicle_type=body.vehicle_type,
    )
    
    await corridor_svc.activate_corridor(event)
    
    # Broadcast signal override — force both lanes GREEN
    await ws_manager.broadcast({
        "type": "signal_update",
        "data": {
            "lane_a_green": settings.EMERGENCY_GREEN_DURATION,
            "lane_b_green": settings.EMERGENCY_GREEN_DURATION,
            "lane_a_red": 0,
            "lane_b_red": 0,
            "lane_a_green_seconds": settings.EMERGENCY_GREEN_DURATION,
            "lane_b_green_seconds": settings.EMERGENCY_GREEN_DURATION,
            "lane_a_red_seconds": 0,
            "lane_b_red_seconds": 0,
            "cycle_time": settings.EMERGENCY_GREEN_DURATION,
            "reason": "AUTO-DETECTED EMERGENCY — Ambulance corridor active. All signals GREEN.",
            "optimization_reason": "AUTO-DETECTED EMERGENCY — Ambulance corridor active. All signals GREEN.",
            "is_emergency": True,
            "is_emergency_override": True,
            "auto_detected": True,
            "confidence": confidence,
        },
    })
    
    # Broadcast emergency alert to dashboard
    await ws_manager.broadcast({
        "type": "emergency_alert",
        "data": {
            "vehicle_id": body.vehicle_id,
            "vehicle_type": body.vehicle_type,
            "route": " → ".join(route),
            "status": "active",
            "auto_detected": True,
            "confidence": confidence,
            "start_time": datetime.utcnow().isoformat(),
            "auto_clear_seconds": settings.EMERGENCY_AUTO_CLEAR_SECONDS,
            **event.to_dict(),
        },
    })
    
    logger.info(
        "Auto-detected emergency activated: %s (confidence=%.2f, route=%s)",
        body.vehicle_id,
        confidence,
        " → ".join(route)
    )
    
    return {
        "status": "activated",
        "vehicle_id": body.vehicle_id,
        "confidence": confidence,
        "auto_clear_seconds": settings.EMERGENCY_AUTO_CLEAR_SECONDS,
        "event": event.to_dict(),
    }
