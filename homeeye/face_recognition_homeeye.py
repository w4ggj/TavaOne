"""
HomeEye Face Recognition
Uses OpenCV face detection + simple face encoding for recognition.
No heavy dlib dependency — works with standard opencv-python.

Setup:
1. Run: py face_setup.py  (to enroll faces)
2. HomeEye will then recognize enrolled faces via webcam

Author: Built for W4GGJ / Joe
"""

import cv2
import numpy as np
import json
import os
from pathlib import Path

FACES_DIR  = Path("C:/HomeEye/faces")
FACES_FILE = Path("C:/HomeEye/faces/enrolled.json")
FACES_DIR.mkdir(exist_ok=True)

# Load OpenCV face detector
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def load_enrolled() -> dict:
    """Load enrolled faces from disk."""
    if FACES_FILE.exists():
        return json.loads(FACES_FILE.read_text())
    return {}

def save_enrolled(data: dict):
    FACES_FILE.write_text(json.dumps(data, indent=2))

def get_face_descriptor(frame) -> np.ndarray | None:
    """Extract a simple face descriptor from a frame."""
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    face_roi   = cv2.resize(gray[y:y+h, x:x+w], (64, 64))
    # Flatten and normalize as simple descriptor
    descriptor = face_roi.astype(np.float32).flatten()
    descriptor /= (np.linalg.norm(descriptor) + 1e-6)
    return descriptor.tolist()

def enroll_face(name: str, frame) -> bool:
    """Enroll a face for recognition."""
    desc = get_face_descriptor(frame)
    if desc is None:
        return False
    enrolled = load_enrolled()
    if name not in enrolled:
        enrolled[name] = []
    enrolled[name].append(desc)
    save_enrolled(enrolled)
    return True

def recognize_face(frame, threshold: float = 0.92) -> str | None:
    """Recognize a face in the frame. Returns name or None."""
    desc = get_face_descriptor(frame)
    if desc is None:
        return None

    enrolled = load_enrolled()
    if not enrolled:
        return None

    query     = np.array(desc)
    best_name = None
    best_sim  = 0.0

    for name, descriptors in enrolled.items():
        for ref_desc in descriptors:
            ref  = np.array(ref_desc)
            sim  = float(np.dot(query, ref))
            if sim > best_sim:
                best_sim  = sim
                best_name = name

    if best_sim >= threshold:
        return best_name
    return None

def identify_from_camera(cam_index: int = 0) -> str:
    """Take a photo and try to identify the person. Returns greeting string."""
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)

    import time
    time.sleep(1.5)
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return "unknown"

    name = recognize_face(frame)
    return name if name else "unknown"
