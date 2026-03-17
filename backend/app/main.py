"""
backend/app/main.py
────────────────────
FastAPI application entry point.

Services wired up
─────────────────
  • Redis (async)                   – app.state.redis
  • MQTT (paho, background thread)  – app.state.mqtt
  • ConnectionManager (WebSocket)   – app.state.ws_manager
  • DensityCalculator               – app.state.density_calc
  • SignalOptimizer                 – app.state.optimizer
  • GreenCorridorService            – app.state.corridor

WebSocket endpoint (/ws)
────────────────────────
  Pushes a "ping" heartbeat every second and relays any events
  broadcast from the REST routers / MQTT callbacks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.mqtt_client import MQTTClient
from app.core.redis_client import init_redis, close_redis, get_redis
from app.core.websocket_manager import ws_manager
from app.routers import traffic, signals, emergency
from app.services.density import DensityCalculator
from app.services.optimizer import SignalOptimizer
from app.services.corridor import GreenCorridorService
from app.services.simulator import simulator as traffic_simulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info("Starting Smart Traffic Management System …")

    try:
        await init_redis()
        redis_client = await get_redis()
    except Exception as exc:
        logger.warning("Redis unavailable at startup: %s", exc)
        redis_client = None

    try:
        mqtt = MQTTClient()
        mqtt.connect()
    except Exception as exc:
        logger.warning("MQTT unavailable at startup: %s", exc)
        mqtt = None

    density_calc = DensityCalculator(max_capacity=settings.MAX_LANE_CAPACITY)
    optimizer = SignalOptimizer(
        base_cycle=float(settings.MIN_GREEN_DURATION + settings.MAX_GREEN_DURATION),
        min_green=float(settings.MIN_GREEN_DURATION),
        max_green=float(settings.MAX_GREEN_DURATION),
    )

    try:
        corridor_svc = GreenCorridorService(
            signal_optimizer=optimizer,
            mqtt_client=mqtt,
            redis_client=redis_client,
            green_ttl=settings.EMERGENCY_GREEN_DURATION,
        )
    except Exception as exc:
        logger.warning("GreenCorridorService init failed: %s", exc)
        corridor_svc = None

    app.state.redis = redis_client
    app.state.mqtt = mqtt
    app.state.ws_manager = ws_manager
    app.state.density_calc = density_calc
    app.state.optimizer = optimizer
    app.state.corridor = corridor_svc

    # Start the traffic simulator so the dashboard shows live data without a video
    asyncio.create_task(traffic_simulator.run())

    logger.info("All services initialised. Simulator running.")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("Shutting down …")
    traffic_simulator.stop()
    if mqtt:
        try:
            mqtt.disconnect()
        except Exception:
            pass
    try:
        await close_redis()
    except Exception:
        pass


# ── App factory ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Traffic Management System",
    description="AI-powered adaptive traffic signal control with emergency green corridor.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(traffic.router,   prefix="/api/traffic",    tags=["Traffic"])
app.include_router(signals.router,   prefix="/api/signals",    tags=["Signals"])
app.include_router(emergency.router, prefix="/api/emergency",  tags=["Emergency"])


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "smart-traffic-backend",
        "ws_clients": ws_manager.connection_count,
    }


# ── WebSocket endpoint ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Clients connect here to receive real-time updates.

    The endpoint:
      1. Sends an "init" message with current system state.
      2. Broadcasts a heartbeat ping every second while the connection
         is open; actual density/signal/emergency updates are pushed via
         ws_manager.broadcast() from the REST routers.
    """
    await ws_manager.connect(websocket)
    try:
        # ── Initial state dump ────────────────────────────────────────────────
        from app.routers.traffic import current_density, current_signal
        await ws_manager.send_personal({
            "type": "init",
            "density": current_density,
            "signal": current_signal,
        }, websocket)

        # ── Heartbeat loop ────────────────────────────────────────────────────
        while True:
            try:
                await asyncio.sleep(1)
                await ws_manager.send_personal({
                    "type": "ping",
                    "data": {"ws_clients": ws_manager.connection_count},
                }, websocket)
            except (WebSocketDisconnect, Exception):
                break  # Exit loop on disconnect or send failure
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WS endpoint error: %s", exc)
    finally:
        ws_manager.disconnect(websocket)
