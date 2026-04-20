# SUMO Documentation

## 1. Goal

Replace the current Pygame animation with SUMO simulation while keeping the same adaptive traffic-signal idea:

- Input: 4 road videos (one per incoming approach)
- Processing: vehicle detection with ROI (incoming lanes only)
- Control: adaptive signal timing logic
- Simulation: SUMO handles vehicle movement, queues, and traffic lights

---

## 2. Current Project Mapping

From the current repository:

- Detection exists (YOLOv8): `Code/YOLO/darkflow/vehicle_detection.py`
- Old simulation exists (Pygame): `Code/YOLO/darkflow/simulation.py`
- Adaptive timer concept already exists in `simulation.py`

Integration strategy:

- Keep detection and adaptive logic concept
- Replace only simulation/render layer with SUMO + TraCI control

---

## 3. 4-Video Integration Design

Each video is assigned to one incoming road:

- Video 1 -> North incoming
- Video 2 -> East incoming
- Video 3 -> South incoming
- Video 4 -> West incoming

For each video stream:

1. Define ROI polygon covering only incoming lanes before stop line
2. Detect vehicles only inside ROI
3. Count per class (`car`, `bus`, `truck`, `motorcycle`)
4. Convert count to demand for SUMO insertion

Important:

- ROI must exclude outgoing lanes and side background traffic
- If possible, use tracking (not only frame-wise detection) to avoid counting the same vehicle repeatedly

---

## 4. Your 10-Second Window Plan (Valid)

Your proposal is good and practical for demo:

- Take 10 seconds from each road video in one cycle
- Count vehicles in that 10-second window
- Send those counts to SUMO for the next simulation round
- Repeat with next 10-second window

This creates an online loop:

`video window (10s) -> ROI counts -> demand update -> SUMO next window`

---

## 5. Better Approach (Recommended)

Your approach works. A slightly better approach for stability is:

### Option A (Simple, good for demo)

- Window size: 10s
- Step size: 10s (non-overlapping)
- Use direct counts per window

### Option B (Smoother and better)

- Window size: 10s
- Step size: 5s (overlapping updates)
- Apply smoothing before sending to SUMO:

`final_count = 0.7 * current_window + 0.3 * previous_window`

Why Option B is better:

- Reduces sudden jumps caused by detection noise
- Gives more realistic adaptive signal behavior
- Looks more stable in live demo

If time is short, use Option A first, then move to Option B.

---

## 6. Handling Different Video Lengths (12s, 30s, 1min)

You mentioned mixed video lengths. For a 2-minute demo:

- Use circular playback for each road video
- Process all inputs in synchronized 10-second slots

Example:

- Road A video length 12s -> loops frequently
- Road B video length 30s -> loops less frequently
- Road C video length 60s -> loops even less
- Road D video length 10s or 12s -> loops frequently

Looping is fine for demo, but mention in presentation that real deployment would use live camera feeds.

---

## 7. 2-Minute Demo Timeline

Total demo = 120 seconds

- Use 12 control slots of 10 seconds each
- In each slot:
	- Read 10s segment from all 4 videos
	- ROI-based vehicle counting
	- Update incoming demand in SUMO
	- Compute/update green timing for next slot

This gives clear adaptive behavior and easy explanation to judges.

---

## 8. Data Contract Between Detection and SUMO

For each 10-second slot, send one record per approach:

- `approach_id`: north/east/south/west
- `slot_start_time`, `slot_end_time`
- `car_count`, `bus_count`, `truck_count`, `motorcycle_count`
- `total_count`

SUMO side converts counts to inserted vehicles over next slot.

Optional but recommended:

- Add `confidence_score` or `quality_flag` if detection quality is poor in a slot

---

## 9. SUMO Responsibilities

SUMO will provide:

- Real movement and queue formation
- Lane behavior and turn behavior
- Signal phase execution
- Metrics for evaluation

Your controller will provide:

- Green phase duration and phase order decisions based on recent counts

---

## 10. ROI Guidelines (Critical)

For each camera:

- Draw ROI only on incoming lanes before stop line
- Keep ROI fixed for demo
- Avoid counting vehicles already inside junction
- Exclude pedestrians and side roads if visible

Validation checklist:

- Manually verify first 3 windows for each camera
- Confirm counted vehicles are only approaching intersection

---

## 11. Practical Risks and Mitigation

Risk: Same vehicle counted multiple times in a 10s window

- Mitigation: lightweight tracking + unique IDs per window

Risk: Sudden false detections cause unstable signal timings

- Mitigation: smoothing or min/max clamp on green time

Risk: Video desynchronization

- Mitigation: align all roads to slot boundaries (0-10s, 10-20s, ...)

---

## 12. Final Recommended Demo Configuration

For your current stage, use this:

- 4 videos mapped to 4 incoming roads
- 10-second slots
- ROI-based incoming-only counting
- Circular video playback
- Adaptive green timing with min/max bounds
- Optional smoothing (recommended if available)

This is simple, explainable, and strong for a 2-minute demo.

---

## 13. What Not to Change Now

To keep scope controlled:

- Do not redesign full detection model
- Do not build complex city-scale network
- Do not over-optimize turn prediction in first demo

Focus on:

- Correct ROI counts
- Stable slot-based control
- Clear SUMO visualization of adaptive behavior

---

## 14. Next Steps (Implementation Order)

1. Build/import a 4-way SUMO intersection network
2. Define 4 incoming approaches and routes
3. Add ROI definitions for each road video
4. Implement 10s slot counting pipeline
5. Connect slot counts to SUMO vehicle injection
6. Connect adaptive signal timing to SUMO traffic light phases
7. Run 120s demo and collect metrics

---

Prepared for project: Adaptive Traffic Signal Timer -> SUMO migration.
