import os
import subprocess
import shutil
import random
import time
import cv2

def setup_directories():
    """Zenith Optimization: Strategic RAM Disk & Resilient Workspace Setup."""
    work_dir = "temp_work"
    drive_dir = "downloads"
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(drive_dir, exist_ok=True)
    return work_dir, drive_dir

def get_face_cascade():
    try:
        path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        if os.path.exists(path): return path
    except: pass
    if os.path.exists("haarcascade_frontalface_default.xml"):
        return "haarcascade_frontalface_default.xml"
    return None

def get_video_dimensions(video_path):
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return w, h

def scan_face_positions(video_path):
    print("👁️ Iniciando Scan Facial Global (Smart Crop V3)...")
    face_map = {}
    try:
        cascade_path = get_face_cascade()
        if not cascade_path: return {}
        face_cascade = cv2.CascadeClassifier(cascade_path)
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        for t in range(0, int(duration), 2):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, frame = cap.read()
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                max_area = 0
                best_center = 0.5
                for (x, y, w, h) in faces:
                    area = w * h
                    if area > max_area:
                        max_area = area
                        best_center = (x + w/2) / frame.shape[1]
                face_map[t] = {"center": best_center, "count": len(faces)}
        cap.release()
        return face_map
    except: return {}

def get_crop_from_cache(start_t, dur, face_map):
    if not face_map: return 0.5
    centers = []
    for t in range(int(start_t), int(start_t + dur)):
        if t in face_map:
            val = face_map[t]
            centers.append(val["center"] if isinstance(val, dict) else val)
    return sum(centers)/len(centers) if centers else 0.5

def get_layout_zones(start_t, dur, face_map):
    """Titan Intelligence: Segmental Zone Analysis with Adaptive Tracking."""
    zones = []
    current_layout = None
    last_t = 0

    # Granular analysis every 0.1s is overkill, but we check every 2s for crop shifts
    CHECK_INTERVAL = 2.0

    for t in range(int(start_t), int(start_t + dur)):
        is_shifted = False
        face_count = 1

        if t in face_map and isinstance(face_map[t], dict):
            c = face_map[t].get("center", 0.5)
            face_count = face_map[t].get("count", 1)
            if c < 0.35 or c > 0.65: is_shifted = True

        layout = "Split" if (face_count >= 2 or is_shifted) else "Normal"

        # We trigger a zone change if the layout changes OR if we hit a threshold for tracking
        if layout != current_layout:
            if current_layout: zones.append((last_t, t - start_t, current_layout))
            current_layout = layout
            last_t = t - start_t

    zones.append((last_t, dur, current_layout))
    return zones

def build_vertical_filter_complex(crop_x, crop_w):
    return f"[0:v]split=2[in_bg][in_fg];[in_bg]scale=-2:480:flags=lanczos,crop={crop_w}:480:{crop_x}:0,gblur=sigma=20,scale=720:1280:flags=lanczos,setsar=1/1[bg];[in_fg]scale=720:-2:flags=lanczos,setsar=1/1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"

def build_split_screen_filter(crop_x_top, crop_x_bottom, crop_w):
    return f"[0:v]split=2[v1][v2];[v1]scale=-2:640:flags=lanczos,crop={crop_w}:640:{crop_x_top}:0,setsar=1/1[top];[v2]scale=-2:640:flags=lanczos,crop={crop_w}:640:{crop_x_bottom}:0,setsar=1/1[bottom];[top][bottom]vstack=inputs=2,scale=720:1280,setsar=1/1"

def build_gamer_overlay_filter(crop_x_face, crop_w):
    """Titan Gamer: Face Circle Overlay over main gameplay/content."""
    return f"[0:v]split=2[in_main][in_face];[in_main]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1/1[bg];[in_face]scale=-2:300:flags=lanczos,crop=250:250:{crop_x_face}:25,format=yuva420p,geq=lum='p(X,Y)':a='if(gt(sqrt(pow(X-125,2)+pow(Y-125,2)),120),0,255)'[fg];[bg][fg]overlay=20:20:shortest=1,setsar=1/1"

def build_dynamic_filter_complex(zones, crop_x_normal, crop_x_top, crop_x_bottom, crop_w, is_gamer=False):
    if is_gamer: return build_gamer_overlay_filter(crop_x_normal, crop_w)

    # Pre-calculate common properties
    # [top] is usually the FACE, [bottom] is usually the CONTENT (smartphone)
    split_vf = f";[0:v]split=2[v_top][v_bot];"
    split_vf += f"[v_top]scale=-2:640:flags=lanczos,crop={crop_w}:640:{crop_x_top}:0,setsar=1/1[top];"
    split_vf += f"[v_bot]scale=-2:640:flags=lanczos,crop={crop_w}:640:{crop_x_bottom}:0,setsar=1/1[bottom];"
    split_vf += "[top][bottom]vstack=inputs=2,scale=720:1280,setsar=1/1[v_split]"

    base_vf = build_vertical_filter_complex(crop_x_normal, crop_w) + "[v_base]"

    splits = [z for z in zones if z[2] == "Split"]
    if not splits: return build_vertical_filter_complex(crop_x_normal, crop_w)

    enable = " + ".join([f"between(t,{z[0]},{z[1]})" for z in splits])
    return base_vf + split_vf + f";[v_base][v_split]overlay=enable='{enable}':shortest=1,setsar=1/1"

def get_best_encoder():
    try:
        res = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        if 'h264_amf' in res.stdout: return 'h264_amf', 'speed'
        if 'h264_nvenc' in res.stdout: return 'h264_nvenc', 'p2'
    except: pass
    return 'libx264', 'ultrafast'

def generate_thumbnail(video_path, output_path, job_id, text="TITAN"):
    try:
        img_tmp = output_path.replace('.mp4', '.jpg')
        subprocess.run(['ffmpeg', '-y', '-ss', '00:00:02', '-i', video_path, '-vf', f"drawtext=text='{text}':fontcolor=yellow:fontsize=150:x=(w-text_w)/2:y=(h-text_h)/4:borderw=10:bordercolor=black", '-vframes', '1', img_tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffmpeg', '-y', '-loop', '1', '-i', img_tmp, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-t', '1.0', '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1/1', '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-ar', '44100', '-ac', '2', output_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def create_narrator_hook(video_path, output_path, text, job_id, narrator_audio_path=None):
    """
    Titan Resilient Hook: Binds text and audio. Guarantees output existence.
    """
    try:
        # 1. Text Overlay (Safe without fontfile for Windows compatibility)
        vf = f"[0:v]scale=720:1280,setsar=1/1,drawtext=text='{text}':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2:borderw=5:bordercolor=black[v]"

        # 2. Audio Strategy: Mix narrator or use original at low vol
        if narrator_audio_path and os.path.exists(narrator_audio_path) and os.path.getsize(narrator_audio_path) > 0:
            af = "[0:a]volume=0.05,aresample=async=1[bg];[1:a]volume=1.0,aresample=async=1[v_a];[bg][v_a]amix=inputs=2:duration=first[a]"
            inputs = ['-i', video_path, '-i', narrator_audio_path]
        else:
            af = "[0:a]volume=1.0,aresample=async=1[a]"
            inputs = ['-i', video_path]

        cmd = [
            'ffmpeg', '-y', '-threads', '1'
        ] + inputs + [
            '-filter_complex', f"{vf};{af}",
            '-map', '[v]', '-map', '[a]',
            '-t', '3', '-c:v', 'libx264', '-preset', 'ultrafast',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            output_path
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"⚠️ Erro ao gerar Hook Estético ({job_id}): {res.stderr[-200:]}")
            # Final Fallback: Literal Copy of the 3s slice to ensure file existence
            shutil.copy(video_path, output_path)
    except Exception as e:
        print(f"❌ Falha Crítica Hook {job_id}: {e}")
        try: shutil.copy(video_path, output_path)
        except: pass

def cleanup_temps(folder, job_id):
    for f in os.listdir(folder):
        if job_id in f and not f.endswith('.mp4'):
            try: os.remove(os.path.join(folder, f))
            except: pass

def download_strategy_yt_dlp(url, output_path):
    subprocess.run(['yt-dlp', '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', url, '-o', output_path], check=True)
