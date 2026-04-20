# Project Workflow Documentation (Current Running Version)

## 1) What This Project Does (Short)

This project runs an adaptive traffic simulation in SUMO using 4 road videos as input.

Flow:
1. Detect vehicles from each road video.
2. Count only vehicles inside ROI (incoming side).
3. Build 10-second slot-wise traffic demand.
4. Compute adaptive green-time hints.
5. Replay those hints and vehicle demand in SUMO.

## 2) Are Vehicles Random or Video-Based?

Current running SUMO workflow:
- Vehicles are generated from video-based counts (`video_1` to `video_4`) in 10-second slots.
- So this is video-driven demand replay, not fully random traffic generation.


## 3) Main Files and Their Purpose

### Core Running Files
- `Code/YOLO/darkflow/videos/roi_config.json`
  - Road-to-video mapping and ROI polygons.
  - Active mapping:
    - `video_1.mp4` -> north
    - `video_2.mp4` -> east
    - `video_3.mp4` -> south
    - `video_4.mp4` -> west

- `Code/YOLO/darkflow/roi_selector.py`
  - Interactive tool to draw ROI rectangles and save to `roi_config.json`.

- `Code/YOLO/darkflow/slot_count_pipeline.py`
  - Reads videos + ROI.
  - Performs slot-wise counting.
  - Saves outputs in `slot_outputs/` as CSV/JSON.

- `Code/YOLO/darkflow/sumo_slot_bridge.py`
  - Reads slot JSON output.
  - Starts SUMO/SUMO-GUI through TraCI.
  - Injects vehicles by road and class.
  - Applies adaptive traffic-light behavior slot-by-slot.

### SUMO Network Files
- `Code/YOLO/darkflow/sumo/intersection.nod.xml`
  - Node definitions.
- `Code/YOLO/darkflow/sumo/intersection.edg.xml`
  - Edge/lane definitions.
- `Code/YOLO/darkflow/sumo/intersection.net.xml`
  - Generated SUMO network.
- `Code/YOLO/darkflow/sumo/intersection.sumocfg`
  - SUMO configuration.
- `Code/YOLO/darkflow/sumo/empty.rou.xml`
  - Vehicle type definitions.
- `Code/YOLO/darkflow/sumo/build_network.ps1`
  - Rebuilds `intersection.net.xml` from node/edge files.
- `Code/YOLO/darkflow/sumo/clear_view.settings.xml`
  - GUI visualization settings profile.

### Detector / Utility Files
- `Code/YOLO/yolov8_detect.py`
  - YOLOv8 detector implementation used by slot counting.
- `Code/YOLO/darkflow/yolov8n.pt`
  - Model file used for detection.

### Output Folder
- `Code/YOLO/darkflow/slot_outputs/`
  - Generated slot-wise traffic data (`slot_counts_*.csv`, `slot_counts_*.json`).

## 4) Quick Commands (Shortcuts)

From project root:

1. Activate environment
```powershell
.\venv311\Scripts\Activate.ps1
```

2. Go to workflow folder
```powershell
cd Code\YOLO\darkflow
```

3. Pick 4 videos (north/east/south/west), then draw ROI, then run slot counting (skip SUMO)
```powershell
python .\run_full_pipeline.py --pick-videos --roi --no-sumo
```

4. Run full workflow in one command (pick videos + ROI + slot table + SUMO)
```powershell
python .\run_full_pipeline.py --pick-videos --roi
```

5. Run full workflow without reopening picker (uses current video mapping in roi_config.json)
```powershell
python .\run_full_pipeline.py
```

6. Draw ROI only (one-time or when camera changes)
```powershell
python .\roi_selector.py
```

7. Generate slot counts from videos
```powershell
python .\slot_count_pipeline.py --duration-seconds 240 --sample-fps 1.0
```

8. Rebuild SUMO network (after edge/node changes)
```powershell
cd .\sumo
powershell -ExecutionPolicy Bypass -File .\build_network.ps1
cd ..
```

9. Run SUMO replay (GUI)
```powershell
python .\sumo_slot_bridge.py --gui --step-delay 0.3 --zoom 1200 --schema clear_view --software-render --no-internal-links
```

## 5) Important Note

If you need physically complete junction internals, avoid `--no-internal-links`.
For clean demo visuals, `--no-internal-links` is acceptable.

## 6) Files Not Used In Current SUMO Workflow

- Old Pygame simulation file was removed from active project.
