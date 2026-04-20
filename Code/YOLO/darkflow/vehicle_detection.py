"""
Vehicle Detection Module - YOLOv8 Version
==========================================
This is the updated version using YOLOv8 (Ultralytics) instead of Darkflow.
Compatible with Python 3.11+

Previous version used Darkflow (YOLOv2 + TensorFlow 1.x).
New version uses YOLOv8n pretrained model.
"""

import cv2
import os
import sys

# Import the YOLOv8 detector from the new module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from yolov8_detect import YOLOv8VehicleDetector

# Configuration
MODEL_PATH = "yolov8n.pt"  # YOLOv8 nano model - good balance of speed and accuracy
CONFIDENCE_THRESHOLD = 0.3  # Same threshold as Darkflow version
INPUT_PATH = os.getcwd() + "/test_images/"
OUTPUT_PATH = os.getcwd() + "/output_images/"

# Initialize the YOLOv8 detector
print(f"Initializing YOLOv8 detector with model: {MODEL_PATH}")
detector = YOLOv8VehicleDetector(MODEL_PATH, confidence_threshold=CONFIDENCE_THRESHOLD)

def detectVehicles(filename):
    """
    Detect vehicles in an image file.
    
    Args:
        filename (str): Name of the image file in INPUT_PATH
    
    Returns:
        list: List of detected vehicles with labels and coordinates
    """
    global detector, INPUT_PATH, OUTPUT_PATH
    
    input_file = INPUT_PATH + filename
    img = cv2.imread(input_file, cv2.IMREAD_COLOR)
    
    if img is None:
        print(f"Error: Could not read image from {input_file}")
        return []
    
    # Detect vehicles using YOLOv8
    detections = detector.detect_vehicles(img, return_annotated=True)
    
    # Draw bounding boxes for visualization
    result_img = detections['annotated_image']
    
    # Save output image
    output_filename = OUTPUT_PATH + "output_" + filename
    cv2.imwrite(output_filename, result_img)
    print(f'Output image stored at: {output_filename}')
    
    # Print detection summary
    counts = detections['counts']
    print(f"  Cars: {counts['car']}, Buses: {counts['bus']}, Trucks: {counts['truck']}, Motorcycles: {counts['motorcycle']}")
    
    return detections['vehicles']

# Main execution
if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    # Process all images in the test_images directory
    if not os.path.exists(INPUT_PATH):
        print(f"Error: Input path does not exist: {INPUT_PATH}")
    else:
        print(f"\nProcessing images from {INPUT_PATH}")
        image_files = [f for f in os.listdir(INPUT_PATH) 
                      if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        
        if image_files:
            for filename in image_files:
                print(f"\nProcessing: {filename}")
                detectVehicles(filename)
            print("\nDone!")
        else:
            print(f"No image files found in {INPUT_PATH}")