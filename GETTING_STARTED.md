# Getting Started with YOLOv8

## 30-Second Quick Start

```bash
cd Code/YOLO/darkflow
python vehicle_detection.py
```

**That's it!** Check `output_images/` for results.

---

## What You Get

The script will:
1. ✅ Load YOLOv8 model (auto-downloads ~6.2 MB on first run)
2. ✅ Process all images in `test_images/`
3. ✅ Detect vehicles (cars, buses, trucks, motorcycles)
4. ✅ Draw bounding boxes on images
5. ✅ Save annotated images to `output_images/`
6. ✅ Print vehicle counts for each image

---

## What to Expect

### Console Output
```
Processing images from .../test_images/
Processing: 1.jpg
  Cars: 16, Buses: 2, Trucks: 0, Motorcycles: 0
  Output image stored at: .../output_images/output_1.jpg

Processing: 2.jpg
  Cars: 11, Buses: 0, Trucks: 0, Motorcycles: 0
  ...
Done!
```

### Output Files
```
output_images/
├── output_1.jpg  (with green bounding boxes around vehicles)
├── output_2.jpg
└── output_3.jpg
```

---

## Want to Monitor a Video?

```bash
cd Code/YOLO

# Webcam (camera index 0)
python yolov8_integration_example.py --video 0

# Video file
python yolov8_integration_example.py --video my_video.mp4

# Save with detections
python yolov8_integration_example.py --video my_video.mp4 --output result.mp4
```

---

## Want to Run the Simulation?
..\..\..\venv311\Scripts\Activate.ps1
```bash
cd Code/YOLO/darkflow
python simulation.py
```

This is the 2D traffic simulation - unchanged from before.

---

## Want to Use in Your Code?

### Example 1: Detect in an Image
```python
import cv2
from yolov8_detect import YOLOv8VehicleDetector

detector = YOLOv8VehicleDetector('yolov8n.pt')
image = cv2.imread('street.jpg')

detections = detector.detect_vehicles(image, return_annotated=True)

print(f"Cars: {detections['counts']['car']}")
print(f"Buses: {detections['counts']['bus']}")

cv2.imwrite('result.jpg', detections['annotated_image'])
```

### Example 2: Get Vehicle Counts Only
```python
from yolov8_detect import YOLOv8VehicleDetector
import cv2

detector = YOLOv8VehicleDetector('yolov8n.pt')
image = cv2.imread('street.jpg')

counts = detector.get_vehicle_count(image)
print(counts)  # {'car': 5, 'bus': 1, 'truck': 0, 'motorcycle': 2, 'total': 8}
```

### Example 3: Calculate Signal Green Time
```python
from yolov8_integration_example import TrafficSignalController

controller = TrafficSignalController(num_lanes=2)

vehicle_counts = {'car': 5, 'bus': 1, 'truck': 0, 'motorcycle': 3, 'total': 9}
green_time = controller.calculate_green_time(vehicle_counts)

print(f"Recommended green time: {green_time} seconds")
```

---

## Files & Locations

### Documentation
- 📖 **QUICK_REFERENCE.md** - Cheat sheet for developers
- 📖 **YOLOV8_UPGRADE_GUIDE.md** - Complete documentation
- 📖 **UPGRADE_SUMMARY.md** - What changed and why
- 📖 **VISUAL_SUMMARY.md** - Before/after comparison

### Code
- 🔍 **Code/YOLO/yolov8_detect.py** - Core detection module
- 🔗 **Code/YOLO/yolov8_integration_example.py** - Reference with CLI
- 🚗 **Code/YOLO/darkflow/vehicle_detection.py** - Image batch processing

### Data
- 📸 **Code/YOLO/darkflow/test_images/** - Sample images to test
- 📤 **Code/YOLO/darkflow/output_images/** - Detection results (generated)
- 🤖 **Code/YOLO/yolov8n.pt** - Model file (auto-generated on first run)

---

## Troubleshooting

### Q: First run is slow / large download
**A:** Model downloads on first run (~6.2 MB). This is normal and cached for future runs.

### Q: Where's the model file?
**A:** Auto-downloaded to `Code/YOLO/yolov8n.pt` on first run.

### Q: Can I use different models?
**A:** Yes! Replace `'yolov8n.pt'` with:
- `'yolov8s.pt'` - Slower but more accurate
- `'yolov8m.pt'` - Even more accurate
- `'yolov8l.pt'` - Highest accuracy (but slowest)

### Q: How fast is it?
**A:** ~50-100ms per image (8-10x faster than Darkflow)

### Q: What vehicles does it detect?
**A:** Cars, buses, trucks, motorcycles

### Q: Can it work with webcam?
**A:** Yes! Use `--video 0` in the CLI

### Q: Can it save output video?
**A:** Yes! Use `--output result.mp4` in the CLI

---

## What Changed from Darkflow?

**Old:** `from darkflow.net.build import TFNet`  
**New:** `from yolov8_detect import YOLOv8VehicleDetector`

But the functionality is the same - just faster!

---

## Next Steps

1. **Test it now:** `python vehicle_detection.py`
2. **Read quick reference:** See QUICK_REFERENCE.md
3. **Learn more:** See YOLOV8_UPGRADE_GUIDE.md
4. **Integrate in your code:** See examples above

---

## Need Help?

1. Check QUICK_REFERENCE.md for common use cases
2. All scripts have `--help` flag
3. See YOLOV8_UPGRADE_GUIDE.md for troubleshooting
4. Code has full docstrings in each file

---

**Ready to start?** Run:
```bash
cd Code/YOLO/darkflow && python vehicle_detection.py
```

Enjoy your brand new YOLOv8 detection system! 🚀
