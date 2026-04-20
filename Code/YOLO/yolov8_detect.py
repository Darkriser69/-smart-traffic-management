"""
YOLOv8 Vehicle Detection Module
================================
This module provides vehicle detection using YOLOv8 (Ultralytics).
Detects: car, bus, truck, motorcycle (bike)
Replaces Darkflow (YOLOv2 + TensorFlow 1.x) for the Adaptive Traffic Signal Timer.

Features:
    - Detect vehicles in images and video frames
    - Count vehicles by type
    - Draw bounding boxes on output
    - Return structured detection results
"""

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path


class YOLOv8VehicleDetector:
    """
    A wrapper class for YOLOv8 vehicle detection.
    
    Attributes:
        model: The YOLOv8 model instance
        model_path: Path to the pretrained model file
        confidence_threshold: Minimum confidence score for detections
        vehicle_classes: Classes to detect (car, bus, truck, motorcycle)
    """
    
    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.5):
        """
        Initialize the YOLOv8 detector.
        
        Args:
            model_path (str): Path to YOLOv8 model file (default: yolov8n.pt)
                             Can be 'yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', etc.
                             If file doesn't exist, it will be downloaded automatically.
            confidence_threshold (float): Minimum confidence for detections (0.0-1.0)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        
        # Vehicle classes to detect
        self.vehicle_classes = {
            'car': 2,
            'bus': 5,
            'truck': 7,
            'motorcycle': 3  # 'motorcycle' in COCO dataset
        }
        
        # Load the model
        print(f"Loading YOLOv8 model from {model_path}...")
        self.model = YOLO(model_path)
        print("YOLOv8 model loaded successfully!")
    
    def detect_vehicles(self, image, return_annotated=False):
        """
        Detect vehicles in an image.
        
        Args:
            image (numpy.ndarray): Input image (BGR format from OpenCV)
            return_annotated (bool): If True, return annotated image with bounding boxes
        
        Returns:
            dict: Detection results containing:
                - 'vehicles': list of detected vehicles with labels and confidence
                - 'counts': dict with count of each vehicle type
                - 'total_vehicles': total count of all vehicles
                - 'annotated_image': annotated image if return_annotated=True
        """
        # Run inference
        results = self.model(image, conf=self.confidence_threshold, verbose=False)
        
        detections = {
            'vehicles': [],
            'counts': {
                'car': 0,
                'bus': 0,
                'truck': 0,
                'motorcycle': 0,
                'total': 0
            },
            'annotated_image': None
        }
        
        # Process results
        result = results[0]  # First (and only) image result
        
        # Get class names from model
        class_names = result.names  # {0: 'person', 1: 'bicycle', 2: 'car', ...}
        
        # Process each detection
        for box in result.boxes:
            class_id = int(box.cls)
            class_name = class_names[class_id]
            confidence = float(box.conf)
            
            # Check if detected class is a vehicle we care about
            if class_name in self.vehicle_classes or class_id in self.vehicle_classes.values():
                # Normalize class name
                normalized_name = class_name.lower()
                if normalized_name == 'motorcycle' or normalized_name == 'motorbike':
                    normalized_name = 'motorcycle'
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = map(float, box.xyxy[0])
                
                vehicle_info = {
                    'label': normalized_name,
                    'confidence': confidence,
                    'topleft': {'x': int(x1), 'y': int(y1)},
                    'bottomright': {'x': int(x2), 'y': int(y2)}
                }
                
                detections['vehicles'].append(vehicle_info)
                
                # Count vehicles by type
                if normalized_name in detections['counts']:
                    detections['counts'][normalized_name] += 1
                detections['counts']['total'] += 1
        
        # Optionally return annotated image
        if return_annotated:
            annotated_image = result.plot()  # Returns BGR image with boxes
            detections['annotated_image'] = annotated_image
        
        return detections
    
    def detect_from_image_file(self, image_path, output_path=None):
        """
        Detect vehicles in an image file.
        
        Args:
            image_path (str): Path to input image file
            output_path (str): Optional path to save annotated output image
        
        Returns:
            dict: Detection results (same format as detect_vehicles)
        """
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot read image from {image_path}")
        
        # Detect vehicles
        detections = self.detect_vehicles(image, return_annotated=True)
        
        # Save annotated image if output path provided
        if output_path and detections['annotated_image'] is not None:
            cv2.imwrite(output_path, detections['annotated_image'])
            print(f"Annotated image saved to {output_path}")
        
        return detections
    
    def detect_from_video(self, video_path, output_path=None, display=False, frame_skip=1):
        """
        Detect vehicles in a video file or camera stream.
        
        Args:
            video_path (str or int): Path to video file or camera index (0 for default camera)
            output_path (str): Optional path to save output video
            display (bool): If True, display the video with detections in real-time
            frame_skip (int): Process every nth frame (for faster processing)
        
        Yields:
            tuple: (frame_number, detection_results, annotated_image)
                   This allows processing video frame by frame
        """
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Setup video writer if output path provided
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_number = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames
                if frame_number % frame_skip != 0:
                    frame_number += 1
                    continue
                
                # Detect vehicles
                detections = self.detect_vehicles(frame, return_annotated=True)
                annotated_image = detections['annotated_image']
                
                # Write to output video
                if writer:
                    writer.write(annotated_image)
                
                # Display if requested
                if display:
                    cv2.imshow('YOLOv8 Vehicle Detection', annotated_image)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Yield results
                yield frame_number, detections, annotated_image
                frame_number += 1
        
        finally:
            cap.release()
            if writer:
                writer.release()
            if display:
                cv2.destroyAllWindows()
    
    def get_vehicle_count(self, image):
        """
        Get total vehicle count in an image.
        Simplified method for quick counting.
        
        Args:
            image (numpy.ndarray): Input image
        
        Returns:
            dict: Vehicle counts by type and total
        """
        detections = self.detect_vehicles(image)
        return detections['counts']


def detect_vehicles_in_image(image_path, model_path='yolov8n.pt', 
                             output_path=None, confidence=0.5):
    """
    Convenience function to detect vehicles in a single image.
    
    Args:
        image_path (str): Path to input image
        model_path (str): Path to YOLOv8 model
        output_path (str): Optional path to save annotated image
        confidence (float): Confidence threshold
    
    Returns:
        dict: Detection results
    """
    detector = YOLOv8VehicleDetector(model_path, confidence)
    return detector.detect_from_image_file(image_path, output_path)


def detect_vehicles_in_video(video_path, model_path='yolov8n.pt',
                            output_path=None, display=False, 
                            confidence=0.5, frame_skip=1):
    """
    Convenience function to detect vehicles in a video.
    
    Args:
        video_path (str or int): Path to video file or camera index
        model_path (str): Path to YOLOv8 model
        output_path (str): Optional path to save output video
        display (bool): Show video in real-time
        confidence (float): Confidence threshold
        frame_skip (int): Process every nth frame
    
    Returns:
        generator: Yields (frame_number, detections, annotated_image)
    """
    detector = YOLOv8VehicleDetector(model_path, confidence)
    return detector.detect_from_video(video_path, output_path, display, frame_skip)


# Example usage and testing
if __name__ == "__main__":
    import os
    
    print("YOLOv8 Vehicle Detection Module")
    print("=" * 50)
    
    # Initialize detector
    detector = YOLOv8VehicleDetector('yolov8n.pt', confidence_threshold=0.5)
    
    # Example 1: Detect in images
    test_images_dir = "test_images"
    output_images_dir = "output_images"
    
    if os.path.exists(test_images_dir):
        print(f"\nProcessing images from {test_images_dir}...")
        os.makedirs(output_images_dir, exist_ok=True)
        
        for filename in os.listdir(test_images_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                input_path = os.path.join(test_images_dir, filename)
                output_path = os.path.join(output_images_dir, f"output_{filename}")
                
                print(f"\nProcessing: {filename}")
                detections = detector.detect_from_image_file(input_path, output_path)
                
                print(f"  Vehicles detected:")
                for vehicle_type, count in detections['counts'].items():
                    if vehicle_type != 'total':
                        print(f"    {vehicle_type}: {count}")
                print(f"  Total: {detections['counts']['total']}")
    else:
        print(f"Note: {test_images_dir} directory not found. Skipping image processing.")
    
    print("\nModule ready for use!")
