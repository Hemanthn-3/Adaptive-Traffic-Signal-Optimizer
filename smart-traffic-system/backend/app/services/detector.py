"""
backend/app/services/detector.py
─────────────────────────────────
YOLOv8-based vehicle detection service using a fine-tuned top-view model.

Model
─────
  PRIMARY  : ml/models/best.pt  (fine-tuned, single class: 'vehicle')
  FALLBACK : yolov8n.pt         (COCO, used only if best.pt not found)

Lane definition
───────────────
  Lane A  →  left  half  (center_x < frame_width / 2)  → BLUE boxes
  Lane B  →  right half  (center_x >= frame_width / 2) → GREEN boxes

Density thresholds (percentage-based, MAX_CAPACITY=20)
──────────────────────────────────────────────────────
   0–25%  → LOW
  26–50%  → MEDIUM
  51–75%  → HIGH
  76–100% → VERY HIGH
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Generator, List, Optional

import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# Fine-tuned model uses a single class: 'vehicle' (class 0)
# COCO multi-class IDs are used only when falling back to yolov8n.pt
COCO_VEHICLE_CLASS_IDS: set[int] = {1, 2, 3, 5, 7}

# Density: percentage-based using MAX_CAPACITY buckets
MAX_CAPACITY = int(os.getenv("MAX_LANE_CAPACITY", "20"))
CONF_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.3"))

# Density level thresholds (percentage)
DENSITY_LEVELS = [
    (25,  "LOW",       (0, 200, 0)),      # green  (BGR)
    (50,  "MEDIUM",    (0, 200, 255)),    # yellow
    (75,  "HIGH",      (0, 128, 255)),    # orange
    (100, "VERY HIGH", (0, 0, 255)),      # red
]

# Lane box colours (BGR)
COLOR_LANE_A  = (255, 80,  0)    # Blue tint
COLOR_LANE_B  = (0,  200, 80)    # Green tint
COLOR_DIVIDER = (255, 255, 255)  # White

FONT           = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE     = 0.55
FONT_THICKNESS = 1
BOX_THICKNESS  = 2


# ── Standalone helpers (module-level) ──────────────────────────────────────────

def calculate_density_pct(vehicle_count: int, max_capacity: int = MAX_CAPACITY) -> float:
    """Return density percentage (0–100) based on vehicle count vs MAX_CAPACITY."""
    return min(100.0, (vehicle_count / max(max_capacity, 1)) * 100.0)


def density_label(pct: float) -> tuple[str, tuple]:
    """Return (level_name, bgr_color) for a density percentage."""
    for threshold, name, color in DENSITY_LEVELS:
        if pct <= threshold:
            return name, color
    return "VERY HIGH", (0, 0, 255)


def draw_lane_divider(frame: np.ndarray) -> np.ndarray:
    """Draw a vertical white dashed line at the horizontal centre of *frame*.

    Modifies the frame **in-place** and returns it for convenience.
    """
    h, w = frame.shape[:2]
    mid_x = w // 2
    dash_len, gap_len = 20, 10
    y = 0
    while y < h:
        cv2.line(frame, (mid_x, y), (mid_x, min(y + dash_len, h)), COLOR_DIVIDER, 2)
        y += dash_len + gap_len
    return frame


def draw_info_panels(frame: np.ndarray, lane_a_count: int, lane_b_count: int,
                     frame_number: int, fps: float, model_name: str = "best.pt") -> np.ndarray:
    """Draw Lane A / Lane B overlay panels and bottom status bar.

    Parameters
    ----------
    frame        : annotated BGR frame (modified in-place)
    lane_a_count : number of vehicles detected in Lane A
    lane_b_count : number of vehicles detected in Lane B
    frame_number : current frame index
    fps          : frames per second
    model_name   : short model filename shown in the bottom bar
    """
    h, w = frame.shape[:2]
    mid_x = w // 2
    panel_h = 80
    bg = (30, 30, 30)          # Dark panel background
    text_color = (255, 255, 255)

    a_pct = calculate_density_pct(lane_a_count)
    b_pct = calculate_density_pct(lane_b_count)
    a_label, a_color = density_label(a_pct)
    b_label, b_color = density_label(b_pct)

    # ── Top-left panel (Lane A) ─────────────────────────────────────────────────
    cv2.rectangle(frame, (5, 5), (mid_x - 5, panel_h), bg, -1)
    cv2.rectangle(frame, (5, 5), (mid_x - 5, panel_h), COLOR_LANE_A, 1)
    cv2.putText(frame, "LANE A", (12, 24), FONT, 0.7, COLOR_LANE_A, 2)
    cv2.putText(frame, f"Vehicles: {lane_a_count}", (12, 46), FONT, 0.5, text_color, 1)
    cv2.putText(frame, f"Density: {a_label} ({a_pct:.0f}%)", (12, 66), FONT, 0.5, a_color, 1)

    # ── Top-right panel (Lane B) ────────────────────────────────────────────────
    cv2.rectangle(frame, (mid_x + 5, 5), (w - 5, panel_h), bg, -1)
    cv2.rectangle(frame, (mid_x + 5, 5), (w - 5, panel_h), COLOR_LANE_B, 1)
    cv2.putText(frame, "LANE B", (mid_x + 12, 24), FONT, 0.7, COLOR_LANE_B, 2)
    cv2.putText(frame, f"Vehicles: {lane_b_count}", (mid_x + 12, 46), FONT, 0.5, text_color, 1)
    cv2.putText(frame, f"Density: {b_label} ({b_pct:.0f}%)", (mid_x + 12, 66), FONT, 0.5, b_color, 1)

    # ── Bottom bar ──────────────────────────────────────────────────────────────
    cv2.rectangle(frame, (0, h - 28), (w, h), bg, -1)
    cv2.rectangle(frame, (0, h - 28), (w, h), COLOR_DIVIDER, 1)
    bottom_text = f"Model: {model_name} | Frame: {frame_number:04d} | FPS: {fps:.1f}"
    cv2.putText(frame, bottom_text, (10, h - 8), FONT, 0.5, text_color, 1)

    return frame


def get_video_metadata(video_path: str) -> Dict[str, float | int]:
    """Return basic metadata for a video file without reading all frames.

    Returns
    -------
    dict with keys: fps, total_frames, width, height
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    meta = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    cap.release()
    return meta


def detect_emergency_color(frame_region: np.ndarray) -> tuple[bool, float]:
    """Detect emergency vehicle using color analysis (red/yellow pixels in HSV).
    
    Parameters
    ----------
    frame_region : np.ndarray
        Bounding box region from the frame (BGR format)
    
    Returns
    -------
    tuple[bool, float]
        (is_emergency, confidence) where confidence is % of red/yellow pixels
    """
    if frame_region.size == 0:
        return False, 0.0
    
    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame_region, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Red range: H=0-10 or H=170-180, S>100, V>100
    red_mask = ((((h >= 0) & (h <= 10)) | ((h >= 170) & (h <= 180))) & 
                (s > 100) & (v > 100))
    
    # Yellow range: H=20-35, S>100, V>100
    yellow_mask = ((h >= 20) & (h <= 35) & (s > 100) & (v > 100))
    
    # Combine red and yellow masks
    emergency_mask = red_mask | yellow_mask
    
    # Calculate percentage of emergency-colored pixels
    total_pixels = emergency_mask.size
    emergency_pixels = np.count_nonzero(emergency_mask)
    confidence = (emergency_pixels / total_pixels) * 100 if total_pixels > 0 else 0.0
    
    # Threshold: > 15% of pixels should be emergency colors
    is_emergency = confidence > 15
    
    return is_emergency, confidence


def detect_emergency_by_size(box_width: int, frame_width: int, vehicle_type: str) -> bool:
    """Detect emergency vehicle based on size heuristics.
    
    Parameters
    ----------
    box_width : int
        Bounding box width in pixels
    frame_width : int
        Frame width in pixels
    vehicle_type : str
        Vehicle type classification (car, truck, bus, etc.)
    
    Returns
    -------
    bool
        True if vehicle size matches emergency vehicle heuristics
    """
    # Ambulances are typically truck/bus-sized
    if vehicle_type not in ("truck", "bus"):
        return False
    
    # Threshold: width > 15% of frame width
    width_ratio = box_width / frame_width if frame_width > 0 else 0.0
    return width_ratio > 0.15


def _compute_iou(bbox1: list, bbox2: list) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes.
    
    Parameters
    ----------
    bbox1 : list
        [x1, y1, x2, y2]
    bbox2 : list
        [x1, y1, x2, y2]
    
    Returns
    -------
    float
        IoU value between 0 and 1
    """
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2
    
    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)
    
    if inter_xmax < inter_xmin or inter_ymax < inter_ymin:
        return 0.0
    
    inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
    bbox1_area = (x1_max - x1_min) * (y1_max - y1_min)
    bbox2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = bbox1_area + bbox2_area - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area


# ── Main class ─────────────────────────────────────────────────────────────────

class VehicleDetector:
    """YOLOv8 vehicle detector with two-lane (left / right) split logic.

    Automatically picks the fine-tuned ``best.pt`` model when available,
    falling back to ``yolov8n.pt`` otherwise.

    Parameters
    ----------
    model_path : str | None
        Explicit path to a YOLOv8 weights file.  When *None* (default) the
        constructor resolves the path automatically:
        ``ml/models/best.pt`` → ``yolov8n.pt``.
    conf_threshold : float
        Minimum confidence score to accept a detection.
    """

    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = CONF_THRESHOLD):
        # ── Resolve model path ────────────────────────────────────────────────
        if model_path is None:
            env_path = os.getenv("YOLO_MODEL_PATH", "ml/models/best.pt")
            if Path(env_path).exists():
                model_path = env_path
                logger.info("[VehicleDetector] Using fine-tuned model: %s", model_path)
            else:
                model_path = "yolov8n.pt"
                logger.warning(
                    "[VehicleDetector] best.pt not found at '%s'. "
                    "Falling back to yolov8n.pt (COCO classes).", env_path
                )

        self.model_path = model_path
        self.conf_threshold = conf_threshold

        logger.info("Loading YOLO model from %s …", model_path)
        self.model = YOLO(model_path)
        logger.info("Model loaded — classes: %s", list(self.model.names.values())[:10])

        # Detect whether this is the fine-tuned single-class model
        self._is_finetuned = (
            len(self.model.names) == 1 or
            list(self.model.names.values()) == ["vehicle"]
        )
        logger.info("Fine-tuned mode: %s", self._is_finetuned)

        # ── DeepSORT tracking initialization (lazy-loaded) ────────────────────
        self.tracker = None
        self.vehicle_history = {}
        self.frame_count = 0
        self.fps = 30.0
        self._tracker_initialized = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_emergency_vehicle(self, frame: np.ndarray, box_coords: tuple, 
                            vehicle_type: str) -> tuple[bool, float]:
        """Detect if a vehicle is an emergency vehicle using color and size heuristics.
        
        Parameters
        ----------
        frame : np.ndarray
            The full frame (BGR format)
        box_coords : tuple
            (x1, y1, x2, y2) bounding box coordinates
        vehicle_type : str
            The detected vehicle type (car, truck, bus, etc.)
        
        Returns
        -------
        tuple[bool, float]
            (is_emergency, confidence) where confidence is 0.0-100.0
        """
        x1, y1, x2, y2 = [int(c) for c in box_coords]
        
        # Clamp to frame bounds
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # Extract vehicle region
        vehicle_region = frame[y1:y2, x1:x2]
        
        # METHOD 1: Color-based detection
        color_emergency, color_confidence = detect_emergency_color(vehicle_region)
        
        # METHOD 2: Size-based detection
        box_width = x2 - x1
        size_emergency = detect_emergency_by_size(box_width, w, vehicle_type)
        
        # Combine both methods: emergency if BOTH color check passes AND size heuristic passes
        is_emergency = color_emergency and size_emergency
        
        # Confidence: use color confidence if both methods agree
        confidence = color_confidence if is_emergency else 0.0
        
        return is_emergency, confidence

    def process_frame(self, frame: np.ndarray, frame_number: int = -1,
                      fps: float = 30.0) -> Dict:
        """Run detection on a single BGR frame.

        Supports both the fine-tuned single-class model (best.pt) and the
        COCO multi-class fallback (yolov8n.pt). Lane assignment is purely
        left-vs-right (center_x < frame_width / 2).

        Returns
        -------
        dict
            Keys: frame, timestamp, lane_a, lane_b,
            emergency_vehicle_detected, emergency_vehicle_type,
            emergency_confidence, tracked_vehicles,
            avg_wait_time_lane_a, avg_wait_time_lane_b,
            unique_vehicle_count, annotated_frame
        """
        h, w = frame.shape[:2]
        mid_x = w // 2
        self.fps = fps

        results = self.model(frame, verbose=False, conf=self.conf_threshold)[0]

        # ── Collect raw detections ─────────────────────────────────────────────
        raw_detections: List[tuple] = []   # (x1,y1,x2,y2, conf, center_x)

        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < self.conf_threshold:
                continue

            cls_id = int(box.cls[0])

            if self._is_finetuned:
                # Fine-tuned model: accept class 0 ('vehicle') only
                if cls_id != 0:
                    continue
            else:
                # COCO fallback: accept standard vehicle class IDs
                if cls_id not in COCO_VEHICLE_CLASS_IDS:
                    continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) // 2
            raw_detections.append((x1, y1, x2, y2, conf, cx))

        # ── Count vehicles per lane ────────────────────────────────────────────
        lane_a_count = sum(1 for *_, cx in raw_detections if cx < mid_x)
        lane_b_count = sum(1 for *_, cx in raw_detections if cx >= mid_x)

        # Build legacy lane_a/lane_b dicts for downstream consumers
        lane_a_data = {"car": 0, "bicycle": 0, "motorcycle": 0, "bus": 0,
                       "truck": 0, "vehicle": lane_a_count,
                       "total": lane_a_count, "positions": []}
        lane_b_data = {"car": 0, "bicycle": 0, "motorcycle": 0, "bus": 0,
                       "truck": 0, "vehicle": lane_b_count,
                       "total": lane_b_count, "positions": []}

        # ── Prepare DeepSORT input ─────────────────────────────────────────────
        deepsort_dets = [[x1, y1, x2, y2, conf] for x1, y1, x2, y2, conf, _ in raw_detections]

        # ── Lazy-initialize tracker ────────────────────────────────────────────
        if not self._tracker_initialized:
            try:
                self.tracker = DeepSort(max_age=30, n_init=3)
                self._tracker_initialized = True
                logger.info("DeepSORT tracker initialized successfully")
            except Exception as exc:
                logger.warning("DeepSORT init failed: %s. Tracking disabled.", exc)
                self._tracker_initialized = True
                self.tracker = None

        tracks = self.tracker.update_tracks(deepsort_dets, frame=frame) if self.tracker else []

        annotated = frame.copy()
        emergency_detected = False
        emergency_type = None
        emergency_confidence = 0.0
        tracked_vehicles: List[Dict] = []

        # ── Draw raw detections (colored by lane) ──────────────────────────────
        for x1, y1, x2, y2, conf, cx in raw_detections:
            color = COLOR_LANE_A if cx < mid_x else COLOR_LANE_B
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, BOX_THICKNESS)

        # ── Process confirmed tracks ───────────────────────────────────────────
        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            x1, y1, x2, y2 = map(int, track.to_tlbr())
            bw, bh = x2 - x1, y2 - y1
            center_x = (x1 + x2) // 2
            lane = "A" if center_x < mid_x else "B"

            # Match conf from closest raw detection
            conf = 0.0
            for rx1, ry1, rx2, ry2, rconf, _ in raw_detections:
                iou = _compute_iou([x1, y1, x2, y2], [rx1, ry1, rx2, ry2])
                if iou > 0.5:
                    conf = rconf
                    break

            # ── Update vehicle history ─────────────────────────────────────────
            if track_id not in self.vehicle_history:
                self.vehicle_history[track_id] = {
                    "class": "vehicle",
                    "lane": lane,
                    "first_frame": frame_number,
                    "last_frame": frame_number,
                    "positions": [],
                }
            entry = self.vehicle_history[track_id]
            entry["last_frame"] = frame_number
            entry["positions"].append((center_x, y2))

            frames_in_view = frame_number - entry["first_frame"] + 1
            wait_time = frames_in_view / fps if fps > 0 else 0.0

            # Speed estimate
            speed_kmh = 0.0
            if len(entry["positions"]) >= 2:
                px, py = entry["positions"][-2]
                cx2, cy2 = entry["positions"][-1]
                disp = ((cx2 - px) ** 2 + (cy2 - py) ** 2) ** 0.5
                speed_kmh = (disp / 10.0) / (1.0 / fps if fps > 0 else 0.0333) * 3.6

            # ── Draw track label ───────────────────────────────────────────────
            label = f"#{track_id}"
            text_sz = cv2.getTextSize(label, FONT, FONT_SCALE, FONT_THICKNESS)[0]
            tx, ty = x1, max(y1 - 6, 0)
            track_color = COLOR_LANE_A if lane == "A" else COLOR_LANE_B
            cv2.rectangle(annotated, (tx, ty - text_sz[1] - 4),
                          (tx + text_sz[0], ty + 2), track_color, -1)
            cv2.putText(annotated, label, (tx, ty), FONT, FONT_SCALE,
                        (0, 0, 0), FONT_THICKNESS)

            tracked_vehicles.append({
                "track_id": track_id,
                "class": "vehicle",
                "lane": lane,
                "wait_time_seconds": wait_time,
                "speed_kmh_estimate": speed_kmh,
                "bounding_box": [x1, y1, bw, bh],
                "confidence": conf,
            })

        # ── Average wait times ─────────────────────────────────────────────────
        la_v = [v for v in tracked_vehicles if v["lane"] == "A"]
        lb_v = [v for v in tracked_vehicles if v["lane"] == "B"]
        avg_wait_a = float(np.mean([v["wait_time_seconds"] for v in la_v])) if la_v else 0.0
        avg_wait_b = float(np.mean([v["wait_time_seconds"] for v in lb_v])) if lb_v else 0.0

        # ── Overlay ────────────────────────────────────────────────────────────
        draw_lane_divider(annotated)
        model_short = Path(self.model_path).name
        draw_info_panels(annotated, lane_a_count, lane_b_count,
                         frame_number, fps, model_short)

        return {
            "frame": frame_number,
            "timestamp": -1.0,
            "lane_a": lane_a_data,
            "lane_b": lane_b_data,
            "emergency_vehicle_detected": emergency_detected,
            "emergency_vehicle_type": emergency_type,
            "emergency_confidence": emergency_confidence,
            "tracked_vehicles": tracked_vehicles,
            "avg_wait_time_lane_a": avg_wait_a,
            "avg_wait_time_lane_b": avg_wait_b,
            "unique_vehicle_count": len(self.vehicle_history),
            "annotated_frame": annotated,
        }

    def process_video(self, video_path: str) -> Generator[Dict, None, None]:
        """Yield one detection-result dict per frame of *video_path*.

        The generator reads the video with OpenCV and passes every frame
        through :meth:`process_frame`, enriching each result with the
        correct ``frame`` and ``timestamp``.

        Parameters
        ----------
        video_path : str
            Absolute or relative path to the input ``.mp4`` / ``.avi`` file.

        Yields
        ------
        dict
            Per-frame detection result with vehicle type classification.

        Raises
        ------
        FileNotFoundError
            If *video_path* cannot be opened by OpenCV.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_number = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number += 1
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0  # Convert to seconds

                result = self.process_frame(frame, frame_number=frame_number, fps=fps)
                result["frame"] = frame_number
                result["timestamp"] = timestamp

                yield result
        finally:
            cap.release()
            logger.info("Released video capture after %d frames.", frame_number)
