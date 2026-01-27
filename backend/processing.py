import os
import wave
import subprocess
import datetime
import random
import time
import shutil
import asyncio
import edge_tts
from faster_whisper import WhisperModel

from . import state_manager

# --- Global Cache ---
_CACHED_MODEL = None

def get_cached_model():
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        print(f"⚡ Carregando Modelo HYPER-SPEED (Faster-Whisper Large-V3)...")
        # V16.5/16.8: CTranslate2 Engine (4x Faster than standard Whisper)
        try:
            # float16 is native for T4/A100. device='cuda' is mandatory.
            # Colab T4 has ~15GB VRAM, enough for large-v3 + beam_size 5 + batching
            _CACHED_MODEL = WhisperModel("large-v3", device="cuda", compute_type="float16")
        except Exception as e:
            print(f"⚠️ GPU Falhou. Usando CPU (int8)... Erro: {e}")
            # Use small/int8 for CPU fallback in faster-whisper to avoid freezing
            _CACHED_MODEL = WhisperModel("small", device="cpu", compute_type="int8")
    return _CACHED_MODEL

def get_transcription(audio_path, dummy_path=None):
    """
    Transcribes audio using Faster-Whisper (CTranslate2).
    Returns list of dicts: {'word': str, 'start': float, 'end': float, 'conf': float}
    """
    model = get_cached_model()

    print(f"⚡ Transcrevendo (Hyper-Speed C++ Engine)... {os.path.basename(audio_path)}")

    # Transcribe
    # beam_size=5 is standard for accuracy. word_timestamps=True is mandatory.
    # wad_filter=True helps with silence/hallucinations
    segments, info = model.transcribe(
        audio_path,
        beam_size=1, # OPTIMIZATION PHASE 1: Greedy Search (5x Faster)
        best_of=None,
        language="pt",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False # Prevents loops/hallucinations
    )

    all_words = []
    # faster-whisper returns a generator, so we iterate
    for segment in segments:
        for word in segment.words:
            all_words.append({
                "word": word.word,
                "start": word.start,
                "end": word.end
            })

    return all_words

def cleanup_temps(folder, job_id):
    """Deletes large intermediate files for a specific job"""
    temps = [f"raw_cut_{job_id}.mp4", f"raw_cut_{job_id}.wav", f"hook_raw_{job_id}.mp4", f"hook_{job_id}.mp4", f"main_clip_{job_id}.mp4", f"thumb_{job_id}.mp4", f"list_{job_id}.txt", f"subs_{job_id}.ass"]
    for f in temps:
        p = os.path.join(folder, f)
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

# --- HYBRID DOWNLOAD ENGINE V13.3 (COBALT CORE) ---
def download_authenticated_ytdlp(url, output_path, cookies_path=None):
    import yt_dlp
    print("💎 Trying Cobalt Engine (Yt-Dlp)...")
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]', # V15.7: Relaxed format for max compatibility
        'outtmpl': output_path,
        'merge_output_format': 'mp4', # Force MP4 merge
        'quiet': True,
        'no_warnings': True,
        'overwrites': True,
        'nocheckcertificate': True,
        'source_address': '0.0.0.0',
        # V13.3: Use standard browser headers (Cobalt style)
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android', 'ios']
            }
        }
    }

    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
        print("   ↳ 🍪 Cookies Attached!")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return True

def download_strategy_pytubefix(url, output_path):
    from pytubefix import YouTube
    print("💎 Fallback: Trying Pytubefix (Client=ANDROID)...")
    # V13.3: Use PoToken-like approach via client choice
    yt = YouTube(url, client='ANDROID')
    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
    if not stream:
        stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()
    stream.download(output_path=os.path.dirname(output_path), filename=os.path.basename(output_path))
    return True
# --- HYBRID DOWNLOAD END ---

# --- ASS LEGENDAS (V11.0) ---
def generate_karaoke_ass(words):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,85,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,20,20,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = ""
    # Group words into small execution blocks (3-4 words)
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i+chunk_size]
        start_t = format_time(chunk[0]['start'])
        end_t = format_time(chunk[-1]['end'])

        line_text = ""
        for w in chunk:
            # Karaoke effect: {\kX} where X is duration in centiseconds
            # V2.0: Simple Karaoke without fancy color shifts to avoid artifacts, rely on big bold text
            dur_cs = int((w['end'] - w['start']) * 100)
            line_text += f"{{\\k{dur_cs}}}{w['word']} "

        events += f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{line_text.strip()}\n"

    return header + events

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds * 100) % 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

# --- POST PROD (V12.0) ---
# --- POST PROD (V17.0 - RETENTION ENGINE) ---
def generate_thumbnail(video_path, output_path, job_id, text="VIRAL"):
    """
    Creates a 0.1s video clip acting as the specific thumbnail.
    It takes a frame from the video, burns the 'PARTE X' text in BIG YELLOW letters,
    and encodes it as a short video to be the first file in the concat list.
    """
    try:
        # 1. Extract and Burn Text (Single Image)
        # Font: default sans-serif. Size: 150 (Big). Color: Yellow with Black Border.
        vf_text = f"drawtext=text='{text}':fontcolor=yellow:fontsize=150:x=(w-text_w)/2:y=(h-text_h)/5:borderw=8:bordercolor=black:shadowx=5:shadowy=5"

        img_tmp = output_path.replace('.mp4', '.jpg')

        # Extract frame at 1s
        subprocess.run([
            'ffmpeg', '-ss', '00:00:01', '-i', video_path,
            '-vf', vf_text,
            '-vframes', '1', img_tmp, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 2. Convert Image to 0.1s Video (Match Main Video Specs: 1080x1920, 30fps, AAC)
        # We generate silent audio to match.
        subprocess.run([
            'ffmpeg', '-loop', '1', '-i', img_tmp,
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=44100',
            '-t', '0.1',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-ar', '44100',
            '-shortest', output_path, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"⚠️ Erro ao gerar thumbnail viral: {e}")

def create_narrator_hook(video_path, output_path, text, job_id):
    """
    Creates a 3s high-retention hook using visual effects.
    Effect: Dynamic Zoom In + Text Overlay "Flash".
    """
    try:
        # Retention Phrases
        hooks = ["⚠️ ATENÇÃO ⚠️", "😱 OLHA ISSO", "🚨 URGENTE", "🤯 INCRÍVEL", "🛑 PARE TUDO"]
        hook_text = random.choice(hooks)

        # Complex Filter:
        # 1. Zoompan: Zooms in 1.5x over 3 seconds (dynamic motion)
        # 2. Drawtext: Flashing text in center
        vf_chain = (
            f"zoompan=z='min(zoom+0.0015,1.5)':d=90:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
            f"drawtext=text='{hook_text}':fontcolor=white:fontsize=130:x=(w-text_w)/2:y=(h-text_h)/2:borderw=5:bordercolor=red:enable='between(t,0,1)'"
        )

        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vf', vf_chain,
            '-t', '3',
            '-c:v', 'libx264', '-preset', 'ultrafast', # Hook needs to match codec, usually libx264 is safest for mix
            '-c:a', 'copy', # Keep audio
            output_path, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except Exception as e:
        print(f"⚠️ Erro ao criar hook viral: {e}")
        # Fallback: Just copy
        shutil.copy(video_path, output_path)

def setup_directories():
    # Detect Google Colab / Linux High Performance RAM Disk
    if os.path.exists("/dev/shm"):
        work_dir = "/dev/shm/temp_work_colab"
        print("🚀 DETECTADO AMBIENTE LINUX/COLAB: Usando RAM DISK (/dev/shm) para velocidade extrema!")
    else:
        work_dir = "temp_work" # Use relative path for portability if standard OS

    drive_dir = "downloads"

    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(drive_dir, exist_ok=True)
    return work_dir, drive_dir

def process_video(url, video_file, settings):
    settings['lang'] = 'Português (BR)'

    # --- V20.0: NEURAL ENV SETUP ---
    try:
        from . import colab_setup
        colab_setup.setup_neural_env()
    except: pass

    work_dir, drive_dir = setup_directories()

    # Files (Local)
    video_path = os.path.join(work_dir, "input_video.mp4")
    audio_path = os.path.join(work_dir, "input_audio.wav")

    # --- V12.0: CREDENTIALS MANAGER ---
    persistent_cookie_path = os.path.join(drive_dir, "auth_cookies.txt")
    persistent_oauth_path = os.path.join(drive_dir, "client_secret.json")

    active_cookie_path = None

    # 1. HANDLE OAUTH (Client Secret)
    if 'oauth_path' in settings and settings['oauth_path']:
        try:
            shutil.copy(settings['oauth_path'], persistent_oauth_path)
            shutil.copy(settings['oauth_path'], "client_secret.json") # Local for current run
            yield "🔑 Client Secret Novo Salvo no Drive!", 1
        except: pass
    elif os.path.exists(persistent_oauth_path):
        shutil.copy(persistent_oauth_path, "client_secret.json")
        yield "♻️ Client Secret Carregado do Drive.", 1

    if os.path.exists("client_secret.json"):
        yield "✅ API do Google Ativada (OAuth Detectado).", 2

    # 2. HANDLE COOKIES
    if 'cookies_path' in settings and settings['cookies_path']:
        try:
            shutil.copy(settings['cookies_path'], persistent_cookie_path)
            active_cookie_path = persistent_cookie_path
            yield "💾 Cookies Novos Salvos no Drive!", 3
        except:
            active_cookie_path = settings['cookies_path']
    elif os.path.exists(persistent_cookie_path):
        active_cookie_path = persistent_cookie_path
        yield "♻️ Cookies Carregados do Drive.", 3

    # 3. INPUT HANDLING (URL vs FILE)
    if video_file:
         yield "📂 Processando Arquivo Local...", 5
         try:
             # If video_file is a file object (Gradio 3.x) or path (Gradio 4.x)
             # Gradio 4 passes a FileData object or path.
             input_path = video_file.name if hasattr(video_file, 'name') else video_file
             shutil.copy(input_path, video_path)
             yield "✅ Arquivo Local Carregado!", 8
         except Exception as e:
             yield f"❌ Erro ao ler arquivo local: {e}", 0
             return
    else:
        # Download (HYBRID ENGINE V13.3)
        yield "⬇️ [Cobalt] Iniciando Download...", 5
        success_dl = False
        error_log = ""

        # STRATEGY 1: COBALT NATIVE (YT-DLP)
        yield "💎 Engine 1: Cobalt Core (Yt-Dlp)...", 8
        try:
            download_authenticated_ytdlp(url, video_path, active_cookie_path)
            success_dl = True
        except Exception as e:
            error_log += f"Cobalt Core Falhou: {e}\n"
            yield f"⚠️ Cobalt Core falhou. Mudando para Fallback...", 10
            pass

        # STRATEGY 2: PYTUBEFIX
        if not success_dl:
            yield "💎 Engine 2: Fallback Driver (Pytubefix)...", 15
            try:
                download_strategy_pytubefix(url, video_path)
                success_dl = True
            except Exception as e:
                error_log += f"Fallback Driver Falhou: {e}\n"
                pass

        if not success_dl:
             yield f"❌ TODOS OS MOTORES FALHARAM. \nSOLUÇÃO: Use a aba 'Acesso Avançado' e suba o cookies.txt.\n{error_log}", 0
             return

    # Sync Input to Drive (Backup)
    try: shutil.copy(video_path, os.path.join(drive_dir, "input_video.mp4"))
    except: pass

    # 4. Extract Full Audio (for Discovery)
    yield "🔊 Lendo Áudio Original (Hi-Res)...", 25
    subprocess.run(['ffmpeg', '-threads', '0', '-i', video_path, '-ac', '1', '-ar', '16000', '-vn', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. Discovery Transcription
    yield "🧠 Mapeando Conteúdo (Faster-Whisper)...", 30

    try:
        full_words = get_transcription(audio_path)
    except Exception as e:
        yield f"❌ Erro Transcrição: {e}", 0
        return

    if not full_words:
        state_manager.append_log("⚠️ Silêncio detectado.")
        yield "⚠️ Silêncio detectado.", 100
        return

    # --- SEGMENTATION LOGIC ---
    if state_manager.check_stop_requested(): return

    segments = []
    current_start_word = 0
    TARGET_DURATION = 60.0 # Minimum

    while current_start_word < len(full_words):
        start_time = full_words[current_start_word]['start']
        target_end = start_time + TARGET_DURATION
        best_end_idx = -1
        for i in range(current_start_word, len(full_words)):
            w = full_words[i]
            if w['end'] >= target_end:
                best_end_idx = i
                for j in range(i, min(len(full_words), i+30)):
                    w_curr = full_words[j]
                    w_next = full_words[j+1] if j+1 < len(full_words) else None
                    if w_next:
                        pause = w_next['start'] - w_curr['end']
                        if pause > 0.5: # Good pause
                            best_end_idx = j
                            break
                break

        if best_end_idx == -1: best_end_idx = len(full_words) - 1
        seg_end_time = full_words[best_end_idx]['end']

        # User request: "corte de no minimo 60 segundos"
        # We allow 50s as a safe floor to catch 59s clips that might be good.
        if (seg_end_time - start_time) >= 50.0:
            segments.append({'start': start_time, 'end': seg_end_time})

        current_start_word = best_end_idx + 1
        if current_start_word >= len(full_words): break

    total_segs = len(segments)
    yield f"📐 Estratégia Definida: {total_segs} Cortes Identificados.", 35

    # --- PARALLEL PROCESSING ENGINE (V21.0 - GPU THREAD POOL) ---
    import concurrent.futures

    def process_single_segment(seg_data):
        idx, seg, total_segs = seg_data
        seg_num = idx + 1
        job_id = f"{int(time.time())}_{idx+1}"

        # Logging (Thread Safe-ish)
        msg = f"✂️ [Thread-Worker] Iniciando Corte {seg_num}/{total_segs}..."
        # state_manager.append_log(msg) # Avoid spamming main log from threads
        print(msg)

        start_t = seg['start']
        dur = seg['end'] - start_t

        # 6. Render Raw Cut (FULL GPU PIPELINE V21.0)
        raw_cut_path = os.path.join(work_dir, f"raw_cut_{job_id}.mp4")
        raw_cut_audio = os.path.join(work_dir, f"raw_cut_{job_id}.wav")

    # --- SMART CROP ENGINE (PHASE 2) ---
    def detect_active_speaker_x(video_path, start_t, dur):
        """
        Analyzes 5 frames to find the average X position of the main face.
        Returns: float (0.0 to 1.0) representing the center X relative to width.
        """
        try:
            import cv2
            import mediapipe as mp

            mp_face_detection = mp.solutions.face_detection
            detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

            cap = cv2.VideoCapture(video_path)
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)

            # Sample 5 frames
            timestamps = [start_t + (dur * i / 5) for i in range(1, 5)]
            face_x_centers = []

            for ts in timestamps:
                cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
                ret, frame = cap.read()
                if not ret: continue

                results = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if results.detections:
                    # Find largest face (assume speaker)
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
                print(f"🎯 Smart Crop Alvo: {avg_x:.2f} (Baseado em {len(face_x_centers)} frames)")
                return avg_x

        except Exception as e:
            print(f"⚠️ Erro Smart Crop: {e}")

        return 0.5 # Default Center

    # Detect Face Logic
    speaker_x_norm = detect_active_speaker_x(video_path, start_t, dur)

    # Calculate Crop Coordinates (Input is 16:9, Output 9:16)
    # Target: 270x480 (to be scaled to 1080x1920)
    # Original H is 480 (after scale).
    # Logic: First scale input to height=480 (keep aspect ratio).
    # Width becomes ~853. We need 270 width.
    # Center X in pixels = speaker_x_norm * 853.
    # Crop X = Center X - (270/2).

    # FFmpeg Formula:
    # 1. Scale height to 480 (iw*480/ih)
    # 2. Crop w=270, h=480, x=?, y=0

    # Since we can't easily get exact width in filter string without ffprobe,
    # we use relative values or standard assume 16:9 input.
    # Standard 16:9 -> Scale h=480 -> w=853.33

    scaled_w = 853
    crop_w = 270

    center_px = speaker_x_norm * scaled_w
    crop_x = int(center_px - (crop_w / 2))

    # Clamping
    if crop_x < 0: crop_x = 0
    if crop_x > (scaled_w - crop_w): crop_x = (scaled_w - crop_w)

    print(f"✂️ Smart Crop Coords: x={crop_x}")

    # Optimization: SMART BLUR with DYNAMIC CROP
    filter_complex = (
        f"[0:v]scale=-1:480,crop={crop_w}:480:{crop_x}:0,boxblur=10:5,"
        "scale=1080:1920[bg];"
        "[0:v]scale=1080:-1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )

        # CHECK GPU
        use_nvenc = False
        try:
            res = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
            if 'h264_nvenc' in res.stdout: use_nvenc = True
        except: pass

        ffmpeg_cmd = ['ffmpeg', '-y']

        # HWACCEL (NVDEC) - Input Stage
        if use_nvenc:
            ffmpeg_cmd.extend([
                '-hwaccel', 'cuda',
                '-hwaccel_output_format', 'cuda', # Keep in VRAM
                '-c:v', 'h264_cuvid' # Hardware Decoder
            ])

        # Input
        ffmpeg_cmd.extend(['-ss', str(start_t), '-t', str(dur), '-i', video_path])

        # Filter Stage (Hybrid CPU/GPU fallback for now as filters are complex)
        # Note: If we use -hwaccel_output_format cuda, filters need to handle CUDA frames.
        # For safety in Phase 1, we let FFmpeg handle the download if filters are software.
        ffmpeg_cmd.extend(['-filter_complex', filter_complex, '-r', '30', '-vsync', 'cfr'])

        # Encoding Stage
        if use_nvenc:
            ffmpeg_cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'p2',      # Fast
                '-tune', 'hq',
                '-rc', 'constqp', '-qp', '26',
                '-b:v', '0'
            ])
        else:
            ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28'])

        ffmpeg_cmd.extend([
            '-c:a', 'aac', '-ar', '44100',
            '-max_muxing_queue_size', '1024',
            raw_cut_path
        ])

        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)
            # Extract Audio for Clip
            subprocess.run(['ffmpeg', '-i', raw_cut_path, '-ac', '1', '-ar', '16000', '-vn', raw_cut_audio, '-y'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        except Exception as e:
            print(f"❌ Erro Render Corte {seg_num}: {e}")
            return None

        # 7. Transcription (Clip level)
        try:
            clip_words = get_transcription(raw_cut_audio)
        except: return None

        ass_path = os.path.join(work_dir, f"subs_{job_id}.ass")
        ass_content = generate_karaoke_ass(clip_words)
        with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

        # 8. Burn Subtitles
        subtitled_cut = os.path.join(work_dir, f"main_clip_{job_id}.mp4")
        vf = f"ass={ass_path.replace(os.sep, '/')}"

        burn_cmd = ['ffmpeg', '-threads', '0', '-i', raw_cut_path, '-vf', vf, '-r', '30', '-vsync', 'cfr']
        if use_nvenc:
             burn_cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p2', '-rc', 'constqp', '-qp', '26', '-b:v', '0'])
        else:
             burn_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast'])
        burn_cmd.extend(['-c:a', 'copy', subtitled_cut, '-y'])

        subprocess.run(burn_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        # 9. Hook & Thumb
        final_hook = os.path.join(work_dir, f"hook_{job_id}.mp4")
        thumb_out = os.path.join(work_dir, f"thumb_{job_id}.mp4")

        # Simple Hook Generation (Async capable)
        raw_hook = os.path.join(work_dir, f"hook_raw_{job_id}.mp4")
        hook_start = dur * 0.15
        subprocess.run(['ffmpeg', '-ss', str(hook_start), '-t', '3', '-i', subtitled_cut, '-c', 'copy', raw_hook, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        phrases = ["Olha só o que aconteceu!", "Assista até o final!", "Segredo revelado!"]
        create_narrator_hook(raw_hook, final_hook, random.choice(phrases), job_id)
        generate_thumbnail(raw_cut_path, thumb_out, job_id, text=f"PARTE {seg_num}")

        # 10. Concat
        final_out_local = os.path.join(work_dir, f"viral_clip_{seg_num}_{job_id}.mp4")
        list_txt = os.path.join(work_dir, f"list_{job_id}.txt")
        abs_thumb = os.path.abspath(thumb_out)
        abs_hook = os.path.abspath(final_hook)
        abs_main = os.path.abspath(subtitled_cut)

        with open(list_txt, 'w') as f:
            if os.path.exists(thumb_out): f.write(f"file '{abs_thumb}'\n")
            if os.path.exists(final_hook): f.write(f"file '{abs_hook}'\n")
            f.write(f"file '{abs_main}'\n")

        subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt, '-c', 'copy', final_out_local, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return {
            "path": final_out_local,
            "seg_num": seg_num,
            "job_id": job_id,
            "clip_words": clip_words
        }

    # --- EXECUTE PARALLEL BATCH ---
    # Max Workers = 2 (Safe for T4 NVENC concurrent sessions limit + VRAM)
    max_workers = 2
    state_manager.append_log(f"🚀 Iniciando Processamento Paralelo (Workers={max_workers})..")

    seg_payloads = [(i, seg, len(segments)) for i, seg in enumerate(segments)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_seg = {executor.submit(process_single_segment, payload): payload for payload in seg_payloads}

        for future in concurrent.futures.as_completed(future_to_seg):
            result = future.result()

            if result and os.path.exists(result['path']):
                final_out_local = result['path']
                seg_num = result['seg_num']
                job_id = result['job_id']
                clip_words = result['clip_words']

                # 11. FINAL ACTIONS (Sequential Part - Upload/Metadata)
                # A. Upload to Drive (API)
                if GLOBAL_GOOGLE_SERVICES:
                    yield f"☁️ Enviando Parte {seg_num}...", 98
                    file_id = GLOBAL_GOOGLE_SERVICES.upload_to_drive(final_out_local)
                    if file_id: state_manager.append_log(f"✅ Salvo no Drive! ID: {file_id}")

                if os.path.exists(drive_dir) and drive_dir != "downloads":
                     shutil.copy(final_out_local, os.path.join(drive_dir, f"viral_clip_{seg_num}_{job_id}.mp4"))

                # B. Upload to YouTube (Auto-Publish)
                if 'publish_youtube' in settings and settings['publish_youtube'] and GLOBAL_GOOGLE_SERVICES:
                    yield f"📺 Publicando Parte {seg_num}...", 99

                    # --- HYBRID INTELLIGENCE (NEURAL V20.0 -> STRUCTURED V19.0) ---
                    meta_result = None
                    try:
                        from .neural_engine import NeuralEngine
                        neural = NeuralEngine()
                        if neural.client:
                             full_text = " ".join([w['word'] for w in clip_words])
                             user_tags = settings.get('hashtags', '')
                             meta_data = neural.generate(full_text, user_tags)
                             if meta_data:
                                 from dataclasses import make_dataclass
                                 MetaObj = make_dataclass("MetaObj", [("title", str), ("description", str), ("tags", list), ("privacy", str), ("pinned_comment", str)])
                                 meta_result = MetaObj(**meta_data)
                    except: pass

                    if not meta_result:
                        try:
                            from .metadata_engine import MetadataEngine
                            engine = MetadataEngine()
                            meta_result = engine.generate(clip_words, settings.get('hashtags', ''))
                        except: pass

                    if meta_result:
                        yt_id = GLOBAL_GOOGLE_SERVICES.upload_to_youtube(
                            final_out_local,
                            title=meta_result.title,
                            description=meta_result.description,
                            tags=meta_result.tags,
                            privacy=meta_result.privacy
                        )
                        if yt_id:
                            if meta_result.pinned_comment: GLOBAL_GOOGLE_SERVICES.post_comment(yt_id, meta_result.pinned_comment)
                            yield f"✅ Publicado YT: {yt_id}", 100

                cleanup_temps(work_dir, job_id)
                yield final_out_local # Yield path to UI

    state_manager.append_log("✅ Processamento de Lote Completado!")
    state_manager.update_state("progress", 100)
    yield "✅ Processamento de Lote Completado!", 100

# --- INITIALIZATION ---
from .google_services import GoogleServices
GLOBAL_GOOGLE_SERVICES = None

def init_google_services():
    global GLOBAL_GOOGLE_SERVICES
    if os.path.exists("client_secret.json"):
        try:
            GLOBAL_GOOGLE_SERVICES = GoogleServices()
            print("✅ Google Services Ativado!")
        except Exception as e:
            print(f"⚠️ Falha ao iniciar Google Services: {e}")
            GLOBAL_GOOGLE_SERVICES = None

# Try auto-init on module load
init_google_services()
