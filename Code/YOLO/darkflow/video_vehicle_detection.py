"""
Real-time Vehicle Detection on Video (YOLOv8)
=============================================
Plays videos/vid.mp4 and detects vehicles frame-by-frame with:
- Colored bounding boxes per vehicle type
- Confidence score on each detected vehicle

Press 'q' to quit the video window.
"""

import os
import cv2
from ultralytics import YOLO


# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BASE_DIR, "videos", "vid.mp4")

# Prefer local model in darkflow, fallback to parent YOLO model path
MODEL_CANDIDATES = [
    os.path.join(BASE_DIR, "yolov8n.pt"),
    os.path.join(BASE_DIR, "..", "yolov8n.pt"),
    "yolov8n.pt",
]


def resolve_model_path():
    for candidate in MODEL_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return "yolov8n.pt"


# COCO class IDs for vehicles
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# BGR colors for each vehicle type
VEHICLE_COLORS = {
    "car": (0, 255, 0),
    "motorcycle": (255, 0, 255),
    "bus": (0, 165, 255),
    "truck": (255, 0, 0),
}

# Keep display window within typical laptop screen size
MAX_DISPLAY_WIDTH = 1000
MAX_DISPLAY_HEIGHT = 1500


def resize_for_display(frame, max_width=MAX_DISPLAY_WIDTH, max_height=MAX_DISPLAY_HEIGHT):
    height, width = frame.shape[:2]
    scale = min(max_width / width, max_height / height, 1.0)
    if scale == 1.0:
        return frame
    new_width = int(width * scale)
    new_height = int(height * scale)
    return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)


def draw_detection(frame, x1, y1, x2, y2, vehicle_label, confidence):
    color = VEHICLE_COLORS.get(vehicle_label, (0, 255, 255))
    text = f"{vehicle_label} {confidence * 100:.1f}%"

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    text_width, text_height = text_size
    y_text = max(20, y1 - 8)

    cv2.rectangle(
        frame,
        (x1, y_text - text_height - 6),
        (x1 + text_width + 8, y_text),
        color,
        -1,
    )
    cv2.putText(
        frame,
        text,
        (x1 + 4, y_text - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def run_video_detection(video_path=VIDEO_PATH, confidence_threshold=0.30):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    model_path = resolve_model_path()
    print(f"Loading model: {model_path}")
    model = YOLO(model_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    cv2.namedWindow("Vehicle Detection - videos/vid.mp4", cv2.WINDOW_NORMAL)

    print(f"Playing video with detection: {video_path}")
    print("Press 'q' to quit.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            results = model(frame, conf=confidence_threshold, verbose=False)
            result = results[0]

            frame_counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}

            for box in result.boxes:
                class_id = int(box.cls)
                if class_id not in VEHICLE_CLASSES:
                    continue

                confidence = float(box.conf)
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                vehicle_label = VEHICLE_CLASSES[class_id]

                frame_counts[vehicle_label] += 1
                draw_detection(frame, x1, y1, x2, y2, vehicle_label, confidence)

            summary = (
                f"Car: {frame_counts['car']}  "
                f"Motorcycle: {frame_counts['motorcycle']}  "
                f"Bus: {frame_counts['bus']}  "
                f"Truck: {frame_counts['truck']}"
            )
            cv2.putText(
                frame,
                summary,
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            display_frame = resize_for_display(frame)
            cv2.imshow("Vehicle Detection - videos/vid.mp4", display_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_video_detection()
