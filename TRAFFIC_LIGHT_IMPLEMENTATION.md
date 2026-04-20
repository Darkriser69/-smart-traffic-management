# Traffic Light Implementation Guide

## Overview

The traffic light visualization system has been added to the SUMO simulation. Each intersection now displays:

1. **Visual Traffic Lights** - Three colored circles (Red, Yellow, Green) for each road
2. **Road Labels** - Clear identification (NORTH, SOUTH, EAST, WEST)
3. **Traffic Signal Sequence** - Yellow → Green → Red based on slot timing
4. **Realistic Vehicle Speeds** - Slower acceleration (5 sec startup instead of 2 sec)

## Changes Made

### 1. **Vehicle Speeds Updated** - `sumo/empty.rou.xml`

```xml
<!-- OLD (too fast) -->
<vType id="passenger" accel="2.6" ... />  <!-- 6.4s to max speed -->

<!-- NEW (more realistic) -->
<vType id="passenger" accel="1.3" ... />  <!-- 12.8s to max speed -->
```

**Vehicle Type Changes:**
- **Passenger**: accel 2.6 → 1.3 (realistic city driving)
- **Motorcycle**: accel 3.0 → 1.5
- **Bus**: accel 1.2 → 0.8
- **Truck**: accel 1.0 → 0.7

### 2. **Traffic Light Visualization** - `sumo_slot_bridge.py`

#### New Configuration Constants

```python
TRAFFIC_LIGHT_POSITIONS = {
    "north": (-50, 130),   # Above intersection
    "south": (-50, -130),  # Below intersection
    "east": (140, -50),    # Right of intersection
    "west": (-140, -50),   # Left of intersection
}
```

#### Visual Design

```
Each Traffic Light Shows:
┌─────────────┐
│   GREEN ●   │  ← Top light (green when active)
│  YELLOW ●   │  ← Middle light (yellow when transitioning)
│    RED ●    │  ← Bottom light (red when no access)
│  NORTH      │  ← Road label (all caps)
└─────────────┘

Color Scheme:
- Gray/Dark Background: Invisible on roads, visible on white
- Green: RGB(0, 255, 0) - Active green phase
- Yellow: RGB(255, 255, 0) - Transition phase
- Red: RGB(255, 0, 0) - Stop/inactive phase
- Inactive: RGB(100, 100, 100) - Gray (standby)
```

#### Key Functions

**`draw_traffic_light(road, state, layer_id)`**
- Draws a single traffic light with three circles
- States: 'red', 'yellow', 'green', or 'inactive'
- Includes road label above the light
- Uses SUMO's polygon drawing API

**`draw_all_traffic_lights(state_map, layer_id)`**
- Updates all four road traffic lights
- `state_map`: dict mapping road → current state
- Called every simulation step

### 3. **Simulation Loop Updates**

Traffic lights are drawn during each simulation phase:

```python
# Green phase - active road shows green
state_map[active_road] = "green"
draw_all_traffic_lights(state_map, sim_time)

# Yellow phase - active road shows yellow
state_map[active_road] = "yellow"
draw_all_traffic_lights(state_map, sim_time)

# Drain phase - all roads show red
state_map = {road: "red" for road in ROADS}
draw_all_traffic_lights(state_map, sim_time)
```

## How It Works

### Timing Based on Slot Generation

1. **Slot Period**: Each 10-second slot contains adaptive traffic timing
2. **Phase Plan**: Built from `green_allocation_sec` in slot data
3. **Sequence per Road**: 
   - Yellow phase: 0-2 seconds (warning)
   - Green phase: Allocated seconds
   - Red phase: Waiting for next green

### Example Timeline (Slot with NESW timing)

```
Time: 0-3s    Road: NORTH  | Traffic Light: ● GREEN  (3 sec slot)
Time: 3-4s    Road: NORTH  | Traffic Light: ● YELLOW (1 sec to stop)
Time: 4-7s    Road: EAST   | Traffic Light: ● GREEN  (3 sec slot)
Time: 7-8s    Road: EAST   | Traffic Light: ● YELLOW (1 sec to stop)
Time: 8-11s   Road: SOUTH  | Traffic Light: ● GREEN  (3 sec slot)
... (continues for WEST) ...
```

## Visual Layout in SUMO GUI

```
                    ┌─────────────┐
                    │   NORTH     │
                    │   GREEN ●   │
                    │  YELLOW ●   │
                    │    RED ●    │
                    └─────────────┘
                          │
                          ↓ (traffic flows down)
           ╔═════════════════════════╗
   ┌──────┐║   INTERSECTION          ║ ┌──────┐
   │WEST  ║║      (4-way)            ║║ EAST │
   │      ║║                          ║║      │
   │LIGHTS║╚═════════════════════════╝║LIGHTS│
   └──────┘                            └──────┘
                          ↑
                          │
                    ┌─────────────┐
                    │    SOUTH    │
                    │   GREEN ●   │
                    │  YELLOW ●   │
                    │    RED ●    │
                    └─────────────┘

Key Features:
✓ No overlaps with roads
✓ Dark background visible on white GUI
✓ Clear gray/black inactive state
✓ Road labels above each light
✓ Three lights: two inactive, one active
```

## Running the Simulation

### Standard Run with Traffic Lights

```powershell
cd Code\YOLO\darkflow
python .\sumo_slot_bridge.py --gui --step-delay 0.3 --zoom 1200 --schema clear_view --software-render --no-internal-links
```

### Custom Yellow Duration

```powershell
python .\sumo_slot_bridge.py --gui --yellow-seconds 3 --step-delay 0.3 --zoom 1200
```

### Test with Limited Slots

```powershell
python .\sumo_slot_bridge.py --gui --max-slots 2 --step-delay 0.3 --zoom 1200
```

## Customization

### Adjust Traffic Light Position

Edit `TRAFFIC_LIGHT_POSITIONS` in `sumo_slot_bridge.py`:

```python
TRAFFIC_LIGHT_POSITIONS = {
    "north": (-50, 130),   # (x, y) coordinates
    "south": (-50, -130),
    "east": (140, -50),
    "west": (-140, -50),
}
```

### Adjust Light Size

Edit constants in `sumo_slot_bridge.py`:

```python
LIGHT_RADIUS = 8      # Circle diameter
LIGHT_SPACING = 20    # Distance between circles
```

### Change Colors

```python
COLOR_RED = (255, 0, 0)        # Traffic red
COLOR_YELLOW = (255, 255, 0)   # Warning yellow
COLOR_GREEN = (0, 255, 0)      # Go green
COLOR_INACTIVE = (100, 100, 100)  # Standby gray
COLOR_BACKGROUND = (40, 40, 40)   # Dark background
```

### Adjust Vehicle Speed/Acceleration

Edit `sumo/empty.rou.xml`:

```xml
<!-- Slower -->
<vType id="passenger" accel="1.0" ... />  <!-- ~15 seconds to max -->

<!-- Faster -->
<vType id="passenger" accel="2.0" ... />  <!-- ~8 seconds to max -->
```

## Troubleshooting

### Traffic Lights Not Visible

1. Check SUMO GUI zoom level (recommend 1200 for good visibility)
2. Ensure `--software-render` flag is used
3. Try adjusting `TRAFFIC_LIGHT_POSITIONS` coordinates

### Lights Overlapping Roads

1. Adjust `TRAFFIC_LIGHT_POSITIONS` to move further from center
2. Increase `LIGHT_RADIUS` sparingly

### Road Labels Not Showing

1. POI rendering depends on SUMO GUI settings
2. Try different `--schema` option (clear_view, standard, etc.)
3. Verify zoom level (too small POIs won't render)

### Simulation Runs Too Fast/Slow

Adjust `--step-delay` parameter:
- `0.1`: Fast (realistic speed playback)
- `0.3`: Moderate (default)
- `0.5`: Slow (detailed observation)

## Performance Notes

1. **Polygon Drawing**: Each traffic light draws ~5 polygons per step (minimal impact)
2. **Memory**: Traffic light layer is recreated each step (not accumulated)
3. **GUI Rendering**: Using `--software-render` may reduce GPU strain

## Next Steps / Future Improvements

1. **Custom Timing Display**: Show remaining seconds for current phase
2. **Sound Effects**: Add horn/beep sounds on phase changes
3. **Pedestrian Crossings**: Add walk/don't walk signals
4. **Queue Length Display**: Show vehicle queue above each road
5. **Statistics Panel**: Display throughput and congestion metrics

## File Locations

- Main Script: `Code/YOLO/darkflow/sumo_slot_bridge.py`
- Vehicle Types: `Code/YOLO/darkflow/sumo/empty.rou.xml`
- Documentation: `Code/YOLO/darkflow/PROJECT_WORKFLOW_DOCUMENTATION.md`
- SUMO Network: `Code/YOLO/darkflow/sumo/intersection.net.xml`
