import os
import subprocess
import shutil
import random
import time

def setup_directories():
    # Detect Google Colab / Linux High Performance RAM Disk
    if os.path.exists("/dev/shm"):
        work_dir = "/dev/shm/temp_work_colab"
        print("🚀 DETECTADO AMBIENTE LINUX/COLAB: Usando RAM DISK (/dev/shm) para velocidade extrema!")
    else:
        work_dir = "temp_work"

    drive_dir = "downloads"

    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(drive_dir, exist_ok=True)
    return work_dir, drive_dir

def detect_active_speaker_x(video_path, start_t, dur):
    """
    Phase 2: Smart Crop Logic using MediaPipe.
    """
    try:
        import cv2
        import mediapipe as mp
        import mediapipe as mp
        try:
             mp_face_detection = mp.solutions.face_detection
        except:
             try:
                 from mediapipe import solutions
                 mp_face_detection = solutions.face_detection
             except:
                 import mediapipe.python.solutions.face_detection as mp_face_detection
        detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

        cap = cv2.VideoCapture(video_path)

        # Sample 5 frames
        timestamps = [start_t + (dur * i / 5) for i in range(1, 5)]
        face_x_centers = []

        for ts in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
            ret, frame = cap.read()
            if not ret: continue

            results = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.detections:
                max_area = 0
                best_center = 0.5
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    area = bbox.width * bbox.height
                    center_x = bbox.xmin + (bbox.width / 2)
                    if area > max_area:
                        max_area = area
                        best_center = center_x
                face_x_centers.append(best_center)

        cap.release()

        if face_x_centers:
            avg_x = sum(face_x_centers) / len(face_x_centers)
            print(f"🎯 Smart Crop Alvo: {avg_x:.2f}")
            return avg_x

    except Exception as e:
        print(f"⚠️ Erro Smart Crop: {e}")

    return 0.5


def scan_face_positions(video_path):
    """
    Phase 5: Global Face Scan (Pre-Calculation)
    Scans the entire video once and caches face positions.
    Returns: {timestamp (int_seconds): center_x_norm (float)}
    """
    print("👁️ Iniciando Scan Facial Global (Smart Crop V2)...")
    face_map = {}

    # 1. Attempt Import
    try:
        import cv2
        import mediapipe as mp
        # Standard Import (The correct way)
        mp_face = mp.solutions.face_detection
    except Exception as e:
        print(f"⚠️ Smart Crop Indisponível (Erro Importação): {e}")
        print("    -> Usando Corte Centralizado (Padrão).")
        return {}

    # 2. Run Scan
    try:
        print("👁️ Iniciando Scan Facial Global (Smart Crop V2)...")
        detector = mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5)

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps

        # Scan every 1 second
        for t in range(0, int(duration), 1):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, frame = cap.read()
            if not ret: break

            results = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.detections:
                # Find biggest face
                max_area = 0
                best_center = 0.5
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    area = bbox.width * bbox.height
                    if area > max_area:
                        max_area = area
                        best_center = bbox.xmin + (bbox.width / 2)
                face_map[t] = best_center

        cap.release()
        print(f"✅ Scan Completo: {len(face_map)} pontos mapeados.")
        return face_map

    except Exception as e:
        print(f"⚠️ Erro durante execução do Global Scan: {e}")
        return {}

def get_crop_from_cache(start_t, dur, face_map):
    """
    Retrieves average face position from cache for a specific segment.
    """
    if not face_map: return 0.5

    relevant_centers = []
    # Check seconds within the segment range
    for t in range(int(start_t), int(start_t + dur)):
        if t in face_map:
            relevant_centers.append(face_map[t])

    if relevant_centers:
        return sum(relevant_centers) / len(relevant_centers)

    return 0.5

# --- FFmpeg Logic Centralized ---

def calculate_crop_x(center_norm, scaled_w, crop_w):
    """Calculates the X coordinate for the crop based on normalized center."""
    center_px = center_norm * scaled_w
    crop_x = int(center_px - (crop_w / 2))
    # Boundary checks
    if crop_x < 0: crop_x = 0
    if crop_x > (scaled_w - crop_w): crop_x = (scaled_w - crop_w)
    return crop_x

def build_vertical_filter_complex(crop_x, crop_w, use_cuda=False):
    """
    Constructs the FFmpeg filter graph string for 9:16 vertical video.
    Supports both CPU and CUDA acceleration.
    """
    if use_cuda:
        # Phase 7: GPU Filters (Hardware Accelerated)
        # 1. Scale input to height 480 (maintaining aspect ratio initially, but we force specific logic here)
        # Note: crop is usually CPU-bound or tricky in pure hw, so we often do:
        # hwdownload -> crop -> hwupload for complex pipelines or stay in CPU for crop.
        # However, looking at the previous working logic:
        # [0:v]scale_cuda=-1:480,hwdownload,format=nv12,crop={crop_w}:480:{crop_x}:0,hwupload,scale_cuda=1080:1920[bg]
        return (
            f"[0:v]scale_cuda=-1:480,hwdownload,format=nv12,crop={crop_w}:480:{crop_x}:0,hwupload,"
            "scale_cuda=1080:1920[bg];"
            "[0:v]scale_cuda=1080:-1[fg];"
            "[bg][fg]overlay_cuda=(W-w)/2:(H-h)/2,hwdownload,format=yuv420p"
        )
    else:
        # Fallback CPU Filters
        return (
            f"[0:v]scale=-1:480,crop={crop_w}:480:{crop_x}:0,boxblur=10:5,"
            "scale=1080:1920[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )

def generate_thumbnail(video_path, output_path, job_id, text="VIRAL"):
    try:
        # Use dynamic timestamp (20% of duration or 1s) to avoid black frames
        timestamp = '00:00:02'

        vf_text = f"drawtext=text='{text}':fontcolor=yellow:fontsize=150:x=(w-text_w)/2:y=(h-text_h)/5:borderw=8:bordercolor=black:shadowx=5:shadowy=5"
        img_tmp = output_path.replace('.mp4', '.jpg')

        subprocess.run([
            'ffmpeg', '-ss', timestamp, '-i', video_path,
            '-vf', vf_text,
            '-vframes', '1', img_tmp, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.run([
            'ffmpeg', '-loop', '1', '-i', img_tmp,
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=44100',
            '-t', '0.1',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-ar', '44100',
            '-shortest', output_path, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️ Erro Thumbnail: {e}")

def create_narrator_hook(video_path, output_path, text, job_id):
    try:
        hooks = ["⚠️ ATENÇÃO ⚠️", "😱 OLHA ISSO", "🚨 URGENTE", "🤯 INCRÍVEL", "🛑 PARE TUDO"]
        hook_text = random.choice(hooks)
        vf_chain = (
            f"zoompan=z='min(zoom+0.0015,1.5)':d=90:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"drawtext=text='{hook_text}':fontcolor=white:fontsize=130:x=(w-text_w)/2:y=(h-text_h)/2:borderw=5:bordercolor=red:enable='between(t,0,1)'"
        )
        subprocess.run([
            'ffmpeg', '-i', video_path, '-vf', vf_chain, '-t', '3',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'copy',
            output_path, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        shutil.copy(video_path, output_path)

def cleanup_temps(folder, job_id):
    temps = [f"raw_cut_{job_id}.mp4", f"raw_cut_{job_id}.wav", f"hook_raw_{job_id}.mp4", f"hook_{job_id}.mp4", f"main_clip_{job_id}.mp4", f"thumb_{job_id}.mp4", f"list_{job_id}.txt", f"subs_{job_id}.ass"]
    for f in temps:
        p = os.path.join(folder, f)
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

# --- DOWNLOADERS ---
def download_strategy_pytubefix(url, output_path):
    try:
        from pytubefix import YouTube
        print("💎 Engine: Pytubefix (Stable)...")
        yt = YouTube(url, client='ANDROID')

        # Priority: Progressive MP4 (Audio+Video) -> Best Video MP4
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()

        if stream:
            stream.download(output_path=os.path.dirname(output_path), filename=os.path.basename(output_path))
            return True
        else:
            print("❌ Erro: Nenhum stream MP4 compatível encontrado.")
            return False

    except Exception as e:
        print(f"❌ Erro Download Pytubefix: {e}")
        return False
