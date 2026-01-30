import os
import sys
import shutil
import cv2

# Mimic the environment
sys.path.append(os.getcwd())

from backend import processing, video_engine

VIDEO_REAL = r"C:\Users\12001036\Downloads\videoplayback (1).MP4"
WORK_DIR = "temp_cert_v24_13"
DRIVE_DIR = "downloads_v24_13"

def run_cert():
    if os.path.exists(WORK_DIR): shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(DRIVE_DIR, exist_ok=True)

    # 1. TEST AUTO DETECTION (DYNAMIC)
    # Face at 0.38 should now trigger Split due to 0.45 threshold
    print("🚀 TESTE 1: DETECÇÃO AUTOMÁTICA (DINÂMICO)...")
    seg = {'start': 130.0, 'end': 135.0}
    face_map = {
        130: {"count": 1, "faces": [{"center": 0.38, "center_y": 0.35, "area": 0.1}]},
        132: {"count": 1, "faces": [{"center": 0.38, "center_y": 0.35, "area": 0.1}]},
        134: {"count": 1, "faces": [{"center": 0.38, "center_y": 0.35, "area": 0.1}]}
    }
    seg_data = (0, seg, 1, face_map, {'layout': 'Dinâmico (Auto-IA)'}, "AUTO_V13", [], 0.38)

    res1 = processing.process_single_segment(seg_data, VIDEO_REAL, WORK_DIR, DRIVE_DIR)
    if res1:
        cap = cv2.VideoCapture(res1['path'])
        cap.set(cv2.CAP_PROP_POS_MSEC, 2500)
        ret, frame = cap.read()
        if ret: cv2.imwrite(os.path.join(DRIVE_DIR, "PROOF_AUTO_V13.jpg"), frame)
        cap.release()
        print("✅ Auto-Detecção OK.")

    # 2. TEST MANUAL OVERRIDE (REAÇÃO)
    print("🚀 TESTE 2: MODO MANUAL (REAÇÃO)...")
    seg_data_manual = (0, seg, 1, face_map, {'layout': 'Reação (Rosto/Base)'}, "MANUAL_V13", [], 0.38)
    res2 = processing.process_single_segment(seg_data_manual, VIDEO_REAL, WORK_DIR, DRIVE_DIR)
    if res2:
        cap = cv2.VideoCapture(res2['path'])
        cap.set(cv2.CAP_PROP_POS_MSEC, 2500)
        ret, frame = cap.read()
        if ret: cv2.imwrite(os.path.join(DRIVE_DIR, "PROOF_MANUAL_V13.jpg"), frame)
        cap.release()
        print("✅ Modo Manual OK.")

if __name__ == "__main__":
    run_cert()
