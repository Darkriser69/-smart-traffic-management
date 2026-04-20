"""
Slot-based ROI vehicle counting pipeline for 4-road videos.

Milestone-1 output:
- Per-slot vehicle counts by road/class (CSV + JSON)
- Suggested green time allocation per road/slot

Usage:
    python slot_count_pipeline.py

Optional args:
    python slot_count_pipeline.py --duration-seconds 240 --sample-fps 1.0
"""

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import sys

# Import detector from parent folder: Code/YOLO/yolov8_detect.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from yolov8_detect import YOLOv8VehicleDetector


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "videos" / "roi_config.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "slot_outputs"

VEHICLE_TYPES = ("car", "bus", "truck", "motorcycle")
DEMAND_WEIGHTS = {
    "car": 1.0,
    "motorcycle": 0.7,
    "bus": 2.5,
    "truck": 2.5,
}


def print_table(headers, rows):
    if not rows:
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt(row):
        return " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * w for w in widths)
    print(fmt(headers))
    print(separator)
    for row in rows:
        print(fmt(row))


def parse_args():
    parser = argparse.ArgumentParser(description="10-second slot traffic counting pipeline")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG), help="Path to ROI config JSON")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLOv8 model path")
    parser.add_argument("--confidence", type=float, default=0.35, help="Detection confidence")
    parser.add_argument("--duration-seconds", type=int, default=240, help="Total demo duration")
    parser.add_argument("--sample-fps", type=float, default=1.0, help="Samples per second inside each slot")
    parser.add_argument("--cycle-seconds", type=int, default=120, help="Green-time budget per cycle")
    parser.add_argument("--min-green", type=int, default=10, help="Minimum green per road")
    parser.add_argument("--max-green", type=int, default=60, help="Maximum green per road")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    return parser.parse_args()


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def open_video(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 else 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise RuntimeError(f"Video has no frames: {video_path}")

    duration_sec = total_frames / fps
    return {
        "cap": cap,
        "fps": fps,
        "total_frames": total_frames,
        "duration_sec": duration_sec,
    }


def close_videos(video_states):
    for state in video_states.values():
        state["cap"].release()


def vehicle_center(vehicle):
    x1 = vehicle["topleft"]["x"]
    y1 = vehicle["topleft"]["y"]
    x2 = vehicle["bottomright"]["x"]
    y2 = vehicle["bottomright"]["y"]
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def count_in_roi(detections, roi_polygon):
    counts = {k: 0 for k in VEHICLE_TYPES}
    roi = np.array(roi_polygon, dtype=np.int32)

    for vehicle in detections.get("vehicles", []):
        label = vehicle.get("label", "").lower()
        if label not in counts:
            continue

        cx, cy = vehicle_center(vehicle)
        inside = cv2.pointPolygonTest(roi, (float(cx), float(cy)), False)
        if inside >= 0:
            counts[label] += 1

    counts["total"] = sum(counts.values())
    return counts


def sample_times(slot_start, window_seconds, sample_fps):
    # Sample at fixed temporal points: e.g., 1 fps -> 10 samples in 10 seconds.
    num_samples = max(1, int(round(window_seconds * sample_fps)))
    delta = window_seconds / num_samples
    return [slot_start + (i * delta) for i in range(num_samples)]


def read_frame_at_time(cap, time_sec, fps, total_frames, duration_sec):
    wrapped_time = time_sec % duration_sec
    frame_idx = int(wrapped_time * fps)
    frame_idx = max(0, min(total_frames - 1, frame_idx))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    if not ok:
        return None, wrapped_time
    return frame, wrapped_time


def weighted_score(counts):
    return (
        counts.get("car", 0) * DEMAND_WEIGHTS["car"]
        + counts.get("motorcycle", 0) * DEMAND_WEIGHTS["motorcycle"]
        + counts.get("bus", 0) * DEMAND_WEIGHTS["bus"]
        + counts.get("truck", 0) * DEMAND_WEIGHTS["truck"]
    )


def allocate_greens(road_counts, cycle_seconds, min_green, max_green):
    roads = list(road_counts.keys())
    n = len(roads)
    base_total = n * min_green
    if base_total > cycle_seconds:
        raise ValueError("min_green too high for selected cycle_seconds")

    remaining = cycle_seconds - base_total
    greens = {road: min_green for road in roads}

    scores = {road: weighted_score(road_counts[road]) for road in roads}
    score_sum = sum(scores.values())

    # No demand observed -> keep near-uniform timing.
    if score_sum <= 0:
        if remaining == 0:
            return greens
        share = remaining // n
        extra = remaining % n
        for i, road in enumerate(roads):
            greens[road] += share + (1 if i < extra else 0)
        return {road: min(max_green, greens[road]) for road in roads}

    # Proportional distribution from remaining budget.
    fractional = {}
    for road in roads:
        add = remaining * (scores[road] / score_sum)
        fractional[road] = add
        greens[road] += int(math.floor(add))

    assigned = sum(greens.values())
    to_assign = cycle_seconds - assigned

    # Assign leftover seconds to roads with highest fractional remainder and unmet max.
    order = sorted(roads, key=lambda r: fractional[r] - math.floor(fractional[r]), reverse=True)
    while to_assign > 0:
        progressed = False
        for road in order:
            if greens[road] < max_green:
                greens[road] += 1
                to_assign -= 1
                progressed = True
                if to_assign == 0:
                    break
        if not progressed:
            break

    # Enforce caps and redistribute if needed.
    for road in roads:
        greens[road] = max(min_green, min(max_green, greens[road]))

    # Keep total aligned to cycle_seconds when possible within caps.
    current_total = sum(greens.values())
    if current_total < cycle_seconds:
        while current_total < cycle_seconds:
            progressed = False
            for road in sorted(roads, key=lambda r: scores[r], reverse=True):
                if greens[road] < max_green:
                    greens[road] += 1
                    current_total += 1
                    progressed = True
                    if current_total == cycle_seconds:
                        break
            if not progressed:
                break
    elif current_total > cycle_seconds:
        while current_total > cycle_seconds:
            progressed = False
            for road in sorted(roads, key=lambda r: scores[r]):
                if greens[road] > min_green:
                    greens[road] -= 1
                    current_total -= 1
                    progressed = True
                    if current_total == cycle_seconds:
                        break
            if not progressed:
                break

    return greens


def aggregate_slot_counts(per_frame_counts):
    total_frames = len(per_frame_counts)
    if total_frames == 0:
        return {
            "car": 0,
            "bus": 0,
            "truck": 0,
            "motorcycle": 0,
            "total": 0,
            "frames_sampled": 0,
            "method": "max_over_samples",
        }

    max_counts = {k: 0 for k in VEHICLE_TYPES}
    for fc in per_frame_counts:
        for k in VEHICLE_TYPES:
            max_counts[k] = max(max_counts[k], fc.get(k, 0))

    max_counts["total"] = sum(max_counts.values())
    max_counts["frames_sampled"] = total_frames
    max_counts["method"] = "max_over_samples"
    return max_counts


def write_outputs(csv_path, json_path, rows, slot_summaries, args, config_path, window_seconds, step_seconds):
    fieldnames = [
        "slot_index",
        "slot_start_sec",
        "slot_end_sec",
        "road",
        "video",
        "frames_sampled",
        "car",
        "bus",
        "truck",
        "motorcycle",
        "total",
        "aggregation_method",
        "video_time_start",
        "video_time_end",
        "green_sec",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    result = {
        "config_path": str(Path(config_path).resolve()),
        "model": args.model,
        "confidence": args.confidence,
        "duration_seconds": args.duration_seconds,
        "window_seconds": window_seconds,
        "step_seconds": step_seconds,
        "sample_fps": args.sample_fps,
        "cycle_seconds": args.cycle_seconds,
        "min_green": args.min_green,
        "max_green": args.max_green,
        "slots": slot_summaries,
        "csv_output": str(csv_path.resolve()),
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")


def main():
    args = parse_args()
    cfg = load_config(args.config)

    window_seconds = int(cfg.get("window_seconds", 10))
    step_seconds = int(cfg.get("step_seconds", 10))
    roads_cfg = cfg.get("roads", {})

    if step_seconds <= 0 or window_seconds <= 0:
        raise ValueError("window_seconds and step_seconds must be > 0")

    required_roads = ("north", "east", "south", "west")
    for road in required_roads:
        if road not in roads_cfg:
            raise ValueError(f"Missing road in config: {road}")

    detector = YOLOv8VehicleDetector(args.model, confidence_threshold=args.confidence)

    video_states = {}
    for road, road_cfg in roads_cfg.items():
        video_file = road_cfg.get("video")
        if not video_file:
            raise ValueError(f"Missing video for road: {road}")
        video_path = BASE_DIR / "videos" / video_file
        video_states[road] = open_video(video_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"slot_counts_{timestamp}.csv"
    json_path = output_dir / f"slot_counts_{timestamp}.json"

    rows = []
    slot_summaries = []

    slots = list(range(0, args.duration_seconds, step_seconds))

    try:
        for slot_index, slot_start in enumerate(slots):
            slot_end = slot_start + window_seconds
            road_slot_counts = {}

            for road, road_cfg in roads_cfg.items():
                state = video_states[road]
                cap = state["cap"]
                fps = state["fps"]
                total_frames = state["total_frames"]
                duration_sec = state["duration_sec"]
                roi_polygon = road_cfg.get("roi_polygon")

                if not roi_polygon or len(roi_polygon) < 3:
                    raise ValueError(f"Invalid ROI polygon for road: {road}")

                times = sample_times(slot_start, window_seconds, args.sample_fps)
                per_frame_counts = []
                sampled_video_times = []

                for t in times:
                    frame, wrapped_t = read_frame_at_time(cap, t, fps, total_frames, duration_sec)
                    if frame is None:
                        continue

                    detections = detector.detect_vehicles(frame, return_annotated=False)
                    counts = count_in_roi(detections, roi_polygon)
                    per_frame_counts.append(counts)
                    sampled_video_times.append(wrapped_t)

                slot_counts = aggregate_slot_counts(per_frame_counts)
                road_slot_counts[road] = slot_counts

                rows.append(
                    {
                        "slot_index": slot_index,
                        "slot_start_sec": slot_start,
                        "slot_end_sec": slot_end,
                        "road": road,
                        "video": road_cfg.get("video", ""),
                        "frames_sampled": slot_counts["frames_sampled"],
                        "car": slot_counts["car"],
                        "bus": slot_counts["bus"],
                        "truck": slot_counts["truck"],
                        "motorcycle": slot_counts["motorcycle"],
                        "total": slot_counts["total"],
                        "aggregation_method": slot_counts["method"],
                        "video_time_start": round(min(sampled_video_times), 3) if sampled_video_times else None,
                        "video_time_end": round(max(sampled_video_times), 3) if sampled_video_times else None,
                    }
                )

            greens = allocate_greens(
                road_slot_counts,
                cycle_seconds=args.cycle_seconds,
                min_green=args.min_green,
                max_green=args.max_green,
            )

            for row in rows[-len(roads_cfg) :]:
                row["green_sec"] = greens[row["road"]]

            slot_summaries.append(
                {
                    "slot_index": slot_index,
                    "slot_start_sec": slot_start,
                    "slot_end_sec": slot_end,
                    "counts": road_slot_counts,
                    "green_allocation_sec": greens,
                }
            )

            print(f"\nSlot Table [{slot_start}-{slot_end}s]")
            table_rows = []
            for road in required_roads:
                c = road_slot_counts[road]
                table_rows.append(
                    [
                        road,
                        roads_cfg[road].get("video", ""),
                        c["car"],
                        c["bus"],
                        c["truck"],
                        c["motorcycle"],
                        c["total"],
                        greens[road],
                    ]
                )
            print_table(
                headers=["road", "video", "car", "bus", "truck", "motorcycle", "total", "green_sec"],
                rows=table_rows,
            )

            print(
                f"Slot {slot_index:02d} [{slot_start}-{slot_end}s] | "
                f"N={road_slot_counts['north']['total']} E={road_slot_counts['east']['total']} "
                f"S={road_slot_counts['south']['total']} W={road_slot_counts['west']['total']} | "
                f"Green N/E/S/W = {greens['north']}/{greens['east']}/{greens['south']}/{greens['west']}"
            )

            # Persist progress every slot so partial runs still produce usable outputs.
            write_outputs(
                csv_path=csv_path,
                json_path=json_path,
                rows=rows,
                slot_summaries=slot_summaries,
                args=args,
                config_path=args.config,
                window_seconds=window_seconds,
                step_seconds=step_seconds,
            )

    finally:
        close_videos(video_states)

    # Final write for completeness.
    write_outputs(
        csv_path=csv_path,
        json_path=json_path,
        rows=rows,
        slot_summaries=slot_summaries,
        args=args,
        config_path=args.config,
        window_seconds=window_seconds,
        step_seconds=step_seconds,
    )

    print("\nFull CSV Table Output")
    csv_headers = [
        "slot_start_sec",
        "slot_end_sec",
        "road",
        "video",
        "car",
        "bus",
        "truck",
        "motorcycle",
        "total",
        "green_sec",
    ]
    csv_rows = [[row.get(h, "") for h in csv_headers] for row in rows]
    print_table(csv_headers, csv_rows)

    print("\nPipeline completed.")
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
