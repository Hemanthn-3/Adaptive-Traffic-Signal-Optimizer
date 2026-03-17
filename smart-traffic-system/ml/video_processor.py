"""
ml/video_processor.py
──────────────────────
Standalone CLI script that uses VehicleDetector to process a video file,
print lane-level summaries every 30 frames, and save an annotated output
video to the same folder as the input.

Usage
─────
    python ml/video_processor.py --video ml/test_videos/sample.mp4
    python ml/video_processor.py --video sample.mp4 --model yolov8s.pt --conf 0.4
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict

import cv2
import numpy as np

# ── Path bootstrap so the script works both standalone and from the repo root
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root

from backend.app.services.detector import VehicleDetector, get_video_metadata

# ── Summary interval ───────────────────────────────────────────────────────────
SUMMARY_EVERY = 30


def build_output_path(input_path: str) -> str:
    """Return '<stem>_annotated<suffix>' alongside the input file."""
    p = Path(input_path)
    return str(p.parent / f"{p.stem}_annotated{p.suffix}")


def print_summary(frame_number: int, lane_a: Dict, lane_b: Dict, timestamp_s: float) -> None:
    """Print detailed vehicle classification summary per lane."""
    bikes_a = lane_a['bicycle'] + lane_a['motorcycle']
    bikes_b = lane_b['bicycle'] + lane_b['motorcycle']
    print(
        f"[Frame {frame_number:>5}  |  {timestamp_s:6.2f}s]  "
        f"Lane A: {lane_a['total']:>2} total (C:{lane_a['car']} B:{bikes_a} "
        f"Bus:{lane_a['bus']} Truck:{lane_a['truck']})  |  "
        f"Lane B: {lane_b['total']:>2} total (C:{lane_b['car']} B:{bikes_b} "
        f"Bus:{lane_b['bus']} Truck:{lane_b['truck']})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart Traffic Video Processor – annotates vehicles per lane"
    )
    parser.add_argument("--video", required=True, help="Path to input video file (.mp4, .avi …)")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLOv8 weights (default: yolov8n.pt)")
    parser.add_argument("--conf", type=float, default=0.35, help="Detection confidence threshold")
    parser.add_argument("--no-display", action="store_true", help="Disable live preview window")
    parser.add_argument("--output", default=None, help="Output video path (default: auto-generated)")
    args = parser.parse_args()

    # ── Validate input ─────────────────────────────────────────────────────────
    if not Path(args.video).exists():
        print(f"ERROR: Video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or build_output_path(args.video)

    # ── Print metadata ─────────────────────────────────────────────────────────
    meta = get_video_metadata(args.video)
    print("=" * 60)
    print(f"  Input  : {args.video}")
    print(f"  Output : {output_path}")
    print(f"  FPS    : {meta['fps']:.2f}  |  Frames: {meta['total_frames']}")
    print(f"  Size   : {meta['width']} × {meta['height']}")
    print(f"  Model  : {args.model}  |  Conf ≥ {args.conf}")
    print("=" * 60)

    # ── Initialise detector ────────────────────────────────────────────────────
    detector = VehicleDetector(model_path=args.model, conf_threshold=args.conf)

    # ── Prepare video writer ───────────────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        output_path,
        fourcc,
        meta["fps"],
        (meta["width"], meta["height"]),
    )

    # ── Running accumulators ───────────────────────────────────────────────────
    total_a_count = total_b_count = 0
    total_a_cars = total_a_bikes = total_a_buses = total_a_trucks = 0
    total_b_cars = total_b_bikes = total_b_buses = total_b_trucks = 0
    t_start = time.perf_counter()

    # ── Main processing loop ───────────────────────────────────────────────────
    for result in detector.process_video(args.video):
        fn      = result["frame"]
        ts_s    = result["timestamp"]
        lane_a  = result["lane_a"]
        lane_b  = result["lane_b"]
        ann     = result["annotated_frame"]

        # Accumulate statistics
        total_a_count += lane_a["total"]
        total_b_count += lane_b["total"]
        total_a_cars += lane_a["car"]
        total_a_bikes += lane_a["bicycle"] + lane_a["motorcycle"]
        total_a_buses += lane_a["bus"]
        total_a_trucks += lane_a["truck"]
        total_b_cars += lane_b["car"]
        total_b_bikes += lane_b["bicycle"] + lane_b["motorcycle"]
        total_b_buses += lane_b["bus"]
        total_b_trucks += lane_b["truck"]

        # Write annotated frame to output video
        writer.write(ann)

        # Print summary every SUMMARY_EVERY frames
        if fn % SUMMARY_EVERY == 0:
            print_summary(fn, lane_a, lane_b, ts_s)

        # Optional live display
        if not args.no_display:
            cv2.imshow("Smart Traffic Monitor  [q = quit]", ann)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\n[INFO] Quit by user.")
                break

    # ── Cleanup ────────────────────────────────────────────────────────────────
    writer.release()
    if not args.no_display:
        cv2.destroyAllWindows()

    elapsed = time.perf_counter() - t_start
    total_frames = meta["total_frames"] or 1

    print("\n" + "=" * 80)
    print("  PROCESSING COMPLETE")
    print(f"  Elapsed        : {elapsed:.1f}s  ({elapsed / total_frames * 1000:.1f} ms/frame)")
    print()
    print("  LANE A Statistics:")
    print(f"    Total vehicles    : {total_a_count}")
    print(f"    Cars              : {total_a_cars}")
    print(f"    Bikes/Motorcycles : {total_a_bikes}")
    print(f"    Buses             : {total_a_buses}")
    print(f"    Trucks            : {total_a_trucks}")
    print()
    print("  LANE B Statistics:")
    print(f"    Total vehicles    : {total_b_count}")
    print(f"    Cars              : {total_b_cars}")
    print(f"    Bikes/Motorcycles : {total_b_bikes}")
    print(f"    Buses             : {total_b_buses}")
    print(f"    Trucks            : {total_b_trucks}")
    print()
    print(f"  Annotated video    : {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
