# SUMO Next Steps (After Adding 4 Videos)

## Current Status

- Videos detected in `Code/YOLO/darkflow/videos`:
  - `video_1.mp4`
  - `video_2.mp4`
  - `video_3.mp4`
  - `video_4.mp4`
- YOLOv8 detector already available in this repo.

## What To Do Next (Execution Order)

1. Set ROI for each road
- Open each video and draw one polygon covering only incoming lanes.
- Update polygon points in `Code/YOLO/darkflow/videos/roi_config.json`.

2. Use 10-second slots
- Keep `window_seconds = 10`.
- Keep `step_seconds = 10` for simple demo.
- Optional later: `step_seconds = 5` for smoother updates.

3. Count vehicles per slot
- For each road and each 10-second slot:
  - Run YOLO detections.
  - Keep detections only if object center is inside ROI.
  - Count by class (`car`, `bus`, `truck`, `motorcycle`).

4. Compute signal split from counts
- Cycle green budget approach:
  - `minGreen = 10s` per road
  - `nominalCycle = 120s`
  - Remaining budget = `120 - 4*10 = 80s`
- Weighted demand score:
  - `score = car*1.0 + motorcycle*0.7 + bus*2.5 + truck*2.5`
- Split remaining budget proportional to score.
- Clamp each road to `[10, 60]` seconds.

5. Edge-case policy (must implement)
- All roads low traffic:
  - Use near-uniform greens, for example 10-15s each.
- All roads high traffic:
  - Use proportional split with max cap; if similar load, it becomes near-equal.
- One road very low:
  - Keep minimum 10s only; redistribute extra to heavier roads.

6. Send to SUMO
- For next slot:
  - Inject route demand per road from slot counts.
  - Apply computed green durations to signal phases.

7. Demo runtime (2 minutes)
- Total 120 seconds.
- Run 12 control slots of 10 seconds each.
- If a source video ends, loop it and continue.

## Recommended First Integration Milestone

- Milestone 1: ROI + slot counting only (no SUMO control yet).
- Output one CSV per slot with per-road class counts.
- After this is stable, connect the same output to SUMO controller.

## Files Introduced For Setup

- `Code/YOLO/darkflow/videos/roi_config.json`

Update ROI coordinates before starting implementation.
