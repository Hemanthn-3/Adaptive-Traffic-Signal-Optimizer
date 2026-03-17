import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS connected | total={len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WS disconnected | total={len(self.active_connections)}")

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.active_connections:
                self.active_connections.remove(ws)

    async def send_personal(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


ws_manager = ConnectionManager()
