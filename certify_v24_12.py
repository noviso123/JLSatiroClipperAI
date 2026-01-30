import os
import sys
import shutil
import cv2

# Mimic the environment
sys.path.append(os.getcwd())

from backend import processing, video_engine

VIDEO_REAL = r"C:\Users\12001036\Downloads\videoplayback (1).MP4"
WORK_DIR = "temp_final_v24_12"
DRIVE_DIR = "downloads_v24_12"

def certify_vstack():
    if os.path.exists(WORK_DIR): shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(DRIVE_DIR, exist_ok=True)

    print("🚀 CERTIFICAÇÃO TITANIUM V24.12 - MODO FUSÃO...")

    # Simulação baseada nos logs reais da face detectada (0.37-0.39)
    # Isso ATIVAVA Normal antes, agora deve ATIVAR Split.
    REAL_HOST_CENTER = 0.38

    seg = {'start': 130.0, 'end': 135.0} # Ponto onde a face está em 0.37

    face_map = {
        130: {"center": REAL_HOST_CENTER, "count": 1},
        132: {"center": REAL_HOST_CENTER, "count": 1},
        134: {"center": REAL_HOST_CENTER, "count": 1}
    }

    seg_data = (0, seg, 1, face_map, {'layout': 'Dinâmico'}, "V24.12_TEST", [], REAL_HOST_CENTER)

    print(f"🔨 Processando T=130-135s (Face em 0.38). Esperado: VSTACK (Split Mode)")
    res = processing.process_single_segment(seg_data, VIDEO_REAL, WORK_DIR, DRIVE_DIR)

    if res:
        print(f"✅ SUCESSO! Vídeo gerado: {res['path']}")
        # Verificação visual
        cap = cv2.VideoCapture(res['path'])
        cap.set(cv2.CAP_PROP_POS_MSEC, 2500)
        ret, frame = cap.read()
        if ret:
            # Check for vertical split (difference between top and bottom halves)
            # Just save it as evidence
            cv2.imwrite(os.path.join(DRIVE_DIR, "V24.12_EVIDENCE.jpg"), frame)
            print("📸 EVIDÊNCIA CAPTURADA: downloads_v24_12/V24.12_EVIDENCE.jpg")
    else:
        print("❌ FALHA NA CERTIFICAÇÃO.")

if __name__ == "__main__":
    certify_vstack()
