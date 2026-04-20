"""
ROI selector for 4-road traffic videos.

Usage:
    python roi_selector.py

This script:
1. Reads videos and road mapping from videos/roi_config.json
2. Opens one frame per video
3. Lets you draw a rectangle ROI using OpenCV GUI
4. Saves ROI as polygon points in roi_config.json
"""

import json
from pathlib import Path

import cv2


BASE_DIR = Path(__file__).resolve().parent
VIDEOS_DIR = BASE_DIR / "videos"
CONFIG_PATH = VIDEOS_DIR / "roi_config.json"


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


def rect_to_polygon(x, y, w, h):
    return [
        [int(x), int(y)],
        [int(x + w), int(y)],
        [int(x + w), int(y + h)],
        [int(x), int(y + h)],
    ]


def get_first_frame(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    return frame


def select_roi_for_road(road_name, video_file):
    video_path = VIDEOS_DIR / video_file
    frame = get_first_frame(video_path)

    if frame is None:
        print(f"[ERROR] Could not read frame for {road_name}: {video_file}")
        return None

    window_name = f"ROI Select - {road_name} ({video_file})"
    print(f"\nRoad: {road_name} | Video: {video_file}")
    print("Draw rectangle and press ENTER or SPACE. Press C to cancel this road.")

    roi = cv2.selectROI(window_name, frame, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow(window_name)

    x, y, w, h = roi
    if w <= 0 or h <= 0:
        print(f"[SKIP] No ROI selected for {road_name}")
        return None

    polygon = rect_to_polygon(x, y, w, h)
    print(f"[OK] {road_name} ROI polygon: {polygon}")
    return polygon


def main():
    if not CONFIG_PATH.exists():
        print(f"[ERROR] Missing config: {CONFIG_PATH}")
        return

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    roads = cfg.get("roads", {})
    if not roads:
        print("[ERROR] No roads found in config.")
        return

    print("Starting ROI selection for configured roads...")

    for road_name, road_cfg in roads.items():
        video_file = road_cfg.get("video")
        if not video_file:
            print(f"[WARN] No video set for road {road_name}, skipping.")
            continue

        polygon = select_roi_for_road(road_name, video_file)
        if polygon is not None:
            road_cfg["roi_polygon"] = polygon

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")

    print("\nDone. Updated:")
    print(CONFIG_PATH)
    print("Saved ROI configuration:")

    table_rows = []
    for road_name, road_cfg in roads.items():
        table_rows.append(
            [
                road_name,
                road_cfg.get("video", ""),
                json.dumps(road_cfg.get("roi_polygon", [])),
            ]
        )

    print_table(headers=["road", "video", "roi_polygon"], rows=table_rows)
    print("Now verify ROI points manually in JSON if needed.")


if __name__ == "__main__":
    main()
