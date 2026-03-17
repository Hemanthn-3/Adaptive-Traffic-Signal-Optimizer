"""
backend/app/services/corridor.py
──────────────────────────────────
Green Corridor emergency-vehicle priority system.

How it works
────────────
1.  Dispatcher creates an EmergencyEvent describing the ambulance route
    (ordered list of intersection IDs).
2.  GreenCorridorService.activate_corridor() iterates the route:
      • Publishes a FORCE_GREEN MQTT command to each intersection.
      • Stores the event in Redis with a TTL of GREEN_TTL_SECONDS (90 s).
      • Broadcasts a JSON alert on traffic/emergency/alert.
3.  As the ambulance clears each intersection, the operator (or automation)
    calls deactivate_intersection() to restore normal signal timing.
4.  When the ambulance reaches its destination, deactivate_full_corridor()
    clears all remaining intersections and publishes a CLEAR alert.

MQTT topics
───────────
  traffic/signals/{intersection_id}/command  → "FORCE_GREEN"
  traffic/signals/{intersection_id}/restore  → "RESTORE_NORMAL"
  traffic/emergency/alert                    → JSON of EmergencyEvent
  traffic/emergency/clear                    → event_id (plain string)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Defaults ───────────────────────────────────────────────────────────────────
GREEN_TTL_SECONDS: int = 90          # how long each intersection stays forced-green
ESTIMATED_TRAVEL_MINUTES: int = 10   # used by simulate_ambulance_route


# ── Dataclass ──────────────────────────────────────────────────────────────────

@dataclass
class EmergencyEvent:
    """Represents a single emergency-vehicle corridor activation."""

    event_id: str                      # UUID (auto-generated)
    vehicle_id: str                    # e.g. "AMB-001"
    vehicle_type: str                  # "ambulance" | "fire_truck" | "police"
    route: List[str]                   # ordered list of intersection IDs
    dispatch_time: datetime
    estimated_arrival: datetime
    status: str                        # "active" | "completed" | "cancelled"
    current_intersection: Optional[str] = None

    # ── Serialisation helpers ────────────────────────────────────────────────
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["dispatch_time"] = self.dispatch_time.isoformat()
        d["estimated_arrival"] = self.estimated_arrival.isoformat()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "EmergencyEvent":
        data = dict(data)
        data["dispatch_time"] = datetime.fromisoformat(data["dispatch_time"])
        data["estimated_arrival"] = datetime.fromisoformat(data["estimated_arrival"])
        return cls(**data)


# ── Service ────────────────────────────────────────────────────────────────────

class GreenCorridorService:
    """Manages emergency green corridors via MQTT commands and Redis state.

    Parameters
    ----------
    signal_optimizer :
        Instance of ``SignalOptimizer`` – used to compute the normal timing
        that is restored after a corridor deactivation.
    mqtt_client :
        Instance of ``MQTTClient`` with a ``publish(topic, payload)`` method.
    redis_client :
        An **async** redis-py client (``redis.asyncio.Redis``).  Pass ``None``
        to run without persistence (in-memory fallback).
    green_ttl : int
        Seconds each intersection remains force-green (default 90).
    """

    def __init__(
        self,
        signal_optimizer,
        mqtt_client,
        redis_client=None,
        green_ttl: int = GREEN_TTL_SECONDS,
    ) -> None:
        self._optimizer = signal_optimizer
        self._mqtt = mqtt_client
        self._redis = redis_client
        self._green_ttl = green_ttl

        # In-memory fallback when Redis is unavailable
        self._local_store: Dict[str, EmergencyEvent] = {}

    # ── Activate ───────────────────────────────────────────────────────────────

    async def activate_corridor(self, event: EmergencyEvent) -> None:
        """Pre-clear all intersections on the route to GREEN.

        Steps
        -----
        1. Store the event (Redis with TTL, or local dict).
        2. MQTT FORCE_GREEN to every intersection on the route.
        3. Broadcast JSON alert on ``traffic/emergency/alert``.
        """
        event.status = "active"

        # Persist event
        await self._store_event(event)

        logger.info(
            "Activating green corridor for %s route=%s",
            event.vehicle_id, event.route,
        )

        # Send FORCE_GREEN to every intersection on the route
        for intersection_id in event.route:
            topic = f"traffic/signals/{intersection_id}/command"
            payload = json.dumps({
                "command": "FORCE_GREEN",
                "event_id": event.event_id,
                "vehicle_id": event.vehicle_id,
                "green_ttl_seconds": self._green_ttl,
            })
            self._mqtt.publish(topic, payload)
            logger.debug("FORCE_GREEN → %s", topic)

        # Broadcast real-time alert to dashboard
        self._mqtt.publish("traffic/emergency/alert", event.to_json())
        logger.info("Green corridor activated: event_id=%s", event.event_id)

    # ── Deactivate one intersection ────────────────────────────────────────────

    async def deactivate_intersection(self, intersection_id: str) -> None:
        """Restore normal signal timing for a single intersection.

        Called progressively as the ambulance clears each intersection.
        """
        topic = f"traffic/signals/{intersection_id}/restore"
        payload = json.dumps({
            "command": "RESTORE_NORMAL",
            "intersection_id": intersection_id,
        })
        self._mqtt.publish(topic, payload)
        logger.info("RESTORE_NORMAL → intersection %s", intersection_id)

    # ── Deactivate full corridor ───────────────────────────────────────────────

    async def deactivate_full_corridor(self, event_id: str) -> None:
        """Called when the ambulance reaches its destination.

        Restores every intersection still on the route and marks the event
        as completed.
        """
        event = await self._load_event(event_id)
        if event is None:
            logger.warning("deactivate_full_corridor: event %s not found", event_id)
            return

        event.status = "completed"

        # Restore all intersections
        for intersection_id in event.route:
            await self.deactivate_intersection(intersection_id)

        # Remove from store
        await self._delete_event(event_id)

        # Publish clear notification
        self._mqtt.publish("traffic/emergency/clear", event_id)
        logger.info("Green corridor completed: event_id=%s", event_id)

    # ── Query ──────────────────────────────────────────────────────────────────

    async def get_active_corridors(self) -> List[EmergencyEvent]:
        """Return all currently active emergency events."""
        if self._redis is not None:
            try:
                keys = await self._redis.keys("corridor:active:*")
                events = []
                for key in keys:
                    raw = await self._redis.get(key)
                    if raw:
                        events.append(EmergencyEvent.from_dict(json.loads(raw)))
                return events
            except Exception as exc:
                logger.error("Redis get_active_corridors failed: %s", exc)

        # Fallback to local store
        return [e for e in self._local_store.values() if e.status == "active"]

    # ── Cancel ────────────────────────────────────────────────────────────────

    async def cancel_corridor(self, event_id: str) -> None:
        """Cancel an active corridor without marking it completed."""
        event = await self._load_event(event_id)
        if event is None:
            logger.warning("cancel_corridor: event %s not found", event_id)
            return

        event.status = "cancelled"
        for intersection_id in event.route:
            await self.deactivate_intersection(intersection_id)

        await self._delete_event(event_id)
        self._mqtt.publish("traffic/emergency/clear", event_id)
        logger.info("Green corridor cancelled: event_id=%s", event_id)

    # ── Internal persistence helpers ───────────────────────────────────────────

    async def _store_event(self, event: EmergencyEvent) -> None:
        key = f"corridor:active:{event.event_id}"
        serialised = event.to_json()
        if self._redis is not None:
            try:
                await self._redis.set(key, serialised, ex=self._green_ttl)
                return
            except Exception as exc:
                logger.error("Redis _store_event failed: %s – falling back to local", exc)
        self._local_store[event.event_id] = event

    async def _load_event(self, event_id: str) -> Optional[EmergencyEvent]:
        key = f"corridor:active:{event_id}"
        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw:
                    return EmergencyEvent.from_dict(json.loads(raw))
            except Exception as exc:
                logger.error("Redis _load_event failed: %s", exc)
        return self._local_store.get(event_id)

    async def _delete_event(self, event_id: str) -> None:
        key = f"corridor:active:{event_id}"
        if self._redis is not None:
            try:
                await self._redis.delete(key)
            except Exception as exc:
                logger.error("Redis _delete_event failed: %s", exc)
        self._local_store.pop(event_id, None)


# ── Factory / test helper ──────────────────────────────────────────────────────

def simulate_ambulance_route(
    intersection_ids: List[str],
    vehicle_id: str = "AMB-001",
    vehicle_type: str = "ambulance",
    travel_minutes: int = ESTIMATED_TRAVEL_MINUTES,
) -> EmergencyEvent:
    """Create a synthetic EmergencyEvent for development and testing.

    Parameters
    ----------
    intersection_ids : List[str]
        Ordered list of intersection IDs the ambulance will pass through.
    vehicle_id : str
        Plate / call-sign of the emergency vehicle (default ``"AMB-001"``).
    vehicle_type : str
        One of ``"ambulance"``, ``"fire_truck"``, ``"police"``.
    travel_minutes : int
        Estimated total travel time; sets ``estimated_arrival``.

    Returns
    -------
    EmergencyEvent  (status = "active", current_intersection = first stop)

    Example
    -------
    >>> event = simulate_ambulance_route(["INT-01", "INT-02", "INT-03"])
    >>> print(event.event_id)
    'a3f1d2c4-...'
    """
    now = datetime.utcnow()
    return EmergencyEvent(
        event_id=str(uuid.uuid4()),
        vehicle_id=vehicle_id,
        vehicle_type=vehicle_type,
        route=list(intersection_ids),
        dispatch_time=now,
        estimated_arrival=now + timedelta(minutes=travel_minutes),
        status="active",
        current_intersection=intersection_ids[0] if intersection_ids else None,
    )
