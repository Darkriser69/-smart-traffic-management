"""
Integration Example: YOLOv8 Detection with Signal Timer
========================================================
This script demonstrates how to use the YOLOv8 detector to feed vehicle counts
into the traffic signal timing algorithm.

This can be used with real camera feeds or video files to adaptively set signal timers
based on actual traffic density detected by YOLOv8.

Usage:
    python yolov8_integration_example.py --video <video_file_or_camera_index>
    
    Examples:
        # Using webcam (camera index 0)
        python yolov8_integration_example.py --video 0
        
        # Using video file
        python yolov8_integration_example.py --video traffic.mp4
        
        # Using images directory
        python yolov8_integration_example.py --mode images --input test_images/
"""

import cv2
import math
import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path to import yolov8_detect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yolov8_detect import YOLOv8VehicleDetector


class TrafficSignalController:
    """
    Traffic signal controller that adapts timing based on vehicle detection.
    
    This is a simplified version of the signal logic that can accept vehicle counts
    from the YOLOv8 detector.
    """
    
    # Vehicle crossing times (in seconds)
    VEHICLE_CROSSING_TIMES = {
        'car': 2.0,
        'bike': 1.0,
        'motorcycle': 1.0,
        'rickshaw': 2.25,
        'bus': 2.5,
        'truck': 2.5
    }
    
    # Signal timings (in seconds)
    DEFAULT_RED = 150
    DEFAULT_YELLOW = 5
    DEFAULT_GREEN = 20
    MIN_GREEN = 10
    MAX_GREEN = 60
    
    def __init__(self, num_lanes=2):
        """Initialize the signal controller."""
        self.num_lanes = num_lanes
        self.direction_names = ['North', 'South', 'East', 'West']
    
    def calculate_green_time(self, vehicle_counts):
        """
        Calculate optimal green time for a traffic direction based on vehicle counts.
        
        Args:
            vehicle_counts (dict): Count of each vehicle type
                                   {'car': int, 'bus': int, 'truck': int, 'motorcycle': int}
        
        Returns:
            int: Recommended green time in seconds
        """
        total_time = 0
        
        for vehicle_type, count in vehicle_counts.items():
            if vehicle_type == 'total':
                continue
            
            crossing_time = self.VEHICLE_CROSSING_TIMES.get(vehicle_type, 2.0)
            total_time += count * crossing_time
        
        # Calculate green time for the number of lanes
        green_time = math.ceil(total_time / (self.num_lanes + 1))
        
        # Clamp between min and max
        green_time = max(self.MIN_GREEN, min(green_time, self.MAX_GREEN))
        
        return green_time


class YOLOv8TrafficMonitor:
    """
    Monitor traffic using YOLOv8 and calculate signal timings.
    """
    
    def __init__(self, model_path='yolov8n.pt', confidence=0.5):
        """Initialize the traffic monitor."""
        self.detector = YOLOv8VehicleDetector(model_path, confidence)
        self.signal_controller = TrafficSignalController()
        self.frame_count = 0
        self.detection_window_frames = 10  # Calculate timing every N frames
    
    def process_video(self, video_source, output_path=None, display=True):
        """
        Process video and display vehicle counts and recommended signal timings.
        
        Args:
            video_source (str or int): Path to video file or camera index
            output_path (str): Optional path to save output video
            display (bool): Whether to display video in real-time
        """
        cap = cv2.VideoCapture(video_source)
        
        if not cap.isOpened():
            print(f"Error: Cannot open video source: {video_source}")
            return
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create video writer if needed
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Accumulate vehicle counts over detection window
        accumulated_counts = {
            'car': 0, 'bus': 0, 'truck': 0, 'motorcycle': 0, 'total': 0
        }
        
        print(f"\nProcessing video from {video_source}")
        print("Controls: Press 'q' to quit, 's' to save frame\n")
        print(f"{'Frame':<8} {'Cars':<6} {'Buses':<7} {'Trucks':<8} {'Bikes':<6} {'Green(N)':<10} {'Green(S)':<10} {'Green(E)':<10} {'Green(W)':<10}")
        print("-" * 80)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Detect vehicles
                detections = self.detector.detect_vehicles(frame, return_annotated=True)
                annotated_frame = detections['annotated_image']
                counts = detections['counts']
                
                # Accumulate counts
                for vehicle_type in ['car', 'bus', 'truck', 'motorcycle']:
                    accumulated_counts[vehicle_type] += counts.get(vehicle_type, 0)
                accumulated_counts['total'] += counts['total']
                
                self.frame_count += 1
                
                # Calculate signal timings every N frames
                if self.frame_count % self.detection_window_frames == 0:
                    # Average counts over detection window
                    avg_counts = {
                        k: v // self.detection_window_frames 
                        for k, v in accumulated_counts.items()
                    }
                    
                    # Calculate green times for each direction (in real scenario)
                    green_n = self.signal_controller.calculate_green_time(avg_counts)
                    green_s = green_n  # In real scenario, these would be calculated differently
                    green_e = green_n
                    green_w = green_n
                    
                    # Print statistics
                    print(f"{self.frame_count:<8} {avg_counts['car']:<6} {avg_counts['bus']:<7} "
                          f"{avg_counts['truck']:<8} {avg_counts['motorcycle']:<6} {green_n:<10} "
                          f"{green_s:<10} {green_e:<10} {green_w:<10}")
                    
                    # Reset accumulated counts
                    accumulated_counts = {
                        'car': 0, 'bus': 0, 'truck': 0, 'motorcycle': 0, 'total': 0
                    }
                
                # Add text to frame
                text_lines = [
                    f"Car: {counts['car']}, Bus: {counts['bus']}, Truck: {counts['truck']}, Bike: {counts['motorcycle']}",
                    f"Frame: {self.frame_count}",
                    f"Total Vehicles: {counts['total']}"
                ]
                
                y_offset = 30
                for text in text_lines:
                    cv2.putText(annotated_frame, text, (10, y_offset), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_offset += 30
                
                # Write to output video
                if writer:
                    writer.write(annotated_frame)
                
                # Display
                if display:
                    cv2.imshow('YOLOv8 Traffic Monitor', annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('s'):
                        filename = f"traffic_frame_{self.frame_count}.png"
                        cv2.imwrite(filename, annotated_frame)
                        print(f"Saved frame to {filename}")
        
        finally:
            cap.release()
            if writer:
                writer.release()
            if display:
                cv2.destroyAllWindows()
        
        print(f"\nProcessing complete! Processed {self.frame_count} frames.")
    
    def process_images(self, image_dir, output_dir=None):
        """
        Process images from a directory and calculate signal timings.
        
        Args:
            image_dir (str): Directory containing images
            output_dir (str): Optional directory to save annotated images
        """
        if not os.path.exists(image_dir):
            print(f"Error: Image directory not found: {image_dir}")
            return
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        print(f"\nProcessing images from {image_dir}\n")
        print(f"{'Image':<25} {'Cars':<6} {'Buses':<7} {'Trucks':<8} {'Bikes':<6} {'Green Time':<12}")
        print("-" * 70)
        
        image_files = [f for f in os.listdir(image_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        for filename in image_files:
            image_path = os.path.join(image_dir, filename)
            image = cv2.imread(image_path)
            
            if image is None:
                print(f"Skipping {filename}: Cannot read image")
                continue
            
            # Detect vehicles
            detections = self.detector.detect_vehicles(image, return_annotated=True)
            counts = detections['counts']
            
            # Calculate green time
            green_time = self.signal_controller.calculate_green_time(counts)
            
            # Print statistics
            print(f"{filename:<25} {counts['car']:<6} {counts['bus']:<7} "
                  f"{counts['truck']:<8} {counts['motorcycle']:<6} {green_time:<12}s")
            
            # Save annotated image
            if output_dir:
                output_path = os.path.join(output_dir, f"detected_{filename}")
                cv2.imwrite(output_path, detections['annotated_image'])
        
        print("\nProcessing complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='YOLOv8 Traffic Monitoring')
    parser.add_argument('--mode', type=str, default='video', 
                       choices=['video', 'images'],
                       help='Processing mode: video or images')
    parser.add_argument('--video', type=str, default='0',
                       help='Video file path or camera index (default: 0 for webcam)')
    parser.add_argument('--input', type=str, default='test_images',
                       help='Input directory for images mode')
    parser.add_argument('--output', type=str, default=None,
                       help='Output path for saving results')
    parser.add_argument('--no-display', action='store_true',
                       help='Disable real-time display')
    parser.add_argument('--model', type=str, default='yolov8n.pt',
                       help='YOLOv8 model to use (default: yolov8n.pt)')
    parser.add_argument('--confidence', type=float, default=0.5,
                       help='Detection confidence threshold (0-1)')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = YOLOv8TrafficMonitor(model_path=args.model, confidence=args.confidence)
    
    # Process based on mode
    if args.mode == 'video':
        # Convert string '0' to integer for camera index
        video_source = int(args.video) if args.video.isdigit() else args.video
        monitor.process_video(video_source, output_path=args.output, 
                            display=not args.no_display)
    else:  # images mode
        monitor.process_images(args.input, output_dir=args.output)


if __name__ == "__main__":
    main()
