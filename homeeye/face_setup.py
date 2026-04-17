"""
HomeEye Face Enrollment
Run this script to enroll faces for recognition.
Usage: py face_setup.py

Author: Built for W4GGJ / Joe
"""

import cv2
import time
from pathlib import Path
from face_recognition_homeeye import enroll_face, load_enrolled, FACES_DIR

FACES_DIR.mkdir(exist_ok=True)

def enroll_person(name: str, cam_index: int = 0, samples: int = 5):
    print(f"\nEnrolling: {name}")
    print("Look at the camera. Taking 5 photos in 3 seconds...")
    time.sleep(3)

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)

    # Warmup
    time.sleep(1.5)
    for _ in range(5):
        cap.read()

    success = 0
    for i in range(samples):
        ret, frame = cap.read()
        if ret and frame is not None:
            if enroll_face(name, frame):
                success += 1
                print(f"  Sample {i+1}/{samples} captured!")
            else:
                print(f"  Sample {i+1}/{samples} - no face detected, try again")
        time.sleep(0.5)

    cap.release()
    print(f"Enrolled {success}/{samples} samples for {name}")
    return success > 0

def main():
    print("=" * 50)
    print("  HomeEye Face Enrollment — W4GGJ")
    print("=" * 50)

    enrolled = load_enrolled()
    if enrolled:
        print(f"\nCurrently enrolled: {', '.join(enrolled.keys())}")

    print("\nEnter name to enroll (or 'done' to finish):")
    while True:
        name = input("Name: ").strip()
        if name.lower() == "done" or not name:
            break
        enroll_person(name)

    print("\nEnrollment complete!")
    print(f"Enrolled faces: {', '.join(load_enrolled().keys())}")

if __name__ == "__main__":
    main()
