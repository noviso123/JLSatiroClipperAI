import cv2
import os

VIDEO_PATH = r"C:\Users\12001036\Downloads\videoplayback (1).MP4"
CASCADE_PATH = r"haarcascade_frontalface_default.xml"

def debug_vision():
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Vídeo não encontrado: {VIDEO_PATH}")
        return

    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    print(f"🎬 Analisando: {VIDEO_PATH}")
    print(f"⏱️ Duração: {duration:.2f}s | FPS: {fps}")

    detections = 0
    total_checks = 0

    # Check every 2 seconds like the engine
    for t in range(0, int(duration), 2):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret: break

        total_checks += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # We'll try different scales
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            detections += 1
            x, y, w, h = faces[0]
            center = (x + w/2) / frame.shape[1]
            print(f"✅ T={t}s: Face detectada em {center:.2f}")
        else:
            # TRY MORE AGGRESSIVE
            faces_v2 = face_cascade.detectMultiScale(gray, 1.05, 3)
            if len(faces_v2) > 0:
                detections += 1
                print(f"⚠️ T={t}s: Detectada apenas com Modo Agressivo")
            else:
                print(f"❌ T={t}s: Nenhuma face detectada")

    cap.release()
    print(f"\n📊 Resultado Final: {detections}/{total_checks} faces encontradas.")
    if detections == 0:
        print("🚨 ALERTA: O motor está cego para este vídeo. Precisamos de um Fallback Manual.")

if __name__ == "__main__":
    debug_vision()
