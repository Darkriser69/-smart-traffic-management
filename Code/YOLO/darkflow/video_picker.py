"""
GUI-assisted video picker for mapping videos to north/east/south/west.

This runs BEFORE ROI selection so the user can manually choose which videos
belong to each road direction.

Behavior:
  - Prompts via native file dialogs (Tkinter) for each road.
  - Ensures selected videos exist under darkflow/videos/ (copies if needed).
  - Updates videos/roi_config.json "roads.<road>.video".
  - Clears existing ROI polygons (since ROI is video-dependent).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def _choose_file_dialog(title: str, initial_dir: Path) -> Path | None:
    # Tkinter is part of the Python standard library on Windows.
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        file_path = filedialog.askopenfilename(
            title=title,
            initialdir=str(initial_dir),
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.m4v"),
                ("All files", "*.*"),
            ],
        )
    finally:
        root.destroy()

    if not file_path:
        return None
    return Path(file_path)


def _safe_copy_into_folder(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)

    # If already in the folder, keep as-is.
    try:
        if src.resolve().parent == dst_dir.resolve():
            return src.resolve()
    except OSError:
        pass

    stem = src.stem
    suffix = src.suffix or ".mp4"
    candidate = dst_dir / f"{stem}{suffix}"
    n = 1
    while candidate.exists():
        candidate = dst_dir / f"{stem}_{n}{suffix}"
        n += 1

    shutil.copy2(str(src), str(candidate))
    return candidate.resolve()


def pick_and_update_config(config_path: Path, videos_dir: Path) -> Path:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    roads = cfg.get("roads") or {}
    if not isinstance(roads, dict) or not roads:
        raise ValueError("roi_config.json has no 'roads' mapping")

    selected: dict[str, Path] = {}
    for road in ("north", "east", "south", "west"):
        if road not in roads:
            roads[road] = {}

        chosen = _choose_file_dialog(f"Select video for {road.upper()}", initial_dir=videos_dir)
        if chosen is None:
            raise RuntimeError(f"Selection cancelled for road: {road}")
        if not chosen.exists():
            raise FileNotFoundError(f"Selected video does not exist: {chosen}")

        local_path = _safe_copy_into_folder(chosen, videos_dir)
        selected[road] = local_path

    # Update config: store just the filename under videos/
    for road, local_path in selected.items():
        roads.setdefault(road, {})
        roads[road]["video"] = local_path.name
        # Clear ROI because it must be redrawn for the new video.
        roads[road].pop("roi_polygon", None)

    cfg["roads"] = roads

    with config_path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")

    return config_path


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    videos_dir = base_dir / "videos"
    config_path = videos_dir / "roi_config.json"

    try:
        updated = pick_and_update_config(config_path=config_path, videos_dir=videos_dir)
    except Exception as e:
        print(f"[ERROR] Video selection failed: {e}")
        return 1

    print("[OK] Updated video mapping in:")
    print(updated)
    print("Next: run ROI selection to create new ROI polygons for these videos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
