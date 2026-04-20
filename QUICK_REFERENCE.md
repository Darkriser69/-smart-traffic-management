# YOLOv8 Detection - Quick Reference Guide

## Quickest Start (0 Setup Required)

```bash
# Test with existing images
cd Code/YOLO/darkflow
python vehicle_detection.py

# Output: Images in output_images/ with vehicle counts printed
```

---

## Common Use Cases

### 1️⃣ Detect Vehicles in a Single Image

```python
import cv2
from yolov8_detect import YOLOv8VehicleDetector

detector = YOLOv8VehicleDetector('yolov8n.pt', confidence_threshold=0.5)

image = cv2.imread('street.jpg')
detections = detector.detect_vehicles(image, return_annotated=True)

# Get results
counts = detections['counts']
print(f"Cars: {counts['car']}, Buses: {counts['bus']}, Trucks: {counts['truck']}")

# Save annotated image
cv2.imwrite('output.jpg', detections['annotated_image'])
```

### 2️⃣ Process Video from Webcam

```python
from yolov8_integration_example import YOLOv8TrafficMonitor

monitor = YOLOv8TrafficMonitor()
monitor.process_video(video_source=0, display=True)
```

### 3️⃣ Get Vehicle Counts Only (Fast)

```python
from yolov8_detect import YOLOv8VehicleDetector

detector = YOLOv8VehicleDetector()
image = cv2.imread('image.jpg')

counts = detector.get_vehicle_count(image)
print(counts)  # {'car': 5, 'bus': 1, 'truck': 0, 'motorcycle': 2, 'total': 8}
```

### 4️⃣ Calculate Signal Green Time from Vehicle Counts

```python
from yolov8_integration_example import TrafficSignalController

controller = TrafficSignalController(num_lanes=2)

vehicle_counts = {'car': 5, 'bus': 1, 'truck': 0, 'motorcycle': 3, 'total': 9}
green_time = controller.calculate_green_time(vehicle_counts)

print(f"Recommended green time: {green_time} seconds")
```

### 5️⃣ Process Video File and Save Output

```python
from yolov8_integration_example import YOLOv8TrafficMonitor

monitor = YOLOv8TrafficMonitor(model_path='yolov8n.pt')
monitor.process_video(
    video_source='input.mp4',
    output_path='output.mp4',
    display=True
)
```

---

## CLI Commands

```bash
# Process webcam (real-time)
python yolov8_integration_example.py --video 0

# Process video file
python yolov8_integration_example.py --video traffic.mp4

# Save with annotations
python yolov8_integration_example.py --video 0 --output result.mp4

# Process without display
python yolov8_integration_example.py --video 0 --no-display

# Process directory of images
python yolov8_integration_example.py --mode images --input test_images/ --output detected_images/

# Use different model (faster)
python yolov8_integration_example.py --video 0 --model yolov8n.pt

# Use different model (more accurate)
python yolov8_integration_example.py --video 0 --model yolov8m.pt

# Adjust confidence threshold
python yolov8_integration_example.py --video 0 --confidence 0.6
```

---

## Return Value Structure

### detect_vehicles() Returns:
```python
{
    'vehicles': [
        {
            'label': 'car',
            'confidence': 0.92,
            'topleft': {'x': 100, 'y': 150},
            'bottomright': {'x': 250, 'y': 400}
        },
        # ... more vehicles
    ],
    'counts': {
        'car': 5,
        'bus': 1,
        'truck': 0,
        'motorcycle': 3,
        'total': 9
    },
    'annotated_image': numpy_array_with_bboxes
}
```

---

## Key Parameters

### YOLOv8VehicleDetector
```python
YOLOv8VehicleDetector(
    model_path='yolov8n.pt',           # Which model to use
    confidence_threshold=0.5            # Min confidence (0.0-1.0)
)
```

### detect_vehicles()
```python
detector.detect_vehicles(
    image,                              # CV2 image (BGR)
    return_annotated=False              # Include bounding box image?
)
```

### detect_from_video()
```python
detector.detect_from_video(
    video_path,                         # File path or camera index (0)
    output_path=None,                   # Save video with detections
    display=False,                      # Show real-time video
    frame_skip=1                        # Process every Nth frame (for speed)
)
```

---

## Model Sizes & Speed

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| **yolov8n** | 6.2 MB | ⚡⚡⚡ Fastest | Good | Real-time traffic |
| yolov8s | 22 MB | ⚡⚡ Fast | Better | Production |
| yolov8m | 49 MB | ⚡ Medium | Very Good | High accuracy |
| yolov8l | 84 MB | Slow | Excellent | Max accuracy |

**Default:** `yolov8n.pt` (good balance for traffic monitoring)

---

## Vehicle Classes Detected

✅ **Car** - Regular automobiles  
✅ **Bus** - Large public transport vehicles  
✅ **Truck** - Cargo/heavy vehicles  
✅ **Motorcycle** - Two-wheelers (bikes)  

The model auto-downloads on first use (~6.2 MB for nano).

---

## Integration with Simulation

The simulation (`simulation.py`) remains **unchanged**:
- Still generates vehicles randomly
- All signal timing logic works as-is
- Can optionally be enhanced with real detection

To use real detection in simulation, modify `setTime()` function to use detector output.

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| "No module named 'ultralytics'" | Already installed in your venv |
| Model download fails | Manual download: https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt |
| Slow on CPU | Use `yolov8n.pt` (nano) or increase `frame_skip` |
| High memory | Resize frames before detection: `cv2.resize(frame, (640, 480))` |
| Low FPS | Use `frame_skip=2` or `frame_skip=3` |

---

## Performance Tips

1. **For Real-time (30+ FPS):**
   ```python
   detector.detect_from_video(video, frame_skip=2)  # Process every 2nd frame
   ```

2. **For Accuracy:**
   ```python
   detector = YOLOv8VehicleDetector('yolov8m.pt')  # Use medium model
   ```

3. **For Video Output:**
   ```python
   detector.detect_from_video('input.mp4', output_path='output.mp4', frame_skip=1)
   ```

---

## Example: Complete Traffic Analysis

```python
from yolov8_detect import YOLOv8VehicleDetector
from yolov8_integration_example import TrafficSignalController
import cv2

# Setup
detector = YOLOv8VehicleDetector('yolov8n.pt', confidence_threshold=0.5)
controller = TrafficSignalController(num_lanes=2)

# Process camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Detect
    detections = detector.detect_vehicles(frame, return_annotated=True)
    counts = detections['counts']
    
    # Calculate signal time
    green_time = controller.calculate_green_time(counts)
    
    # Display
    result = detections['annotated_image']
    cv2.putText(result, f"Green: {green_time}s", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow('Traffic Monitor', result)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## Files Overview

| File | Purpose | Location |
|------|---------|----------|
| `yolov8_detect.py` | Core detection module | `Code/YOLO/` |
| `yolov8_integration_example.py` | Reference + CLI | `Code/YOLO/` |
| `vehicle_detection.py` | Image batch processing | `Code/YOLO/darkflow/` |
| `YOLOV8_UPGRADE_GUIDE.md` | Full documentation | Root directory |
| `yolov8n.pt` | Model (auto-downloaded) | `Code/YOLO/` or root |

---

## Version Info

- **YOLOv8 Version:** 8.4.12 (Ultralytics)
- **Model:** yolov8n.pt (Nano)
- **Python:** 3.11+
- **Framework:** PyTorch 2.10.0
- **OpenCV:** 4.13.0.92

---

**Last Updated:** February 8, 2026  
**Status:** ✅ Production Ready - All Tests Passing
