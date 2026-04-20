# IEEE Research Paper README
## Adaptive Traffic Signal Control Using YOLOv8, ROI-Based Traffic Demand Estimation, and SUMO Replay

This file is a publication-oriented writing guide for your project.
It gives:
- Required IEEE paper fields (checklist)
- What to write in each field (point-wise)
- A detailed methodology section aligned with your implementation
- Flowchart guidance (what figures are needed and where)

---

## 1) IEEE Paper Fields Checklist (Use This Order)

1. Title
2. Authors and Affiliations
3. Abstract
4. Keywords
5. Introduction
6. Related Work / Literature Review
7. Problem Statement and Research Gap
8. Objectives and Contributions
9. System Overview / Architecture
10. Methodology (Detailed)
11. Experimental Setup
12. Evaluation Metrics
13. Results
14. Discussion
15. Limitations
16. Conclusion
17. Future Work
18. Acknowledgment (optional)
19. References (IEEE format)

---

## 2) Section-by-Section Writing Guide (Point-Wise)

## 2.1 Title
- Keep title specific to method + application domain.
- Mention core techniques: YOLOv8, adaptive signal timing, SUMO.
- Keep concise and technical.

Suggested options:
- "Video-Driven Adaptive Traffic Signal Control Using YOLOv8 and SUMO-Based Replay"
- "ROI-Based Vehicle Demand Estimation for Adaptive Traffic Light Timing in Urban Intersections"

## 2.2 Authors and Affiliations
- Full author names.
- Department/Institute.
- Email IDs.
- Mark corresponding author.

## 2.3 Abstract (Structured, 150–250 words)
Include these points in one compact paragraph:
- Background: Fixed-time signals are not responsive to real-time traffic.
- Problem: Need dynamic green-time allocation from observed traffic demand.
- Method: YOLOv8-based detection + ROI filtering + 10-second slot demand estimation + weighted green allocation + SUMO replay.
- Data source: Four road videos mapped to north/east/south/west approaches.
- Output: Slot-wise counts (car, bus, truck, motorcycle), green-time hints, and simulation behavior.
- Main finding statement: Adaptive allocation better reflects demand than static timing.
- Conclusion statement: Vision-guided control is feasible and scalable for smart-city intersections.

## 2.4 Keywords
Use 5–8 keywords:
- Adaptive Traffic Signal Control
- Intelligent Transportation Systems (ITS)
- YOLOv8
- Computer Vision
- SUMO
- Traffic Demand Estimation
- Real-Time Traffic Management
- ROI-Based Vehicle Counting

## 2.5 Introduction
Write in this order:
- Urban congestion challenges (delay, fuel loss, emissions, productivity impact).
- Limitation of fixed-cycle traffic lights.
- Opportunity from camera-based analytics and modern object detection.
- Why YOLOv8 is practical (speed + improved detection quality).
- Research motivation: convert video observations into operational signal timings.
- End with paper organization paragraph.

## 2.6 Related Work / Literature Review
Cover these groups:
- Classical fixed-time and actuated signal control approaches.
- CV-based vehicle detection (traditional ML, CNN/YOLO family).
- Simulation-driven traffic control studies using SUMO.
- Adaptive green allocation strategies (queue-based, demand-based, RL-based).

Then add your gap statement:
- Many works focus only on detection accuracy, not full deployment pipeline.
- Fewer studies show end-to-end flow from video detection to slot-based control replay in SUMO.

## 2.7 Problem Statement and Research Gap
- Existing intersections frequently use static schedules, insensitive to temporal demand shifts.
- Vehicle demand differs by approach and by short time windows.
- Real camera streams are noisy; signal control needs robust intermediate representation.
- Research gap: practical, reproducible pipeline connecting detection, demand aggregation, and adaptive timing.

## 2.8 Objectives and Contributions
State clear objectives:
- Build a video-driven traffic demand estimation pipeline for 4-way junctions.
- Estimate per-road, per-class demand using ROI-constrained counting.
- Allocate adaptive green times from weighted class demand under cycle constraints.
- Replay estimated demand and signal plans in SUMO for controlled analysis.

Claim contributions point-wise:
- End-to-end framework: Video -> Detection -> ROI Counts -> Slot Demand -> Green Split -> SUMO Replay.
- Practical slot aggregation method using max-over-samples strategy.
- Weighted demand model that accounts for heavier vehicle classes.
- Reproducible implementation with configurable timing bounds.

## 2.9 System Overview / Architecture
Describe modules:
- Module A: YOLOv8 vehicle detector (car, bus, truck, motorcycle).
- Module B: ROI-based filtering for incoming-lane relevance.
- Module C: Slot-wise aggregation (10-second windows, configurable sampling FPS).
- Module D: Green-time allocator with min/max constraints.
- Module E: SUMO/TraCI replay for demand injection and phase execution.

Recommended figure:
- "System Architecture Diagram" with arrows across all modules.

---

## 3) Methodology (Detailed, IEEE-ready)

## 3.1 Data Acquisition and Road Mapping
- Use four approach videos corresponding to north, east, south, and west roads.
- Define approach-wise ROI polygons to focus on incoming vehicles only.
- Ensure ROI setup is aligned with camera perspective and lane entry zones.

## 3.2 Vehicle Detection
- Use YOLOv8 model (e.g., yolov8n) for frame-level detection.
- Detect classes: car, bus, truck, motorcycle.
- Apply confidence threshold to remove low-confidence detections.
- Convert detections into structured records (label, confidence, bounding box).

## 3.3 ROI-Constrained Counting
- Compute each vehicle bounding-box center point.
- Apply point-in-polygon test to retain only detections inside road ROI.
- Produce per-frame class counts per approach.
- Ignore detections outside ROI to reduce irrelevant cross-road noise.

## 3.4 Temporal Slotting and Aggregation
- Partition timeline into fixed slots (default 10 seconds).
- Sample frames within each slot (configurable sample FPS).
- Aggregate sampled frame counts per class.
- Use "max-over-samples" per class within each slot to approximate peak visible demand.
- Generate slot-level totals and class-wise distributions per approach.

## 3.5 Demand Weighting Model
Use weighted demand score per road:
- car weight = 1.0
- motorcycle weight = 0.7
- bus weight = 2.5
- truck weight = 2.5

Weighted score per road:
- score = (car × 1.0) + (motorcycle × 0.7) + (bus × 2.5) + (truck × 2.5)

Rationale:
- Heavy vehicles represent larger road occupancy and clearance time.
- Weighted representation improves fairness versus plain total count.

## 3.6 Adaptive Green-Time Allocation
- Define cycle budget (e.g., 120 s).
- Enforce min-green and max-green bounds per road.
- Assign base minimum green to all roads.
- Distribute remaining cycle time proportionally to weighted demand scores.
- Handle fractional seconds by ranked remainder assignment.
- Rebalance to satisfy total cycle budget while respecting bounds.

## 3.7 SUMO Replay and Signal Execution
- Convert slot outputs into simulation demand input.
- Inject vehicles by road and class using TraCI.
- Map incoming edges and candidate outgoing turns.
- Apply per-slot phase plan: green interval + yellow interval per active road.
- Execute simulation step-by-step and log behavior.

## 3.8 Reproducibility and Configuration
Record and report:
- Model version and confidence threshold.
- Slot duration, sample FPS, cycle length.
- Min/max green limits.
- Simulation seed and GUI/no-GUI mode.
- Output artifacts (CSV/JSON slot files, simulation logs).

---

## 4) Experimental Setup

Include these points:
- Hardware details (CPU/GPU/RAM).
- Software stack (Python, OpenCV, Ultralytics, SUMO, TraCI).
- Video duration and scene conditions (time, density, camera angle).
- Number of evaluated slots.
- Baseline for comparison (fixed-time split).
- Number of repeated simulation runs (for stability).

---

## 5) Evaluation Metrics

Use both detection and control metrics:

Detection-side metrics:
- Per-class count consistency across sampled frames.
- Detection confidence distribution.

Traffic-control metrics:
- Average waiting time per vehicle.
- Queue length per approach.
- Throughput (vehicles cleared per cycle).
- Delay reduction (%) vs fixed-time baseline.
- Fairness of allocation across roads.

Optional system metrics:
- Inference time per frame.
- End-to-end slot processing latency.

---

## 6) Results (How to Present)

Add results in tables/figures:
- Table 1: Slot-wise per-road vehicle counts by class.
- Table 2: Weighted scores and allocated green times.
- Table 3: Baseline vs proposed method (delay, queue, throughput).
- Figure: Time-series plot of demand vs allocated green for each road.

Write result statements point-wise:
- Adaptive controller increased green share for high-demand approaches.
- Queue carryover reduced in high-load intervals.
- Throughput improved compared to static schedule.
- System remained bounded and stable due to min/max green constraints.

(Replace with your measured numbers during final submission.)

---

## 7) Discussion

Interpret outcomes:
- Why weighted demand improves practical control decisions.
- Cases where detector errors propagate to timing decisions.
- Sensitivity to ROI quality and camera perspective.
- Trade-off between responsiveness (short slots) and robustness (longer slots).

---

## 8) Limitations

Be transparent:
- Single-intersection focus.
- Dependence on camera quality and weather/lighting.
- No emergency vehicle priority in current setup.
- No pedestrian phase modeling.
- Approximate turn behavior in replay.

---

## 9) Conclusion

Conclusion points:
- Proposed and implemented a full video-to-signal adaptive pipeline.
- Demonstrated feasibility of YOLOv8 + ROI + weighted slot allocation.
- Validated operational behavior using SUMO replay.
- Showed pathway from perception outputs to traffic-control actions.

---

## 10) Future Work

- Multi-intersection corridor coordination.
- Real-time edge deployment with streaming cameras.
- Reinforcement learning or MPC for phase optimization.
- Integration of emergency vehicle and pedestrian prioritization.
- Domain adaptation for night/rain and diverse camera viewpoints.

---

## 11) Is a Flowchart Required? (Your Question)

Short answer: **Yes, strongly recommended for IEEE submission clarity.**

Where to include flowcharts/figures:
- Methodology section: mandatory pipeline flowchart.
- System overview: architecture block diagram.
- Experimental workflow: optional but useful.

Minimum recommended visuals:
1. End-to-end methodology flowchart.
2. Module architecture diagram.
3. Results chart (demand vs green allocation).

Example methodology flow (text form):
- Input Videos (N/E/S/W)
- ROI Definition
- YOLOv8 Detection
- ROI Vehicle Filtering
- Slot-wise Class Counting
- Weighted Demand Scoring
- Green-Time Allocation
- SUMO Demand Replay
- Performance Evaluation

---

## 12) Ready-to-Use Paper Skeleton (Copy into IEEE Template)

Use this exact heading flow in your manuscript:
- Abstract
- Keywords
- I. Introduction
- II. Related Work
- III. Problem Formulation and Contributions
- IV. Proposed Methodology
- V. Experimental Setup
- VI. Results and Discussion
- VII. Limitations
- VIII. Conclusion and Future Work
- Acknowledgment
- References

---

## 13) Final Submission Checklist (IEEE)

- Abstract length and clarity checked.
- Keywords are specific and searchable.
- Contributions are explicitly listed.
- Methodology has algorithm detail and parameter values.
- At least 2–3 clear figures included.
- Baseline comparison included.
- Limitations and future work included.
- References in IEEE citation format.
- Grammar and formatting reviewed against conference template.

---

If you want, the next step can be creating a **full first draft manuscript text** (ready to paste into IEEE Word/LaTeX template) based on this README.
