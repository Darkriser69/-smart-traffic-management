"""
Milestone-2 bridge: Replay slot-based demand into SUMO.

Reads slot JSON produced by slot_count_pipeline.py and injects vehicles
into a simple 4-way SUMO intersection.
"""

import argparse
import json
import math
import os
import random
import shutil
import time
from pathlib import Path

import traci
from PIL import Image, ImageDraw, ImageFont

# For traffic light visualization
TRAFFIC_LIGHT_POSITIONS = {
    # Tune these one-by-one if any light is too far from the junction.
    "north": (280, 330),
    "south": (320, 275),
    "east": (320, 330),
    "west": (280, 275),
}

# Compact traffic light UI (smaller overall size)
LIGHT_RADIUS = 3
LIGHT_SPACING = 6

TL_BG_HALF_WIDTH = 6
TL_BG_BOTTOM_OFFSET = 14
TL_BG_TOP_OFFSET = 12

LABEL_Y_OFFSET = 14
TIMER_Y_OFFSET = 10

LABEL_IMAGE_SIZE = (70, 18)
TIMER_IMAGE_SIZE = (40, 16)

LABEL_IMAGE_SCALE = (7, 2.5)
TIMER_IMAGE_SCALE = (3.8, 1.8)

# Top-left cycle summary box (you can tune manually later)
CYCLE_PANEL_POSITION = (250, 340)
CYCLE_PANEL_IMAGE_SIZE = (310, 128)
CYCLE_PANEL_SCALE = (36, 13)
CYCLE_PANEL_Y_OFFSET = 0

COLOR_RED = (255, 0, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_INACTIVE = (80, 80, 80)
COLOR_BACKGROUND = (30, 30, 30)

# Track current traffic light state and timers
TRAFFIC_LIGHT_STATE = {
    "north": {"state": "inactive", "remaining": 0},
    "south": {"state": "inactive", "remaining": 0},
    "east": {"state": "inactive", "remaining": 0},
    "west": {"state": "inactive", "remaining": 0},
}


BASE_DIR = Path(__file__).resolve().parent
SUMO_DIR = BASE_DIR / "sumo"
DEFAULT_SUMO_CFG = SUMO_DIR / "intersection.sumocfg"
DEFAULT_SLOT_OUTPUT_DIR = BASE_DIR / "slot_outputs"
DEFAULT_GUI_SETTINGS = SUMO_DIR / "clear_view.settings.xml"
GUI_ASSET_DIR = BASE_DIR / "generated_gui_assets"
GUI_ASSET_DIR.mkdir(exist_ok=True)
TEXT_IMAGE_CACHE = {}

# Source edge per incoming road.
INCOMING = {
    "north": "n2c",
    "east": "e2c",
    "south": "s2c",
    "west": "w2c",
}

# Candidate outgoing edges per incoming road.
OUTGOING_CHOICES = {
    "north": ["c2s", "c2e", "c2w"],
    "east": ["c2w", "c2s", "c2n"],
    "south": ["c2n", "c2w", "c2e"],
    "west": ["c2e", "c2n", "c2s"],
}

# Demo turn distribution: straight, right, left (approximate).
TURN_WEIGHTS = [0.6, 0.2, 0.2]

VEHICLE_TYPE_MAP = {
    "car": "passenger",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "truck": "truck",
}

ROADS = ("north", "east", "south", "west")


def build_text_image(text, filename, background=(25, 25, 25, 230), text_color=(255, 255, 255, 255), size=(220, 56), font_size=22):
    cache_key = (filename, text, background, text_color, size, font_size)
    cached_path = TEXT_IMAGE_CACHE.get(cache_key)
    if cached_path and cached_path.exists():
        return cached_path

    image_path = GUI_ASSET_DIR / filename
    image = Image.new("RGBA", size, background)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = max(0, (size[0] - text_width) // 2)
    text_y = max(0, (size[1] - text_height) // 2 - 2)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=10, outline=(255, 255, 255, 80), width=2)
    draw.text((text_x, text_y), text, fill=text_color, font=font)
    image.save(image_path)
    TEXT_IMAGE_CACHE[cache_key] = image_path
    return image_path


def build_multiline_text_image(lines, filename, background=(20, 20, 20, 230), text_color=(245, 245, 245, 255), size=(320, 130), font_size=16):
    key_lines = tuple(lines)
    cache_key = (filename, key_lines, background, text_color, size, font_size)
    cached_path = TEXT_IMAGE_CACHE.get(cache_key)
    if cached_path and cached_path.exists():
        return cached_path

    image_path = GUI_ASSET_DIR / filename
    image = Image.new("RGBA", size, background)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=12, outline=(255, 255, 255, 90), width=2)

    y = 8
    for line in lines:
        draw.text((10, y), line, fill=text_color, font=font)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += max(18, (bbox[3] - bbox[1]) + 3)

    image.save(image_path)
    TEXT_IMAGE_CACHE[cache_key] = image_path
    return image_path


def update_cycle_summary_panel(green_alloc, cycle_remaining):
    panel_id = "cycle_summary_panel"
    panel_lines = [
        f"Cycle Remaining: {cycle_remaining}s / 120s",
        f"North: {int(green_alloc.get('north', 0))}s",
        f"East:  {int(green_alloc.get('east', 0))}s",
        f"South: {int(green_alloc.get('south', 0))}s",
        f"West:  {int(green_alloc.get('west', 0))}s",
    ]

    panel_image = build_multiline_text_image(
        panel_lines,
        f"cycle_panel_{cycle_remaining}_{int(green_alloc.get('north', 0))}_{int(green_alloc.get('east', 0))}_{int(green_alloc.get('south', 0))}_{int(green_alloc.get('west', 0))}.png",
        size=CYCLE_PANEL_IMAGE_SIZE,
        font_size=16,
    )

    px, py = CYCLE_PANEL_POSITION
    py = py + CYCLE_PANEL_Y_OFFSET

    if panel_id in traci.poi.getIDList():
        traci.poi.setPosition(panel_id, px, py)
        traci.poi.setImageFile(panel_id, str(panel_image))
    else:
        traci.poi.add(panel_id, px, py, (255, 255, 255), "cyclepanel", 98, str(panel_image), CYCLE_PANEL_SCALE[0], CYCLE_PANEL_SCALE[1])


def build_cycle_start_offsets(phase_plan):
    offsets = {}
    elapsed = 0
    for phase in phase_plan:
        offsets[phase["road"]] = elapsed
        elapsed += int(phase["allocated"])
    return offsets


def build_all_road_timers(phase_plan, cycle_elapsed, active_road, active_state, active_remaining):
    slot_cycle_seconds = max(1, sum(int(p["allocated"]) for p in phase_plan))
    offsets = build_cycle_start_offsets(phase_plan)

    timers = {}
    for road in ROADS:
        if road == active_road:
            timers[road] = max(0, int(active_remaining))
            continue

        road_start = offsets.get(road, 0)
        wait = (road_start - cycle_elapsed) % slot_cycle_seconds
        if wait == 0:
            wait = slot_cycle_seconds
        timers[road] = int(wait)

    return timers


def update_traffic_light_display(road, state, remaining_sec=0):
    """
    Update traffic light display for a single road with timer.
    Uses persistent polygon IDs to avoid recreation errors.
    """
    if road not in TRAFFIC_LIGHT_STATE:
        return
    
    x, y = TRAFFIC_LIGHT_POSITIONS[road]
    
    # Update state tracking
    TRAFFIC_LIGHT_STATE[road]["state"] = state
    TRAFFIC_LIGHT_STATE[road]["remaining"] = remaining_sec
    
    bg_id = f"tl_bg_{road}"
    bg_shape = (
        (x - TL_BG_HALF_WIDTH, y - TL_BG_BOTTOM_OFFSET),
        (x + TL_BG_HALF_WIDTH, y - TL_BG_BOTTOM_OFFSET),
        (x + TL_BG_HALF_WIDTH, y + TL_BG_TOP_OFFSET),
        (x - TL_BG_HALF_WIDTH, y + TL_BG_TOP_OFFSET),
    )
    if bg_id in traci.polygon.getIDList():
        traci.polygon.setShape(bg_id, bg_shape)
        traci.polygon.setColor(bg_id, COLOR_BACKGROUND)
    else:
        traci.polygon.add(bg_id, bg_shape, COLOR_BACKGROUND, True, "trafficlight", 80, 1)

    # Draw road label above the light as an image so SUMO can render it reliably
    label_id = f"label_{road}"
    label_image = build_text_image(
        road.upper(),
        f"label_{road}.png",
        background=(20, 20, 20, 230),
        text_color=(245, 245, 245, 255),
        size=LABEL_IMAGE_SIZE,
        font_size=20,
    )
    if label_id in traci.poi.getIDList():
        traci.poi.setPosition(label_id, x, y + LABEL_Y_OFFSET)
        traci.poi.setImageFile(label_id, str(label_image))
    else:
        traci.poi.add(label_id, x, y + LABEL_Y_OFFSET, (255, 255, 255), "trafficlabel", 90, str(label_image), LABEL_IMAGE_SCALE[0], LABEL_IMAGE_SCALE[1])

    # Draw countdown timer above the light as an image so the seconds are visible
    timer_id = f"timer_{road}"
    timer_text = f"{remaining_sec}s" if remaining_sec > 0 else "--"
    timer_image = build_text_image(
        timer_text,
        f"timer_{road}_{timer_text}.png",
        background=(35, 35, 35, 230),
        text_color=(255, 255, 120, 255),
        size=TIMER_IMAGE_SIZE,
        font_size=18,
    )
    if timer_id in traci.poi.getIDList():
        traci.poi.setPosition(timer_id, x, y + TIMER_Y_OFFSET)
        traci.poi.setImageFile(timer_id, str(timer_image))
    else:
        traci.poi.add(timer_id, x, y + TIMER_Y_OFFSET, (255, 255, 140), "trafficlabel", 95, str(timer_image), TIMER_IMAGE_SCALE[0], TIMER_IMAGE_SCALE[1])

    # Draw three lights: green, yellow, red
    lights_config = [
        ("green", COLOR_GREEN if state == "green" else COLOR_INACTIVE, y + LIGHT_SPACING),
        ("yellow", COLOR_YELLOW if state == "yellow" else COLOR_INACTIVE, y),
        ("red", COLOR_RED if state == "red" else COLOR_INACTIVE, y - LIGHT_SPACING),
    ]

    for light_name, color, light_y in lights_config:
        light_id = f"tl_{road}_{light_name}"
        radius = LIGHT_RADIUS
        points = []
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            points.append((x + radius * math.cos(rad), light_y + radius * math.sin(rad)))

        if light_id in traci.polygon.getIDList():
            traci.polygon.setShape(light_id, tuple(points))
            traci.polygon.setColor(light_id, color)
        else:
            traci.polygon.add(light_id, tuple(points), color, True, "trafficlight", 100, 1)


def update_all_traffic_lights(state_map, timers_map=None):
    """
    Update all traffic lights with their state and timers.
    state_map: dict with road -> 'red'|'yellow'|'green'|'inactive'
    timers_map: dict with road -> remaining_seconds (optional)
    """
    if timers_map is None:
        timers_map = {}
    
    for road in ROADS:
        state = state_map.get(road, "inactive")
        remaining = timers_map.get(road, 0)
        update_traffic_light_display(road, state, remaining)


def parse_args():
    parser = argparse.ArgumentParser(description="Replay slot demand into SUMO")
    parser.add_argument("--slot-json", type=str, default=None, help="Path to slot_counts_*.json")
    parser.add_argument("--sumocfg", type=str, default=str(DEFAULT_SUMO_CFG), help="Path to .sumocfg")
    parser.add_argument("--gui", action="store_true", help="Run with sumo-gui")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--yellow-seconds", type=int, default=2, help="Yellow duration before slot end")
    parser.add_argument("--max-slots", type=int, default=0, help="Optional cap for quick tests (0 = all slots)")
    parser.add_argument("--step-delay", type=float, default=0.2, help="GUI delay per simulation step in seconds")
    parser.add_argument("--zoom", type=float, default=900.0, help="SUMO GUI zoom for better visibility")
    parser.add_argument("--schema", type=str, default="clear_view", help="SUMO GUI schema (for example: clear_view, standard, real world)")
    parser.add_argument(
        "--gui-settings-file",
        type=str,
        default=str(DEFAULT_GUI_SETTINGS),
        help="SUMO GUI settings XML for stable visual styling",
    )
    parser.add_argument(
        "--software-render",
        action="store_true",
        default=True,
        help="Force software OpenGL for SUMO GUI (reduces stripe artifacts on some GPUs)",
    )
    parser.add_argument(
        "--hardware-render",
        dest="software_render",
        action="store_false",
        help="Use hardware OpenGL rendering",
    )
    parser.add_argument(
        "--no-internal-links",
        action="store_true",
        default=True,
        help="Disable internal junction links for cleaner visualization (default: enabled)",
    )
    parser.add_argument(
        "--with-internal-links",
        dest="no_internal_links",
        action="store_false",
        help="Keep internal links (advanced, less clear visuals)",
    )
    return parser.parse_args()


def resolve_sumo_binary(use_gui):
    exe_name = "sumo-gui" if use_gui else "sumo"

    found = shutil.which(exe_name)
    if found:
        return found

    sumo_home = (
        Path(str(Path.home()))  # fallback placeholder path object only
    )
    # Prefer process env, then user/machine env on Windows.
    env_value = None
    try:
        import os

        env_value = os.environ.get("SUMO_HOME")
        if not env_value:
            import winreg  # type: ignore

            def read_reg(root, subkey, value_name):
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        return winreg.QueryValueEx(key, value_name)[0]
                except OSError:
                    return None

            env_value = read_reg(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                "SUMO_HOME",
            ) or read_reg(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                "SUMO_HOME",
            )
    except Exception:
        env_value = None

    if env_value:
        sumo_home = Path(env_value)
        candidate = sumo_home / "bin" / f"{exe_name}.exe"
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        f"Could not find '{exe_name}'. Add SUMO bin to PATH or set SUMO_HOME correctly."
    )


def latest_slot_json(slot_output_dir):
    files = sorted(slot_output_dir.glob("slot_counts_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(
            f"No slot JSON files found in: {slot_output_dir}. Run slot_count_pipeline.py first."
        )
    return files[-1]


def load_slots(slot_json_path):
    with open(slot_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    slots = data.get("slots", [])
    if not slots:
        raise ValueError("Slot JSON has no slots")
    return data, slots


def ensure_route(route_id, from_edge, to_edge):
    if route_id in traci.route.getIDList():
        return
    traci.route.add(route_id, [from_edge, to_edge])


def schedule_counts(total_count, slot_seconds):
    if total_count <= 0:
        return []
    slot_seconds = max(1, int(slot_seconds))

    # Evenly spread with random jitter to avoid burst insertion at one second.
    per_sec = [0 for _ in range(slot_seconds)]
    for i in range(total_count):
        idx = int((i / total_count) * slot_seconds)
        idx = min(slot_seconds - 1, idx)
        per_sec[idx] += 1

    # Tiny shuffle to make the stream less deterministic while preserving totals.
    if slot_seconds > 1:
        for _ in range(slot_seconds // 3):
            a = random.randint(0, slot_seconds - 1)
            b = random.randint(0, slot_seconds - 1)
            per_sec[a], per_sec[b] = per_sec[b], per_sec[a]

    return per_sec


def pick_vehicle_label(counts):
    labels = [k for k in ("car", "motorcycle", "bus", "truck") if counts.get(k, 0) > 0]
    if not labels:
        return "car"

    weights = [max(1, int(counts[k])) for k in labels]
    return random.choices(labels, weights=weights, k=1)[0]


def maybe_set_green_hint(slot):
    # Milestone-2 logs green split for traceability.
    # Direct per-phase TLS control is completed in Milestone-3.
    greens = slot.get("green_allocation_sec", {})
    print(
        "  Green hint N/E/S/W = "
        f"{greens.get('north', 0)}/{greens.get('east', 0)}/{greens.get('south', 0)}/{greens.get('west', 0)}"
    )


def get_link_groups(tls_id):
    groups = {road: set() for road in ROADS}
    controlled = traci.trafficlight.getControlledLinks(tls_id)

    for idx, links in enumerate(controlled):
        if not links:
            continue
        # links is a list of tuples: (fromLane, toLane, viaLane)
        from_lane = links[0][0]
        if from_lane.startswith("n2c_"):
            groups["north"].add(idx)
        elif from_lane.startswith("e2c_"):
            groups["east"].add(idx)
        elif from_lane.startswith("s2c_"):
            groups["south"].add(idx)
        elif from_lane.startswith("w2c_"):
            groups["west"].add(idx)

    return {k: tuple(sorted(v)) for k, v in groups.items()}


def build_tls_state(active_road, signal_char, state_len, link_groups):
    state = ["r"] * state_len
    for idx in link_groups.get(active_road, ()):  # dynamic indices from SUMO network
        state[idx] = signal_char
    return "".join(state)


def get_tls_id():
    tls_ids = traci.trafficlight.getIDList()
    if not tls_ids:
        raise RuntimeError("No traffic lights found in SUMO network")
    return tls_ids[0]


def setup_gui_view(enabled, zoom, schema):
    if not enabled:
        return
    try:
        # Keep the intersection centered and zoomed for demo visibility.
        traci.gui.setOffset("View #0", 300.0, 300.0)
        traci.gui.setZoom("View #0", zoom)
        if schema:
            traci.gui.setSchema("View #0", schema)
    except traci.TraCIException:
        pass


def build_phase_plan(slot, yellow_seconds):
    greens = slot.get("green_allocation_sec", {})
    phase_plan = []

    for road in ROADS:
        allocated = int(greens.get(road, 0))
        if allocated <= 0:
            continue

        road_yellow = max(0, min(yellow_seconds, allocated - 1 if allocated > 1 else 0))
        road_green = max(1, allocated - road_yellow)
        phase_plan.append(
            {
                "road": road,
                "allocated": allocated,
                "green": road_green,
                "yellow": road_yellow,
            }
        )

    return phase_plan


def run_replay(
    slot_json_path,
    sumocfg_path,
    use_gui,
    seed,
    yellow_seconds,
    max_slots,
    step_delay,
    zoom,
    schema,
    gui_settings_file,
    no_internal_links,
    software_render,
):
    random.seed(seed)

    _, slots = load_slots(slot_json_path)

    if use_gui and software_render:
        os.environ["QT_OPENGL"] = "software"

    binary = resolve_sumo_binary(use_gui)
    cmd = [binary, "-c", str(sumocfg_path), "--start"]
    if use_gui and gui_settings_file:
        gfile = Path(gui_settings_file)
        if gfile.exists():
            cmd.extend(["-g", str(gfile)])
    if no_internal_links:
        cmd.extend(["--no-internal-links", "true"])
    traci.start(cmd)

    sim_time = 0
    veh_counter = 0
    try:
        tls_id = get_tls_id()
        state_len = len(traci.trafficlight.getRedYellowGreenState(tls_id))
        link_groups = get_link_groups(tls_id)
        setup_gui_view(use_gui, zoom, schema)
        
        # Initialize all traffic lights to inactive (gray) state
        initial_state_map = {road: "inactive" for road in ROADS}
        if max_slots > 0:
            slots = slots[:max_slots]
        
        # Initialize traffic lights on first step
        initial_timers = {road: 0 for road in ROADS}
        update_all_traffic_lights(initial_state_map, initial_timers)

        for slot in slots:
            slot_index = int(slot.get("slot_index", 0))
            slot_start = int(slot.get("slot_start_sec", 0))
            slot_end = int(slot.get("slot_end_sec", slot_start + 10))
            counts_by_road = slot.get("counts", {})
            phase_plan = build_phase_plan(slot, yellow_seconds)

            if not phase_plan:
                continue

            slot_cycle_seconds = sum(phase["allocated"] for phase in phase_plan)

            print(f"Slot {slot_index:02d} [{slot_start}-{slot_end}s]")
            maybe_set_green_hint(slot)
            print(f"  Slot cycle length from green hints: {slot_cycle_seconds}s")
            cycle_elapsed = 0
            green_alloc = slot.get("green_allocation_sec", {})

            # Build per-second schedule for each road.
            road_schedule = {}
            for road in ROADS:
                road_counts = counts_by_road.get(road, {})
                total = int(road_counts.get("total", 0))
                phase = next((p for p in phase_plan if p["road"] == road), None)
                green_secs = phase["green"] if phase else 1
                road_schedule[road] = {
                    "per_sec": schedule_counts(total, green_secs),
                    "counts": road_counts,
                }

            for phase in phase_plan:
                active_road = phase["road"]
                green_secs = phase["green"]
                yellow_secs = phase["yellow"]

                print(
                    f"  Active road: {active_road} | green={green_secs}s yellow={yellow_secs}s"
                )

                green_state = build_tls_state(active_road, "G", state_len, link_groups)
                yellow_state = build_tls_state(active_road, "y", state_len, link_groups)

                for sec_idx in range(green_secs):
                    traci.trafficlight.setRedYellowGreenState(tls_id, green_state)
                    # Calculate remaining time in this phase
                    remaining_in_phase = green_secs - sec_idx
                    timers = build_all_road_timers(
                        phase_plan=phase_plan,
                        cycle_elapsed=cycle_elapsed,
                        active_road=active_road,
                        active_state="green",
                        active_remaining=remaining_in_phase,
                    )
                    
                    # Update traffic light visualization with timer
                    state_map = {road: "red" if road != active_road else "green" for road in ROADS}
                    update_all_traffic_lights(state_map, timers)
                    cycle_remaining = slot_cycle_seconds - (cycle_elapsed % slot_cycle_seconds)
                    update_cycle_summary_panel(green_alloc, cycle_remaining)

                    to_add = road_schedule[active_road]["per_sec"][sec_idx]
                    if to_add <= 0:
                        traci.simulationStep()
                        sim_time += 1
                        if use_gui and step_delay > 0:
                            time.sleep(step_delay)

                        continue

                    in_edge = INCOMING[active_road]
                    out_edges = OUTGOING_CHOICES[active_road]

                    for _ in range(to_add):
                        out_edge = random.choices(out_edges, weights=TURN_WEIGHTS, k=1)[0]
                        route_id = f"r_{in_edge}_{out_edge}"
                        ensure_route(route_id, in_edge, out_edge)

                        label = pick_vehicle_label(road_schedule[active_road]["counts"])
                        vclass = VEHICLE_TYPE_MAP.get(label, "passenger")

                        veh_id = f"v_{slot_index}_{active_road}_{veh_counter}"
                        veh_counter += 1

                        try:
                            traci.vehicle.add(
                                vehID=veh_id,
                                routeID=route_id,
                                typeID=vclass,
                                depart=str(sim_time),
                            )
                        except traci.TraCIException:
                            # Ignore occasional insertion conflicts; keep simulation running.
                            pass

                    traci.simulationStep()
                    sim_time += 1
                    cycle_elapsed += 1
                    if use_gui and step_delay > 0:
                        time.sleep(step_delay)

                for _ in range(yellow_secs):
                    traci.trafficlight.setRedYellowGreenState(tls_id, yellow_state)
                    # Update with yellow state and timer
                    state_map = {road: "red" if road != active_road else "yellow" for road in ROADS}
                    timers = build_all_road_timers(
                        phase_plan=phase_plan,
                        cycle_elapsed=cycle_elapsed,
                        active_road=active_road,
                        active_state="yellow",
                        active_remaining=1,
                    )
                    update_all_traffic_lights(state_map, timers)
                    cycle_remaining = slot_cycle_seconds - (cycle_elapsed % slot_cycle_seconds)
                    update_cycle_summary_panel(green_alloc, cycle_remaining)
                    
                    traci.simulationStep()
                    sim_time += 1
                    cycle_elapsed += 1
                    if use_gui and step_delay > 0:
                        time.sleep(step_delay)

        # Drain some extra steps so last inserted vehicles can move out.
        for _ in range(30):
            state_map = {road: "red" for road in ROADS}
            timers = {road: 0 for road in ROADS}
            update_all_traffic_lights(state_map, timers)
            traci.simulationStep()
            if use_gui and step_delay > 0:
                time.sleep(step_delay)

        print("\nMilestone-3 replay completed.")
        print(f"Simulated seconds: {sim_time}")
        print(f"Vehicles attempted: {veh_counter}")

    except KeyboardInterrupt:
        print("\nInterrupted by user. Closing SUMO gracefully.")
    finally:
        try:
            # wait=False avoids long blocking waits on GUI close.
            traci.close(wait=False)
        except Exception:
            pass


def main():
    args = parse_args()

    slot_json_path = Path(args.slot_json) if args.slot_json else latest_slot_json(DEFAULT_SLOT_OUTPUT_DIR)
    sumocfg_path = Path(args.sumocfg)

    if not sumocfg_path.exists():
        raise FileNotFoundError(
            f"Missing SUMO config: {sumocfg_path}. Build network first using sumo/build_network.ps1"
        )

    run_replay(
        slot_json_path=slot_json_path,
        sumocfg_path=sumocfg_path,
        use_gui=args.gui,
        seed=args.seed,
        yellow_seconds=args.yellow_seconds,
        max_slots=args.max_slots,
        step_delay=args.step_delay,
        zoom=args.zoom,
        schema=args.schema,
        gui_settings_file=args.gui_settings_file,
        no_internal_links=args.no_internal_links,
        software_render=args.software_render,
    )


if __name__ == "__main__":
    main()
