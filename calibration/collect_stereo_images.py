#!/usr/bin/env python3
"""
Stereo Camera Image Collection Script
Collects synchronized image pairs from two USB cameras with live preview.
"""

import cv2
import numpy as np
import os
import datetime
from pathlib import Path


def create_folders():
    """Create folders for storing images from each camera."""
    Path("camera0").mkdir(exist_ok=True)
    Path("camera1").mkdir(exist_ok=True)
    print("Created/verified camera0 and camera1 folders")


def main():
    # Create output folders
    create_folders()
    
    # Initialize cameras
    # Camera indices might be 0, 1 or different depending on your system
    cap0 = cv2.VideoCapture(0)
    cap1 = cv2.VideoCapture(1)
    
    if not cap0.isOpened():
        print("Error: Cannot open camera 0")
        return
    
    if not cap1.isOpened():
        print("Error: Cannot open camera 1")
        cap0.release()
        return
    
    # Set resolution (optional - adjust for your cameras)
    cap0.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n=== Stereo Camera Image Collection ===")
    print("Controls:")
    print("  SPACE - Capture image pair")
    print("  'q' or ESC - Quit")
    print("\nCamera 0 (Left) -> camera0/")
    print("Camera 1 (Right) -> camera1/")
    print("\nStarting preview...\n")
    
    image_count = 0
    
    while True:
        # Read frames from both cameras
        ret0, frame0 = cap0.read()
        ret1, frame1 = cap1.read()
        
        if not ret0 or not ret1:
            print("Error: Failed to capture frames")
            break
        
        # Add text overlay showing image count
        display_frame0 = frame0.copy()
        display_frame1 = frame1.copy()
        
        cv2.putText(display_frame0, f"Camera 0 (Left) - Images: {image_count}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame1, f"Camera 1 (Right) - Images: {image_count}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Concatenate frames horizontally
        combined_frame = np.hstack((display_frame0, display_frame1))
        
        # Display in single window
        cv2.imshow('Stereo Camera Preview - Left | Right', combined_frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):  # Spacebar - capture images
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename0 = f"camera0/img_{image_count:03d}_{timestamp}.jpg"
            filename1 = f"camera1/img_{image_count:03d}_{timestamp}.jpg"
            
            cv2.imwrite(filename0, frame0)
            cv2.imwrite(filename1, frame1)
            
            image_count += 1
            print(f"Captured pair {image_count}: {filename0}, {filename1}")
            
        elif key == ord('q') or key == 27:  # 'q' or ESC - quit
            break
    
    # Cleanup
    cap0.release()
    cap1.release()
    cv2.destroyAllWindows()
    
    print(f"\n=== Session Complete ===")
    print(f"Total image pairs captured: {image_count}")


if __name__ == "__main__":
    main()

