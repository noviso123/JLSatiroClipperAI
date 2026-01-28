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
    Improved: Detects if there are two distinct speakers for stacked layout.
    Returns: dict {timestamp_int: [centers_list]}
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
    duration = total_frames / (fps if fps > 0 else 30)

    raw_centers = {}
    step_sec = 2
    for t in range(0, int(duration), step_sec):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret: break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            # Sort faces by X position
            sorted_faces = sorted(faces, key=lambda f: f[0])

            # Simple clustering: if gap between max_x of one and min_x of next is > 20% width
            # we consider them distinct speakers
            width = frame.shape[1]
            groups = []
            if len(sorted_faces) > 0:
                current_group = [sorted_faces[0]]
                for i in range(1, len(sorted_faces)):
                    prev_face = sorted_faces[i-1]
                    curr_face = sorted_faces[i]
                    gap = curr_face[0] - (prev_face[0] + prev_face[2])
                    if gap > (width * 0.15): # 15% width gap
                        groups.append(current_group)
                        current_group = [curr_face]
                    else:
                        current_group.append(curr_face)
                groups.append(current_group)

            centers = []
            for group in groups:
                min_x = min([f[0] for f in group])
                max_x = max([f[0] + f[2] for f in group])
                centers.append(((min_x + max_x) / 2) / width)

            raw_centers[t] = centers

    cap.release()

    # APPLY SMOOTHING (Simple persistence for this version)
    times = sorted(raw_centers.keys())
    for t in times:
        face_map[t] = raw_centers[t]

    print(f"✅ Scan Inteligente Completo: {len(face_map)} pontos.")
    return face_map

def get_crop_center(start, end, face_map):
    """
    Returns a list of centers for the segment.
    If mostly 2 centers are found, returns two averaged centers.
    """
    all_snapshots = []
    for t in range(int(start), int(end)):
        val = face_map.get(t) or face_map.get(t-1)
        if val: all_snapshots.append(val)

    if not all_snapshots: return [0.5]

    # Count how many centers we usually have
    counts = [len(s) for s in all_snapshots]
    avg_count = round(sum(counts) / len(counts))

    if avg_count <= 1:
        # Just average all first centers
        flat = [s[0] for s in all_snapshots]
        return [sum(flat) / len(flat)]
    else:
        # Average left and right centers
        lefts = [s[0] for s in all_snapshots]
        rights = [s[-1] for s in all_snapshots] # simplified for 2 groups
        return [sum(lefts)/len(lefts), sum(rights)/len(rights)]
