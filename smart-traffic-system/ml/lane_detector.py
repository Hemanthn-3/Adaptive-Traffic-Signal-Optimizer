"""lane_detector.py – Define and manage lane zones within a video frame.

Provides LaneDetector which holds bounding-box definitions for each lane
and offers utility methods to determine which lane a point falls in.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Lane:
    id: str
    label: str
    direction: str
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    max_capacity: int = 20
    color_bgr: Tuple[int, int, int] = (0, 200, 0)

    def contains_point(self, x: int, y: int) -> bool:
        x1, y1, x2, y2 = self.bbox
        return x1 <= x <= x2 and y1 <= y <= y2


class LaneDetector:
    """Manages lane zones for a given frame resolution."""

    def __init__(self, frame_width: int, frame_height: int):
        self.fw = frame_width
        self.fh = frame_height
        self.lanes: Dict[str, Lane] = {}
        self._init_default_lanes()

    def _init_default_lanes(self):
        """
        Default layout: split frame into 4 equal vertical strips mapped to
        North, South, East, West directions.
        Strip sizes: left quarter, left-centre, right-centre, right quarter.
        """
        w, h = self.fw, self.fh
        quarter = w // 4

        definitions = [
            ("A", "North-A", "N", (0,           0, quarter,     h)),
            ("B", "South-B", "S", (quarter,      0, quarter * 2, h)),
            ("C", "East-C",  "E", (quarter * 2,  0, quarter * 3, h)),
            ("D", "West-D",  "W", (quarter * 3,  0, w,            h)),
        ]
        for lid, label, direction, bbox in definitions:
            self.lanes[lid] = Lane(id=lid, label=label, direction=direction, bbox=bbox)

    def add_custom_lane(self, lane: Lane) -> None:
        self.lanes[lane.id] = lane

    def find_lane(self, x: int, y: int) -> Optional[Lane]:
        """Return the first lane that contains the given point."""
        for lane in self.lanes.values():
            if lane.contains_point(x, y):
                return lane
        return None

    def assign_detections_to_lanes(
        self, detections: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Parameters
        ----------
        detections : list of dicts with 'center': [cx, cy]

        Returns
        -------
        dict mapping lane_id -> list of detections in that lane
        """
        assignment: Dict[str, List] = {lid: [] for lid in self.lanes}
        for det in detections:
            cx, cy = det.get("center", [0, 0])
            lane = self.find_lane(cx, cy)
            if lane:
                assignment[lane.id].append(det)
        return assignment

    def summary(self, assignment: Dict[str, List]) -> List[Dict]:
        """Return a list of per-lane count summaries."""
        result = []
        for lid, detections in assignment.items():
            lane = self.lanes[lid]
            count = len(detections)
            score = min(count / lane.max_capacity, 1.0)
            result.append({
                "lane_id": lid,
                "label": lane.label,
                "direction": lane.direction,
                "vehicle_count": count,
                "density_score": round(score, 4),
                "max_capacity": lane.max_capacity,
            })
        return result
