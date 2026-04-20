# Milestone-2/3: Slot Output To SUMO Bridge

## What this milestone does

- Uses output from `slot_count_pipeline.py` JSON
- Starts SUMO/SUMO-GUI on a 4-way intersection
- Injects vehicles per 10-second slot by road and class
- Runs simulation for full demo duration
- Milestone-3: applies adaptive traffic-light states via TraCI each slot

## 1) Build network once

```powershell
cd Code/YOLO/darkflow/sumo
powershell -ExecutionPolicy Bypass -File .\build_network.ps1
```

This creates:
- `intersection.net.xml`

## 2) Run bridge

```powershell
cd Code/YOLO/darkflow
python sumo_slot_bridge.py --gui
```

Optional explicit slot file:

```powershell
python sumo_slot_bridge.py --slot-json .\slot_outputs\slot_counts_<timestamp>.json --gui
```

Recommended visual demo run (clear movement):

```powershell
python sumo_slot_bridge.py --gui --step-delay 0.3 --zoom 1200 --schema clear_view --software-render --no-internal-links
```

Quick test with only first 3 slots:

```powershell
python sumo_slot_bridge.py --gui --max-slots 3
```

## Notes

- Vehicle injection mapping uses your roads:
  - north -> edge `n2c`
  - east -> edge `e2c`
  - south -> edge `s2c`
  - west -> edge `w2c`
- Turn choice is randomized (straight/right/left ratios) for demo realism.
- Adaptive TLS controller uses slot green hints as credits and chooses active road fairly over time.
- `--yellow-seconds` controls yellow duration near end of each slot.
- `--step-delay` slows replay for easier visualization in SUMO GUI.
- `--zoom` centers and zooms the view so intersection/vehicles are visible.
- `--schema standard` gives clearer lane/vehicle contrast than `real world` on many systems.
- `--no-internal-links` hides internal connector lanes that often appear as moving green lines.
- `--software-render` forces software OpenGL and often removes horizontal/green stripe rendering artifacts.
- If SUMO GUI is not needed, run without `--gui`.

## Normal messages

- `simulation ended at time ... reason: TraCI request termination` is expected when the Python script ends and closes SUMO.
- If you manually stop (`Ctrl+C`), the bridge now handles close more gracefully.

## Next

- Add queue/waiting-time metrics export.
- Add per-road performance comparison against fixed-time baseline.
