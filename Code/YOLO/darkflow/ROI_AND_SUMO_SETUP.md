# ROI And SUMO Setup (Windows)

## Part A: Mark ROI Rectangle On Videos

Road mapping used:
- `video_1.mp4` -> `north`
- `video_2.mp4` -> `east`
- `video_3.mp4` -> `south`
- `video_4.mp4` -> `west`

### 1. Run ROI selector

From project root:

```powershell
cd Code/YOLO/darkflow
python roi_selector.py
```

### 2. How to mark rectangle

For each road video window:
- Drag mouse to draw rectangle over incoming lanes only
- Press `Enter` or `Space` to confirm
- Press `c` to cancel for that road

### 3. Where ROI gets saved

Updated file:
- `Code/YOLO/darkflow/videos/roi_config.json`

ROI is saved as 4-point polygon from your rectangle.

### 4. ROI rules

- Include only incoming lanes before stop line
- Exclude outgoing lanes
- Exclude junction center area
- Exclude side-road traffic if visible

---

## Part B: Install SUMO (You have not installed yet)

## Option 1 (Recommended): Windows installer

1. Download SUMO from official page:
- https://eclipse.dev/sumo/

2. Install it (default path is fine), for example:
- `C:\Program Files (x86)\Eclipse\Sumo`

3. Add environment variable `SUMO_HOME`:
- Value: SUMO install folder

4. Add SUMO `bin` folder to `Path`:
- Example: `C:\Program Files (x86)\Eclipse\Sumo\bin`

5. Open new PowerShell and verify:

```powershell
sumo --version
sumo-gui --version
```

## Option 2: Conda install (if you use conda)

```powershell
conda install -c conda-forge sumo
```

---

## Part C: Python packages for SUMO control

In your active venv, install:

```powershell
pip install traci sumolib
```

---

## Next milestone after setup

1. ROI marked and saved
2. SUMO installed and version verified
3. Python `traci` and `sumolib` installed
4. Start Milestone-1: 10-second slot counting pipeline

---

## Part D: Run Milestone-1 Slot Counting

From project root:

```powershell
cd Code/YOLO/darkflow
python slot_count_pipeline.py --duration-seconds 120 --sample-fps 1.0
```

Outputs are generated in:
- `Code/YOLO/darkflow/slot_outputs/`

Generated files:
- `slot_counts_<timestamp>.csv`
- `slot_counts_<timestamp>.json`

What this gives you:
- Per-road vehicle counts every 10-second slot (ROI-filtered)
- Suggested green split per slot using min/max bounded adaptive logic
