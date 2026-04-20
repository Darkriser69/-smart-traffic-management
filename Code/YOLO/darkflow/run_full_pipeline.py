"""
One-command runner for the full workflow:
  1) Optional video selection (native file picker)
  2) Optional ROI selection (interactive OpenCV)
  3) Slot-count pipeline (writes slot_counts_*.json/csv)
  4) Print compact table + summary to terminal
  5) Optional SUMO replay (GUI optional)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "videos" / "roi_config.json"
SLOT_OUTPUT_DIR = BASE_DIR / "slot_outputs"
REQUIRED_ROADS = ("north", "east", "south", "west")


def hr(title: str) -> None:
    line = "=" * max(12, len(title))
    print(f"\n{line}\n{title}\n{line}")


def stream_command(cmd: Sequence[str], cwd: Path) -> int:
    printable = " ".join(cmd)
    print(f"\n>>> {printable}\n")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        list(cmd),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env,
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    return int(proc.wait())


def newest_slot_json(slot_dir: Path) -> Path:
    files = sorted(slot_dir.glob("slot_counts_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No slot_counts_*.json found in: {slot_dir}")
    return files[-1]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_all_rois(config: dict) -> bool:
    roads = (config.get("roads") or {}) if isinstance(config, dict) else {}
    if not isinstance(roads, dict):
        return False
    for road in REQUIRED_ROADS:
        rc = roads.get(road) or {}
        poly = rc.get("roi_polygon")
        if not (isinstance(poly, list) and len(poly) >= 3):
            return False
    return True


def print_json_file(title: str, path: Path) -> None:
    hr(title)
    print(f"File: {path.resolve()}\n")
    data = load_json(path)
    print(json.dumps(data, indent=2))


def iter_slots(data: dict) -> Iterable[dict]:
    slots = data.get("slots", [])
    if not isinstance(slots, list):
        return []
    return slots


def summarize_counts(data: dict) -> dict:
    totals = {road: {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0, "total": 0} for road in REQUIRED_ROADS}
    overall = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0, "total": 0}

    for slot in iter_slots(data):
        counts = slot.get("counts", {}) or {}
        for road in totals.keys():
            rc = counts.get(road, {}) or {}
            for k in ("car", "bus", "truck", "motorcycle", "total"):
                v = int(rc.get(k, 0) or 0)
                totals[road][k] += v
                overall[k] += v
    return {"by_road": totals, "overall": overall}


def print_summary(data: dict, slot_json_path: Path) -> None:
    hr("Vehicle count summary (aggregated across all slots)")
    summary = summarize_counts(data)
    overall = summary["overall"]
    print(f"From: {slot_json_path.name}\n")
    print(
        "OVERALL: "
        f"total={overall['total']} | "
        f"car={overall['car']} bus={overall['bus']} truck={overall['truck']} motorcycle={overall['motorcycle']}\n"
    )

    by_road = summary["by_road"]
    for road, d in by_road.items():
        print(
            f"{road.upper():5} "
            f"total={d['total']:6d} | "
            f"car={d['car']:6d} bus={d['bus']:6d} truck={d['truck']:6d} motorcycle={d['motorcycle']:6d}"
        )


def _fmt_row(cols: list[str], widths: list[int]) -> str:
    return "| " + " | ".join(c.ljust(w) for c, w in zip(cols, widths, strict=False)) + " |"


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(sep)
    print(_fmt_row(headers, widths))
    print(sep)
    for r in rows:
        print(_fmt_row(r, widths))
    print(sep)


def print_slot_json_as_table(data: dict, max_slots: int = 0) -> None:
    hr("Slot JSON (table view)")
    slots = list(iter_slots(data))
    if max_slots and max_slots > 0:
        slots = slots[: max_slots]

    headers = [
        "slot",
        "t(s)",
        "road",
        "car",
        "bus",
        "truck",
        "moto",
        "total",
        "green_sec",
        "frames",
    ]
    rows: list[list[str]] = []
    for slot in slots:
        idx = str(int(slot.get("slot_index", 0)))
        t = f"{int(slot.get('slot_start_sec', 0))}-{int(slot.get('slot_end_sec', 0))}"
        counts = slot.get("counts", {}) or {}
        greens = slot.get("green_allocation_sec", {}) or {}

        for road in REQUIRED_ROADS:
            rc = counts.get(road, {}) or {}
            rows.append(
                [
                    idx,
                    t,
                    road,
                    str(int(rc.get("car", 0) or 0)),
                    str(int(rc.get("bus", 0) or 0)),
                    str(int(rc.get("truck", 0) or 0)),
                    str(int(rc.get("motorcycle", 0) or 0)),
                    str(int(rc.get("total", 0) or 0)),
                    str(int(greens.get(road, 0) or 0)),
                    str(int(rc.get("frames_sampled", 0) or 0)),
                ]
            )

    if not rows:
        print("[No slots found in JSON]")
        return

    _print_table(headers, rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run ROI -> slot counts -> SUMO replay in one command")

    p.add_argument(
        "--pick-videos",
        action="store_true",
        help="Open dialogs to choose videos for north/east/south/west",
    )

    p.add_argument("--roi", action="store_true", help="Run ROI selector first (interactive OpenCV windows)")
    p.add_argument("--config", type=str, default=str(DEFAULT_CONFIG), help="Path to ROI config JSON")

    p.add_argument("--model", type=str, default="yolov8n.pt", help="YOLOv8 model path")
    p.add_argument("--confidence", type=float, default=0.35, help="Detection confidence")
    p.add_argument("--duration-seconds", type=int, default=240, help="Total demo duration")
    p.add_argument("--sample-fps", type=float, default=1.0, help="Samples per second inside each slot")
    p.add_argument("--cycle-seconds", type=int, default=120, help="Green-time budget per cycle")
    p.add_argument("--min-green", type=int, default=10, help="Minimum green per road")
    p.add_argument("--max-green", type=int, default=60, help="Maximum green per road")
    p.add_argument("--output-dir", type=str, default=str(SLOT_OUTPUT_DIR), help="Slot output directory")
    p.add_argument("--table-max-slots", type=int, default=0, help="If >0, print only first N slots in table")
    p.add_argument("--print-json", action="store_true", help="Also print full slot JSON")

    p.add_argument("--sumo", action="store_true", default=True, help="Run SUMO replay after slot counting (default: on)")
    p.add_argument("--no-sumo", dest="sumo", action="store_false", help="Skip SUMO replay")
    p.add_argument("--gui", action="store_true", help="Run with sumo-gui")
    p.add_argument("--step-delay", type=float, default=0.3, help="GUI delay per simulation step in seconds")
    p.add_argument("--zoom", type=float, default=1200.0, help="SUMO GUI zoom")
    p.add_argument("--schema", type=str, default="clear_view", help="SUMO GUI schema name")
    p.add_argument("--software-render", action="store_true", default=True, help="Force software OpenGL for SUMO GUI")
    p.add_argument("--hardware-render", dest="software_render", action="store_false", help="Use hardware OpenGL rendering")
    p.add_argument("--no-internal-links", action="store_true", default=True, help="Disable internal junction links (cleaner visuals)")
    p.add_argument("--with-internal-links", dest="no_internal_links", action="store_false", help="Keep internal links")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    cwd = BASE_DIR
    py = sys.executable

    hr("ONE COMMAND WORKFLOW START")
    print(f"Working directory: {cwd}")
    print(f"Python: {py}")

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (cwd / config_path).resolve()

    if args.pick_videos:
        hr("Step 0: Pick videos (north/east/south/west)")
        code = stream_command([py, "-u", "video_picker.py"], cwd=cwd)
        if code != 0:
            print(f"\n[STOP] Video picking failed with exit code {code}")
            return code
        if config_path.exists():
            print_json_file("ROI config JSON (after video selection)", config_path)
        args.roi = True

    if args.roi:
        hr("Step 1: ROI selection (interactive)")
        code = stream_command([py, "-u", "roi_selector.py"], cwd=cwd)
        if code != 0:
            print(f"\n[STOP] ROI selector failed with exit code {code}")
            return code
        if config_path.exists():
            print_json_file("ROI config JSON (after ROI selection)", config_path)

    if config_path.exists():
        cfg_now = load_json(config_path)
        if not has_all_rois(cfg_now):
            hr("STOP: ROI not configured yet")
            print(
                "Your selected videos are saved, but ROI polygons are missing.\n"
                "Run again with ROI enabled so you can draw ROIs:\n\n"
                "  python .\\run_full_pipeline.py --pick-videos --roi --no-sumo\n"
            )
            return 1

    hr("Step 2: Slot counting pipeline")
    slot_cmd = [
        py,
        "-u",
        "slot_count_pipeline.py",
        "--config",
        str(config_path),
        "--model",
        str(args.model),
        "--confidence",
        str(args.confidence),
        "--duration-seconds",
        str(args.duration_seconds),
        "--sample-fps",
        str(args.sample_fps),
        "--cycle-seconds",
        str(args.cycle_seconds),
        "--min-green",
        str(args.min_green),
        "--max-green",
        str(args.max_green),
        "--output-dir",
        str(args.output_dir),
    ]
    code = stream_command(slot_cmd, cwd=cwd)
    if code != 0:
        print(f"\n[STOP] Slot counting failed with exit code {code}")
        return code

    slot_dir = Path(args.output_dir)
    if not slot_dir.is_absolute():
        slot_dir = (cwd / slot_dir).resolve()
    slot_json_path = newest_slot_json(slot_dir)

    data = load_json(slot_json_path)
    if args.print_json:
        print_json_file("Slot output JSON (generated by slot_count_pipeline)", slot_json_path)
    print_slot_json_as_table(data, max_slots=args.table_max_slots)
    print_summary(data, slot_json_path)

    if not args.sumo:
        hr("DONE (SUMO replay skipped)")
        return 0

    hr("Step 3: SUMO replay / simulation")
    sumo_cmd = [
        py,
        "-u",
        "sumo_slot_bridge.py",
        "--slot-json",
        str(slot_json_path),
    ]
    if args.gui:
        sumo_cmd.append("--gui")
    sumo_cmd.extend(["--step-delay", str(args.step_delay)])
    sumo_cmd.extend(["--zoom", str(args.zoom)])
    sumo_cmd.extend(["--schema", str(args.schema)])
    if args.software_render:
        sumo_cmd.append("--software-render")
    else:
        sumo_cmd.append("--hardware-render")
    if args.no_internal_links:
        sumo_cmd.append("--no-internal-links")
    else:
        sumo_cmd.append("--with-internal-links")

    code = stream_command(sumo_cmd, cwd=cwd)
    if code != 0:
        print(f"\n[WARN] SUMO replay exited with code {code}")
        return code

    hr("WORKFLOW COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
