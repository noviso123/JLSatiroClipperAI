import cv2
import os

def get_face_cascade_path():
    # Try standard opencv path
    path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
    if os.path.exists(path): return path
    return "haarcascade_frontalface_default.xml"

def scan_face(video_path):
    """
    Scans the video every 2 seconds to find the active speaker(s) center.
    Improved: Handles multiple faces and group framing.
    Returns: dict {timestamp_int: center_x_float_0_to_1}
    """
    print("👁️ Iniciando Scan Facial Inteligente (OpenCV)...")
    face_map = {}

    cascade_path = get_face_cascade_path()
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("⚠️ Erro: Haarcascade XML não encontrado.")
        return {}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return {}

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    raw_centers = {}
    step_sec = 2
    for t in range(0, int(duration), step_sec):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret: break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            # Multi-face logic: Find the min/max x to encompass all faces
            min_x = min([f[0] for f in faces])
            max_x = max([f[0] + f[2] for f in faces])

            # Simple center of the "group"
            center_x = ((min_x + max_x) / 2) / frame.shape[1]
            raw_centers[t] = center_x
        else:
            # Maintain previous if lost? No, just skip for smoothing
            pass

    cap.release()

    # APPLY SMOOTHING (Moving Average)
    times = sorted(raw_centers.keys())
    for i, t in enumerate(times):
        # Average over a 3-point window (6 seconds)
        window = []
        for j in range(max(0, i-1), min(len(times), i+2)):
            window.append(raw_centers[times[j]])
        face_map[t] = sum(window) / len(window)

    print(f"✅ Scan Inteligente Completo: {len(face_map)} pontos.")
    return face_map

def get_crop_center(start, end, face_map):
    # Average center for the segment
    centers = []
    for t in range(int(start), int(end)):
        # Check nearest key or exact key
        # Since we scan every 2s, we look for t or t-1
        val = face_map.get(t) or face_map.get(t-1)
        if val: centers.append(val)

    if not centers: return 0.5
    return sum(centers) / len(centers)
