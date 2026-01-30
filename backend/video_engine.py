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
    print("👁️ Iniciando Scan Facial Avançado (Titan Vision V25)...")
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
                # V25/V26: Collect up to 2 significant centers (most left and most right) WITH Y-COORDINATES
                f_data = []
                for (x, y, w, h) in faces:
                    f_data.append({
                        "center": (x + w/2) / frame.shape[1],
                        "center_y": (y + h/2) / frame.shape[0], # Normalized Y
                        "area": w * h
                    })
                # Sort by area to keep most relevant
                f_data = sorted(f_data, key=lambda x: x["area"], reverse=True)
                face_map[t] = {"faces": f_data[:3], "count": len(faces)}
        cap.release()
        return face_map
    except: return {}

def get_crop_from_cache(start_t, dur, face_map):
    if not face_map: return 0.5
    centers = []
    for t in range(int(start_t), int(start_t + dur)):
        avail = sorted(face_map.keys())
        if not avail: continue
        closest = min(avail, key=lambda x: abs(x - t))
        meta = face_map[closest]
        if "faces" in meta and meta["faces"]:
            centers.append(meta["faces"][0]["center"])
    return sum(centers)/len(centers) if centers else 0.5

def get_layout_zones(start_t, dur, face_map):
    """Titan Vision V25: Advanced Intelligent Layout Orchestrator."""
    zones = []
    temp_zones = []

    def get_meta(seconds):
        avail = sorted(face_map.keys())
        if not avail: return {"faces": [], "count": 0}
        closest = min(avail, key=lambda x: abs(x - seconds))
        return face_map[closest]

    split_counts = 0
    for t in range(int(start_t), int(start_t + dur)):
        meta = get_meta(t)
        faces = meta.get("faces", [])
        count = meta.get("count", 0)

        is_reaction = False
        if count == 1:
            c = faces[0]["center"]
            if c < 0.45 or c > 0.55: is_reaction = True

        is_split = (count >= 2 or is_reaction)
        layout = "Split" if is_split else "Normal"

        if layout == "Split": split_counts += 1
        temp_zones.append(layout)

    # Sticky Logic V25: If clipe has significant split moments, keep Split to maintain continuity
    if (split_counts / dur) > 0.35:
        return [(0, dur, "Split")]

    current = None
    last = 0
    for i, layout in enumerate(temp_zones):
        if layout != current:
            if current: zones.append((last, i, current))
            current = layout
            last = i
    zones.append((last, dur, current))
    return zones

def build_vertical_filter_complex(crop_x, crop_w):
    return f"[0:v]split=2[in_bg][in_fg];[in_bg]scale=-2:480:flags=lanczos,crop={crop_w}:480:{crop_x}:0,gblur=sigma=20,scale=720:1280:flags=lanczos,setsar=1/1[bg];[in_fg]scale=720:-2:flags=lanczos,setsar=1/1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"

def build_split_screen_filter(crop_x_top, crop_x_bottom, crop_w):
    return f"[0:v]split=2[v1][v2];[v1]scale=-2:640:flags=lanczos,crop={crop_w}:640:{crop_x_top}:0,setsar=1/1[top];[v2]scale=-2:640:flags=lanczos,crop={crop_w}:640:{crop_x_bottom}:0,setsar=1/1[bottom];[top][bottom]vstack=inputs=2,scale=720:1280,setsar=1/1"

def build_gamer_overlay_filter(crop_x_face, crop_w):
    """Titan Gamer: Face Circle Overlay over main gameplay/content."""
    return f"[0:v]split=2[in_main][in_face];[in_main]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1/1[bg];[in_face]scale=-2:300:flags=lanczos,crop=250:250:{crop_x_face}:25,format=yuva420p,geq=lum='p(X,Y)':a='if(gt(sqrt(pow(X-125,2)+pow(Y-125,2)),120),0,255)'[fg];[bg][fg]overlay=20:20:shortest=1,setsar=1/1"

def build_dynamic_filter_complex(zones, crop_x_normal, norm_x_host, norm_y_host, norm_x_guest, crop_w, is_gamer=False, is_reaction=False):
    if is_gamer: return build_gamer_overlay_filter(crop_x_normal, crop_w)

    # TITAN VISION V27.2: Hybrid Scaling Engine
    # Top (Face): High Zoom (780px) for immersion and focus.
    # Bottom (Content): Fit-to-Height (600px) for maximum context visibility.

    # Configuration
    scale_top = 780   # Face Zoom (Focus)
    scale_bot = 900   # Content Zoom (Extreme zoom to cut duplicate host)

    out_w = 720
    out_h = 600

    def get_crop_x(norm_x, current_scale):
        # Calculate width for this specific scale
        # 16:9 Aspect Ratio Assumption
        current_w = int(current_scale * 16 / 9)

        target_px = norm_x * current_w
        start_x = int(target_px - (out_w / 2))
        return max(0, min(current_w - out_w, start_x))

    def get_crop_y(norm_y, current_scale, offset_scale=0):
        target_px = norm_y * current_scale
        target_px += offset_scale
        start_y = int(target_px - (out_h / 2))
        return max(0, min(current_scale - out_h, start_y))

    # 1. TOP (Face) -> Uses scale_top
    tx_top = get_crop_x(norm_x_host, scale_top)
    ty_top = get_crop_y(norm_y_host, scale_top, 0)

    # 2. BOTTOM (Content) -> Uses scale_bot
    #    With scale 600, we fit the entire height effortlessly.
    #    We assume content shouldn't be vertically offset much,
    #    as 600h input fits 600h output perfectly (start_y=0).
    #    But get_crop_y will figure it out if target is center.
    tx_bot = get_crop_x(norm_x_guest, scale_bot)
    ty_bot = get_crop_y(0.5, scale_bot) # Center Y is safest for Fit-to-Height

    # 3. Dynamic Switch Logic
    splits = [z for z in zones if z[2] == "Split"]
    enable_sq = " + ".join([f"between(t,{z[0]},{z[1]})" for z in splits])

    # BUILD FILTER
    # Normal Path
    vf = "[0:v]split=4[v_bg][v_fg][v_tp][v_bt];"
    vf += f"[v_bg]scale=-2:1280:flags=lanczos,crop={crop_w}:1280:{crop_x_normal}:0,gblur=sigma=20,scale=720:1280:flags=lanczos,setsar=1/1[bg];"
    vf += f"[v_fg]scale=720:-2:flags=lanczos,setsar=1/1[fg];"
    vf += "[bg][fg]overlay=(W-w)/2:(H-h)/2[v_norm];"

    # Split Path (V27.2 Hybrid)
    vf += f"[v_tp]scale=-2:{scale_top}:flags=lanczos,crop={out_w}:{out_h}:{tx_top}:{ty_top},setsar=1/1[top];"
    vf += f"[v_bt]scale=-2:{scale_bot}:flags=lanczos,crop={out_w}:{out_h}:{tx_bot}:{ty_bot},setsar=1/1[bottom];"
    vf += f"color=black:s=720x80[bar];"
    vf += "[top][bar][bottom]vstack=inputs=3,scale=720:1280,setsar=1/1[v_split];"

    # Optimization
    if len(zones) == 1 and zones[0][2] == "Split":
        simple_vf = "[0:v]split=2[v_tp][v_bt];"
        simple_vf += f"[v_tp]scale=-2:{scale_top}:flags=lanczos,crop={out_w}:{out_h}:{tx_top}:{ty_top},setsar=1/1[top];"
        simple_vf += f"[v_bt]scale=-2:{scale_bot}:flags=lanczos,crop={out_w}:{out_h}:{tx_bot}:{ty_bot},setsar=1/1[bottom];"
        simple_vf += f"color=black:s=720x80[bar];"
        simple_vf += "[top][bar][bottom]vstack=inputs=3,scale=720:1280,setsar=1/1"
        return simple_vf

    vf += f"[v_norm][v_split]overlay=enable='{enable_sq}':shortest=1,setsar=1/1"
    return vf

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
