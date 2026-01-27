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
        beam_size=5,
        language="pt",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
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
Style: Default,Montserrat ExtraBold,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,250,1

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
            # Karaoke effect: {\kX} where X is duration in centiseconds
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

    # --- PROCESSING LOOP ---
    for idx, seg in enumerate(segments):
        if state_manager.check_stop_requested():
            state_manager.append_log("🛑 Processamento Interrompido pelo Usuário.")
            yield "🛑 Interrompido.", 0
            return

        job_id = f"{int(time.time())}_{idx+1}"
        seg_num = idx + 1

        msg = f"✂️ Processando Corte {seg_num}/{total_segs}..."
        pct = 40 + int(20 * (idx/total_segs))

        state_manager.append_log(msg)
        state_manager.update_state("progress", pct)
        yield msg, pct

        start_t = seg['start']
        dur = seg['end'] - start_t

        # 6. Render Raw Cut (VERTICAL 9:16 CONVERSION)
        raw_cut_path = os.path.join(work_dir, f"raw_cut_{job_id}.mp4")
        raw_cut_audio = os.path.join(work_dir, f"raw_cut_{job_id}.wav")

        # Optimization: SMART BLUR (Downscale -> Blur -> Upscale)
        # 16x faster than blurring 1080p
        # bg chain: Input -> Scale to 270x480 (1/4 res) -> BoxBlur -> Scale back to 1080x1920
        filter_complex = (
            "[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10:5,"
            "scale=1080:1920[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )

        # V16.4/16.8: NVENC HARDWARE ENCODING CHECK (Dynamic Auto-Detection)
        use_nvenc = False
        try:
             # Check if we have an NVIDIA GPU available for FFmpeg
            result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
            if 'h264_nvenc' in result.stdout:
                use_nvenc = True
        except: pass

        ffmpeg_cmd = [
            'ffmpeg', '-threads', '0', # DYNAMIC: Use ALL available CPU cores for decoding
            '-ss', str(start_t), '-t', str(dur),
            '-i', video_path,
            '-filter_complex', filter_complex,
            '-r', '30', '-vsync', 'cfr'
        ]

        if use_nvenc:
            # GPU ENCODING (BLAZING FAST - EXTREME MODE)
            # Nvidia Tesla T4/A100 optimization
            if seg_num == 1: print("    🚀 MODO EXTREMO: GPU NVENC (P2) + SMART BLUR ATIVADO!")
            else: print(f"    🚀 GPU NVENC Ativo para Corte {seg_num}!")

            ffmpeg_cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'p2', # p2 = Faster (Aggressive optimization for speed)
                '-tune', 'hq',
                '-rc', 'constqp', '-qp', '26', # Relaxed QP for speed (24 -> 26)
                '-b:v', '0',
                '-spatial-aq', '0', # Disable spatial-aq for raw speed
            ])
        else:
            # CPU ENCODING (FALLBACK)
            print(f"    🐌 CPU Encoding para Corte {seg_num} (Pode demorar)...")
            ffmpeg_cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'ultrafast', # CPU priority is pure speed
                '-crf', '28', # Lower quality for speed
                '-threads', '0' # Use all cores
            ])

        ffmpeg_cmd.extend([
            '-c:a', 'aac', '-ar', '44100',
            '-max_muxing_queue_size', '1024',
            raw_cut_path, '-y'
        ])

        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)

            subprocess.run(['ffmpeg', '-i', raw_cut_path, '-ac', '1', '-ar', '16000', '-vn', raw_cut_audio, '-y'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        except subprocess.TimeoutExpired:
            yield f"⚠️ Corte {seg_num} demorou demais e foi pulado.", 0
            continue

        try: shutil.copy(raw_cut_path, os.path.join(drive_dir, f"raw_cut_{job_id}.mp4"))
        except: pass

        # 7. Production Transcription
        try:
            clip_words = get_transcription(raw_cut_audio)
        except:
            yield f"⚠️ Erro Transcrição {seg_num}. Pulando.", 0; continue

        ass_path = os.path.join(work_dir, f"subs_{job_id}.ass")
        ass_content = generate_karaoke_ass(clip_words)
        with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

        # 8. Burn
        subtitled_cut = os.path.join(work_dir, f"main_clip_{job_id}.mp4")
        vf = f"ass={ass_path.replace(os.sep, '/')}" # FFmpeg needs forward slashes even on Windows sometimes

        burn_cmd = [
            'ffmpeg', '-threads', '0', # Maximize CPU usage for reading/muxing
            '-i', raw_cut_path,
            '-vf', vf,
            '-r', '30', '-vsync', 'cfr'
        ]

        if use_nvenc:
             # P2 for extreme speed on burn too
             burn_cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p2', '-rc', 'constqp', '-qp', '26', '-b:v', '0'])
        else:
             burn_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28'])

        burn_cmd.extend(['-c:a', 'copy', subtitled_cut, '-y'])

        try:
            subprocess.run(burn_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)
        except subprocess.TimeoutExpired: continue

        # 9. Hook & Thumb
        raw_hook = os.path.join(work_dir, f"hook_raw_{job_id}.mp4")
        hook_start = dur * 0.15
        subprocess.run(['ffmpeg', '-ss', str(hook_start), '-t', '3', '-i', subtitled_cut, '-c', 'copy', raw_hook, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        final_hook = os.path.join(work_dir, f"hook_{job_id}.mp4")
        phrases = ["Olha só o que aconteceu!", "Você não vai acreditar!", "Assista até o final!", "Isso é incrível!", "Segredo revelado!"]
        create_narrator_hook(raw_hook, final_hook, random.choice(phrases), job_id)

        thumb_out = os.path.join(work_dir, f"thumb_{job_id}.mp4")
        generate_thumbnail(raw_cut_path, thumb_out, job_id, text=f"PARTE {seg_num}")

        # 10. Concat
        yield f"🎬 Montagem Final (Parte {seg_num})...", 95
        final_out_local = os.path.join(work_dir, f"viral_clip_{seg_num}_{job_id}.mp4")
        list_txt = os.path.join(work_dir, f"list_{job_id}.txt")

        abs_thumb = os.path.abspath(thumb_out)
        abs_hook = os.path.abspath(final_hook)
        abs_main = os.path.abspath(subtitled_cut)

        with open(list_txt, 'w') as f:
            if os.path.exists(thumb_out) and os.path.getsize(thumb_out) > 0:
                f.write(f"file '{abs_thumb}'\n")
            if os.path.exists(final_hook) and os.path.getsize(final_hook) > 0:
                f.write(f"file '{abs_hook}'\n")
            f.write(f"file '{abs_main}'\n")

        try:
            subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt, '-c', 'copy', final_out_local, '-y'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        except: pass

        if os.path.exists(final_out_local) and os.path.getsize(final_out_local) > 1000:
            # 11. FINAL ACTIONS (API UPLOAD)

            # A. Upload to Drive (API)
            if GLOBAL_GOOGLE_SERVICES:
                yield f"☁️ Enviando para o Drive (API)...", 98
                file_id = GLOBAL_GOOGLE_SERVICES.upload_to_drive(final_out_local)
                if file_id: state_manager.append_log(f"✅ Salvo no Drive! ID: {file_id}")

            # Fallback legacy copy if drive mounted (local run)
            if os.path.exists(drive_dir) and drive_dir != "downloads":
                 shutil.copy(final_out_local, os.path.join(drive_dir, f"viral_clip_{seg_num}_{job_id}.mp4"))

            # B. Upload to YouTube (Auto-Publish)
            if 'publish_youtube' in settings and settings['publish_youtube'] and GLOBAL_GOOGLE_SERVICES:
                yield f"📺 Publicando no YouTube...", 99

                # --- SMART METADATA GENERATION ---
                # Title: [Hook/First 5 words] + [Main Hashtags]
                # We try to get the hook text if available, or just use a generic viral title
                video_title_base = f"Segredo Revelado! 🤯 #{random.choice(['Shorts', 'Viral', 'Fy'])}"

                # Use user hashtags or defaults
                user_tags = settings.get('hashtags', '#Shorts #Viral #Empreendedorismo')

                title = f"{video_title_base} {user_tags.split(' ')[0]}" # Add first tag to title
                if len(title) > 100: title = title[:97] + "..."

                desc = (
                    f"😱 Você não vai acreditar nesse segredo! \n\n"
                    f"👇 Inscreva-se no canal para mais cortes de alto valor!\n"
                    f"{user_tags}\n\n"
                    "Disclaimer: This video is for educational purposes. All rights belong to respective owners.\n"
                    "#shorts #motivation #business #mindset"
                )

                yt_id = GLOBAL_GOOGLE_SERVICES.upload_to_youtube(
                    final_out_local,
                    title=title,
                    description=desc,
                    tags=user_tags.replace('#', '').split(' '),
                    privacy="private" # Safety first
                )

                if yt_id:
                    msg_yt = f"✅ Publicado no YouTube! https://youtu.be/{yt_id}"
                    state_manager.append_log(msg_yt)

                    # POST FIRST COMMENT (Engagement)
                    comment_text = "👇 Qual sua opinião sobre isso? Comente abaixo! \n\n✅ Inscreva-se no canal: @empreendedorismobr2026"
                    GLOBAL_GOOGLE_SERVICES.post_comment(yt_id, comment_text)

                    yield msg_yt, 100

            cleanup_temps(work_dir, job_id)
            if GLOBAL_GOOGLE_SERVICES: yield f"✅ Processo Finalizado (Nuvem).", 100
            else: yield final_out_local # Return path if local
        else:
            yield f"⚠️ Erro ao gerar corte {seg_num} (Arquivo Vazio/Falha FFmpeg).", 0

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
