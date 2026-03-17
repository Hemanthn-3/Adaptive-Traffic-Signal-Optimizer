"""
backend/app/services/simulator.py
───────────────────────────────────
Traffic data simulator for demo purposes.
Runs automatically when no video is being processed, keeping the
dashboard live with realistic time-based traffic patterns.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime

from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

INTERSECTIONS = [
    "INT-01", "INT-02", "INT-03", "INT-04",
    "INT-05", "INT-06", "INT-07", "INT-08"
]


def get_level(density: float) -> str:
    if density <= 30:
        return "low"
    if density <= 60:
        return "medium"
    if density <= 80:
        return "high"
    return "critical"


class TrafficSimulator:
    """Simulates realistic traffic data for all 8 Bengaluru intersections."""

    def __init__(self):
        self.running = False
        self.intersections = INTERSECTIONS
        self._paused_sources: set[str] = set()

    async def run(self):
        self.running = True
        logger.info("Traffic simulator started – dashboard will show live data")

        while self.running:
            if self._paused_sources:
                await asyncio.sleep(0.25)
                continue

            hour = datetime.now().hour

            # Time-based traffic multiplier
            if 8 <= hour <= 10 or 17 <= hour <= 19:
                multiplier = 0.8   # peak hours
            elif 12 <= hour <= 14:
                multiplier = 0.5   # lunch
            elif hour >= 22 or hour <= 6:
                multiplier = 0.1   # night
            else:
                multiplier = 0.3   # normal

            for intersection_id in self.intersections:
                base = random.randint(2, 15)

                # Lane A
                lane_a_cars   = int(base * multiplier * random.uniform(0.8, 1.2))
                lane_a_bikes  = int(base * 0.6 * multiplier * random.uniform(0.5, 1.5))
                lane_a_buses  = random.randint(0, max(0, int(2 * multiplier)))
                lane_a_trucks = random.randint(0, max(0, int(1 * multiplier)))

                # Lane B
                lane_b_cars   = int(base * 0.7 * multiplier * random.uniform(0.8, 1.2))
                lane_b_bikes  = int(base * 0.5 * multiplier * random.uniform(0.5, 1.5))
                lane_b_buses  = random.randint(0, max(0, int(2 * multiplier)))
                lane_b_trucks = random.randint(0, max(0, int(1 * multiplier)))

                # Weighted counts
                a_weighted = (lane_a_cars * 1.0 + lane_a_bikes * 0.5 +
                              lane_a_buses * 2.5 + lane_a_trucks * 2.5)
                b_weighted = (lane_b_cars * 1.0 + lane_b_bikes * 0.5 +
                              lane_b_buses * 2.5 + lane_b_trucks * 2.5)

                a_density = min(100.0, (a_weighted / 20) * 100)
                b_density = min(100.0, (b_weighted / 20) * 100)

                a_total = lane_a_cars + lane_a_bikes + lane_a_buses + lane_a_trucks
                b_total = lane_b_cars + lane_b_bikes + lane_b_buses + lane_b_trucks

                # Time to clear: (cars×2 + bikes×1 + buses×2.5 + trucks×2.5) / 2
                a_ttc = max(10, min(90,
                    (lane_a_cars * 2 + lane_a_bikes * 1 +
                     lane_a_buses * 2.5 + lane_a_trucks * 2.5) / 2
                ))
                b_ttc = max(10, min(90,
                    (lane_b_cars * 2 + lane_b_bikes * 1 +
                     lane_b_buses * 2.5 + lane_b_trucks * 2.5) / 2
                ))

                payload = {
                    "type": "density_update",
                    "intersection_id": intersection_id,
                    "data": {
                        # Lane A
                        "lane_a_count":       a_total,
                        "lane_a_cars":        lane_a_cars,
                        "lane_a_bikes":       lane_a_bikes,
                        "lane_a_buses":       lane_a_buses,
                        "lane_a_trucks":      lane_a_trucks,
                        "lane_a_density":     round(a_density, 1),
                        "lane_a_level":       get_level(a_density),
                        "lane_a_weighted":    round(a_weighted, 2),
                        "lane_a_queue_meters": a_total * 6,
                        "lane_a_time_to_clear": round(a_ttc, 1),
                        # Lane B
                        "lane_b_count":       b_total,
                        "lane_b_cars":        lane_b_cars,
                        "lane_b_bikes":       lane_b_bikes,
                        "lane_b_buses":       lane_b_buses,
                        "lane_b_trucks":      lane_b_trucks,
                        "lane_b_density":     round(b_density, 1),
                        "lane_b_level":       get_level(b_density),
                        "lane_b_weighted":    round(b_weighted, 2),
                        "lane_b_queue_meters": b_total * 6,
                        "lane_b_time_to_clear": round(b_ttc, 1),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }

                await ws_manager.broadcast(payload)
                await asyncio.sleep(0.1)   # stagger intersections slightly

            await asyncio.sleep(2)   # full update every 2 seconds

    def stop(self):
        self.running = False

    def pause(self, source: str = "manual"):
        """Temporarily suspend simulator broadcasts for a named source."""
        self._paused_sources.add(source)

    def resume(self, source: str = "manual"):
        """Resume simulator broadcasts once the named source is cleared."""
        self._paused_sources.discard(source)


# Singleton
simulator = TrafficSimulator()
