"""
Camera Viewer for HomeEye
Shows live webcam feeds in grid or individual windows.
Author: Built for W4GGJ / Joe
"""

import cv2
import threading
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
# Indexes of all active cameras on your system
CAMERA_INDEXES = [0, 1, 2, 3, 4]
CAMERA_LABELS  = {
    0: "Camera 0",
    1: "Camera 1",
    2: "Camera 2",
    3: "Camera 3",
    4: "Camera 4",
}

WINDOW_W = 640
WINDOW_H = 480
GRID_CELL_W = 320
GRID_CELL_H = 240

# Track open windows
_open_threads  = []
_stop_events   = []
_windows_open  = False

# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_active_cameras():
    """Return list of camera indexes that are actually working."""
    active = []
    for i in CAMERA_INDEXES:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                active.append(i)
        cap.release()
    return active

# ── Individual camera window ──────────────────────────────────────────────────
def _show_single(index: int, stop_event: threading.Event):
    label = CAMERA_LABELS.get(index, f"Camera {index}")
    cap   = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"[Camera]: Could not open camera {index}")
        return

    window_name = f"HomeEye - {label}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, WINDOW_W, WINDOW_H)

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break
        cv2.putText(frame, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyWindow(window_name)

# ── Grid view ─────────────────────────────────────────────────────────────────
def _show_grid(indexes: list, stop_event: threading.Event):
    caps = {}
    for i in indexes:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            caps[i] = cap

    if not caps:
        print("[Camera]: No cameras available for grid view")
        return

    n     = len(caps)
    cols  = min(n, 3)
    rows  = (n + cols - 1) // cols
    ids   = list(caps.keys())

    window_name = "HomeEye - All Cameras"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, GRID_CELL_W * cols, GRID_CELL_H * rows)

    while not stop_event.is_set():
        cells = []
        for i in ids:
            ret, frame = caps[i].read()
            if ret and frame is not None:
                frame = cv2.resize(frame, (GRID_CELL_W, GRID_CELL_H))
                label = CAMERA_LABELS.get(i, f"Cam {i}")
                cv2.putText(frame, label, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cells.append(frame)
            else:
                blank = np.zeros((GRID_CELL_H, GRID_CELL_W, 3), dtype=np.uint8)
                cv2.putText(blank, f"Cam {i} - No Signal", (10, GRID_CELL_H // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cells.append(blank)

        # Pad to fill grid
        while len(cells) < rows * cols:
            cells.append(np.zeros((GRID_CELL_H, GRID_CELL_W, 3), dtype=np.uint8))

        rows_frames = []
        for r in range(rows):
            row_cells = cells[r * cols:(r + 1) * cols]
            rows_frames.append(np.hstack(row_cells))
        grid = np.vstack(rows_frames)

        cv2.imshow(window_name, grid)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    for cap in caps.values():
        cap.release()
    cv2.destroyWindow(window_name)

# ── Public API ────────────────────────────────────────────────────────────────
def close_all_cameras():
    global _open_threads, _stop_events, _windows_open
    for evt in _stop_events:
        evt.set()
    for t in _open_threads:
        t.join(timeout=2)
    _open_threads  = []
    _stop_events   = []
    _windows_open  = False
    cv2.destroyAllWindows()

def show_camera(index: int) -> str:
    global _open_threads, _stop_events, _windows_open
    close_all_cameras()
    stop = threading.Event()
    t    = threading.Thread(target=_show_single, args=(index, stop), daemon=True)
    _stop_events.append(stop)
    _open_threads.append(t)
    _windows_open = True
    t.start()
    label = CAMERA_LABELS.get(index, f"Camera {index}")
    return f"Opening {label}. Say close cameras to shut it down."

def show_all_cameras() -> str:
    global _open_threads, _stop_events, _windows_open
    close_all_cameras()
    active = _get_active_cameras()
    if not active:
        return "I couldn't find any active cameras."
    stop = threading.Event()
    t    = threading.Thread(target=_show_grid, args=(active, stop), daemon=True)
    _stop_events.append(stop)
    _open_threads.append(t)
    _windows_open = True
    t.start()
    return f"Opening grid view with {len(active)} cameras. Say close cameras to shut it down."

# ── Voice command handler ─────────────────────────────────────────────────────
CAMERA_SHOW_KEYWORDS  = ["show camera", "open camera", "show cameras", "show all cameras",
                          "open cameras", "view camera", "camera view", "show me the camera"]
CAMERA_CLOSE_KEYWORDS = ["close camera", "close cameras", "hide camera", "shut camera"]

def is_camera_command(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in CAMERA_SHOW_KEYWORDS + CAMERA_CLOSE_KEYWORDS)

def handle_camera_command(text: str) -> str:
    t = text.lower()

    if any(kw in t for kw in CAMERA_CLOSE_KEYWORDS):
        close_all_cameras()
        return "Closing all camera windows."

    if "all" in t or "cameras" in t:
        return show_all_cameras()

    # Look for specific camera number
    import re
    match = re.search(r'camera\s*(\d+)', t)
    if match:
        index = int(match.group(1))
        return show_camera(index)

    # Default — show all
    return show_all_cameras()
