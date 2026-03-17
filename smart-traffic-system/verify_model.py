#!/usr/bin/env python3
"""
verify_model.py — Quick sanity check for the fine-tuned YOLOv8 best.pt model.

Usage:
    python verify_model.py
    python verify_model.py ml/test_videos/sample_video.mp4
"""

from __future__ import annotations

import sys
from pathlib import Path

MODEL_PATH = "ml/models/best.pt"
FALLBACK   = "yolov8n.pt"
CONF       = 0.3


def main():
    # ── 1. Resolve video source ────────────────────────────────────────────────
    video_arg = sys.argv[1] if len(sys.argv) > 1 else "ml/test_videos/sample_video.mp4"

    # ── 2. Load model ─────────────────────────────────────────────────────────
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run:  pip install ultralytics")
        sys.exit(1)

    if Path(MODEL_PATH).exists():
        model = YOLO(MODEL_PATH)
        print(f"[INFO]  Model   : {MODEL_PATH}  (fine-tuned)")
    else:
        model = YOLO(FALLBACK)
        print(f"[WARN]  best.pt not found at '{MODEL_PATH}' — using fallback: {FALLBACK}")

    print(f"[INFO]  Classes : {model.names}")

    # ── 3. Read one frame ─────────────────────────────────────────────────────
    try:
        import cv2
    except ImportError:
        print("[ERROR] opencv-python not installed. Run:  pip install opencv-python")
        sys.exit(1)

    cap = cv2.VideoCapture(video_arg)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"[WARN]  Could not read a frame from '{video_arg}'.")
        print("[INFO]  Running inference on a blank 640×640 image instead …")
        import numpy as np
        frame = np.zeros((640, 640, 3), dtype="uint8")

    # ── 4. Run inference ──────────────────────────────────────────────────────
    results = model(frame, verbose=False, conf=CONF)
    boxes   = results[0].boxes

    print(f"\n[INFO]  Model loaded        : OK")
    print(f"[INFO]  Frame detections    : {len(boxes)} vehicles")

    if len(boxes):
        confs = [round(float(b.conf), 2) for b in boxes]
        print(f"[INFO]  Confidence scores  : {confs}")

        # Lane split
        h, w = frame.shape[:2]
        mid_x = w // 2
        lane_a = sum(1 for b in boxes if float(b.xywh[0][0]) < mid_x)
        lane_b = len(boxes) - lane_a
        print(f"[INFO]  Lane A vehicles    : {lane_a}")
        print(f"[INFO]  Lane B vehicles    : {lane_b}")
    else:
        print("[HINT]  No detections found. Try lowering CONF to 0.2 in this script.")

    print("\n[OK] Verification complete.\n")


if __name__ == "__main__":
    main()
