import os
import json
import wave
import subprocess
import datetime
import random
import time
import shutil
import yt_dlp
import asyncio
import edge_tts
from vosk import Model, KaldiRecognizer
from PIL import Image, ImageDraw, ImageFont

# --- Global Cache ---
_CACHED_MODEL = None

def get_cached_model(model_path):
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        print(f"🔄 Carregando Modelo para RAM (Apenas uma vez)...")
        _CACHED_MODEL = Model(model_path)
    return _CACHED_MODEL

# --- Helpers ---
def seconds_to_ass_time(seconds):
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    centis = int((seconds * 100) % 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"

def generate_karaoke_ass(words):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial,80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,1,3,0,2,10,10,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = ""
    chunk = []
    chunk_start = 0
    for i, word in enumerate(words):
        w_start = word['start']
        w_end = word['end']
        if not chunk: chunk_start = w_start
        chunk.append(word)
        current_duration = w_end - chunk_start
        if len(chunk) >= 3 or current_duration > 1.5:
            c_text = " ".join([w['word'] for w in chunk]).upper()
            c_end = chunk[-1]['end']
            events += f"Dialogue: 0,{seconds_to_ass_time(chunk_start)},{seconds_to_ass_time(c_end)},Viral,,0,0,0,,{c_text}\n"
            chunk = []
    if chunk:
        c_text = " ".join([w['word'] for w in chunk]).upper()
        c_end = chunk[-1]['end']
        events += f"Dialogue: 0,{seconds_to_ass_time(chunk_start)},{seconds_to_ass_time(c_end)},Viral,,0,0,0,,{c_text}\n"
    return header + events

# --- Narrator ---
async def generate_narrator_audio(text, output_file):
    voice = "pt-BR-AntonioNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_narrator_hook(hook_video, output_hook, phrase, job_id):
    narrator_audio = f"narrator_{job_id}.mp3"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(generate_narrator_audio(phrase, narrator_audio))

    cmd = [
        'ffmpeg', '-i', hook_video, '-i', narrator_audio,
        '-filter_complex', '[0:a]volume=0.1[original];[1:a]volume=2.0[narrator];[original][narrator]amix=inputs=2:duration=first[a_out]',
        '-map', '0:v', '-map', '[a_out]',
        '-c:v', 'copy', '-c:a', 'aac',
        output_hook, '-y'
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if os.path.exists(narrator_audio): os.remove(narrator_audio)
    if os.path.exists(output_hook): return output_hook
    return hook_video

def generate_thumbnail(video_path, output_path, unique_id, text="VIRAL CLIP"):
    try:
        frame_jpg = output_path.replace(".mp4", ".jpg")
        # Try to extract frame from middle of source to be unique
        # Get duration first? Assume we have access or just pick random offset?
        # Actually video_path here is the original full video. We need the RAW CUT path preferably to be relevant.
        # But hook function receives raw video path? Wait.
        # In main loop, we pass valid path.

        # Taking frame at 30% of the clip duration.
        subprocess.run(['ffmpeg', '-ss', '2', '-i', video_path, '-frames:v', '1', '-q:v', '2', frame_jpg, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(frame_jpg): return None
        img = Image.open(frame_jpg)
        draw = ImageDraw.Draw(img)
        font = None
        font_paths = ["arial.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        for path in font_paths:
            try: font = ImageFont.truetype(path, 100); break
            except: continue
        if not font: font = ImageFont.load_default()
        W, H = img.size; w_text, h_text = 600, 150; x, y = (W - w_text)/2, (H - h_text)/2
        draw.text((x, y), text, fill="yellow", stroke_width=3, stroke_fill="black", font=font)

        # Add Unique ID visual ? No just text.

        img.save(frame_jpg)
        subprocess.run(['ffmpeg', '-loop', '1', '-i', frame_jpg, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-c:v', 'libx264', '-t', '0.1', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', output_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except: return None

def get_transcription(audio_path, model_path):
    model = get_cached_model(model_path)
    wf = wave.open(audio_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    all_words = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0: break
        if rec.AcceptWaveform(data):
            part = json.loads(rec.Result())
            if 'result' in part: all_words.extend(part['result'])
    final_res = json.loads(rec.FinalResult())
    if 'result' in final_res: all_words.extend(final_res['result'])
    wf.close()
    return all_words

def cleanup_temps(folder, job_id):
    """Deletes large intermediate files for a specific job"""
    temps = [f"raw_cut_{job_id}.mp4", f"raw_cut_{job_id}.wav", f"hook_raw_{job_id}.mp4", f"hook_{job_id}.mp4", f"main_clip_{job_id}.mp4", f"thumb_{job_id}.mp4", f"list_{job_id}.txt"]
    for f in temps:
        p = os.path.join(folder, f)
        if os.path.exists(p): os.remove(p)

def process_video(url, settings):
    settings['lang'] = 'Português (BR)'

    # WORKSPACE STRATEGY:
    # 1. Work in Local SSD (Fast/Stable)
    # 2. Sync to Drive (Symlinked 'downloads' folder) for persistence

    work_dir = "/content/temp_work" # Local SSD
    drive_dir = "downloads" # Points to Drive via Symlink

    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(drive_dir, exist_ok=True) # Ensure symlink or folder exists

    # Files (Local)
    video_path = f"{work_dir}/input_video.mp4"
    audio_path = f"{work_dir}/input_audio.wav"

    # 1. Download
    yield "⬇️ Baixando vídeo (SSD Local)...", 5
    # Relaxed format: prefer mp4 but take best if needed to avoid empty file
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': video_path,
        'quiet': True,
        'no_warnings': True,
        'overwrites': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    except Exception as e: yield f"❌ Erro Download: {e}", 0; return

    # Sync Input to Drive
    try: shutil.copy(video_path, f"{drive_dir}/input_video.mp4")
    except: pass

    # 2. Extract Full Audio (for Discovery)
    yield "🔊 Lendo Áudio Original...", 10
    subprocess.run(['ffmpeg', '-threads', '4', '-i', video_path, '-ac', '1', '-ar', '16000', '-vn', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 3. Discovery Transcription
    yield "🧠 Mapeando Conteúdo...", 20
    model_path = "model"
    if not os.path.exists(model_path): yield "❌ Modelo não encontrado!", 0; return

    full_words = get_transcription(audio_path, model_path)
    if not full_words: yield "⚠️ Silêncio detectado.", 100; return

    # --- SEGMENTATION LOGIC ---
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

        if (seg_end_time - start_time) >= 10.0:
            segments.append({'start': start_time, 'end': seg_end_time})

        current_start_word = best_end_idx + 1
        if current_start_word >= len(full_words): break

    total_segs = len(segments)
    yield f"📐 Estratégia Definida: {total_segs} Cortes Identificados.", 30

    # --- PROCESSING LOOP ---
    for idx, seg in enumerate(segments):
        job_id = f"{int(time.time())}_{idx+1}"
        seg_num = idx + 1

        yield f"✂️ Processando Corte {seg_num}/{total_segs}...", 40 + int(20 * (idx/total_segs))

        start_t = seg['start']
        dur = seg['end'] - start_t

        # 4. Render Raw Cut
        raw_cut_path = f"{work_dir}/raw_cut_{job_id}.mp4"
        raw_cut_audio = f"{work_dir}/raw_cut_{job_id}.wav"

        # FIX SYNC/SLOWMO: Force 30fps (CFR) and use 'veryfast' instead of 'ultrafast'
        # -r 30: Forces standardized framerate
        # -vsync cfr: Enforces constant frame rate (prevents drift)
        # -max_muxing_queue_size 1024: Prevents buffer underflows
        try:
            subprocess.run([
                'ffmpeg', '-threads', '4',
                '-ss', str(start_t), '-t', str(dur),
                '-i', video_path,
                '-r', '30', '-vsync', 'cfr',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-c:a', 'aac', '-ar', '44100',
                '-max_muxing_queue_size', '4096',
                raw_cut_path, '-y'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)

            subprocess.run(['ffmpeg', '-i', raw_cut_path, '-ac', '1', '-ar', '16000', '-vn', raw_cut_audio, '-y'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        except subprocess.TimeoutExpired:
            yield f"⚠️ Corte {seg_num} demorou demais e foi pulado.", 0
            continue

        # Backup Raw to Drive
        try: shutil.copy(raw_cut_path, f"{drive_dir}/raw_cut_{job_id}.mp4")
        except: pass

        # 5. Production Transcription
        try:
            clip_words = get_transcription(raw_cut_audio, model_path)
        except:
             yield f"⚠️ Erro Transcrição {seg_num}. Pulando.", 0; continue

        ass_path = f"{work_dir}/subs_{job_id}.ass"
        ass_content = generate_karaoke_ass(clip_words)
        with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

        # 6. Burn
        subtitled_cut = f"{work_dir}/main_clip_{job_id}.mp4"
        vf = f"ass={ass_path}"
        try:
            # Re-enforce r 30 here to be safe during burn
            subprocess.run(['ffmpeg', '-threads', '4',
                           '-i', raw_cut_path,
                           '-vf', vf,
                           '-r', '30', '-vsync', 'cfr',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                           '-c:a', 'copy',
                           subtitled_cut, '-y'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)
        except subprocess.TimeoutExpired: continue

        # 7. Hook & Thumb
        raw_hook = f"{work_dir}/hook_raw_{job_id}.mp4"
        hook_start = dur * 0.15
        subprocess.run(['ffmpeg', '-ss', str(hook_start), '-t', '3', '-i', subtitled_cut, '-c', 'copy', raw_hook, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        final_hook = f"{work_dir}/hook_{job_id}.mp4"
        phrases = ["Olha só o que aconteceu!", "Você não vai acreditar!", "Assista até o final!", "Isso é incrível!", "Segredo revelado!"]
        create_narrator_hook(raw_hook, final_hook, random.choice(phrases), job_id)

        thumb_out = f"{work_dir}/thumb_{job_id}.mp4"
        generate_thumbnail(raw_cut_path, thumb_out, job_id, text=f"PARTE {seg_num}")

        # 8. Concat
        yield f"🎬 Montagem Final (Parte {seg_num})...", 95
        final_out_local = f"{work_dir}/viral_clip_{seg_num}_{job_id}.mp4"
        list_txt = f"{work_dir}/list_{job_id}.txt"

        # ABSOLUTE PATHS for local concat
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
            # 9. FINAL COPY TO DRIVE (The most important step)
            final_out_drive = f"{drive_dir}/viral_clip_{seg_num}_{job_id}.mp4"
            shutil.copy(final_out_local, final_out_drive)

            # Clean Local Temps
            cleanup_temps(work_dir, job_id)

            # Yield the DRIVE Path (so the user can download it from Streamlit which looks at 'downloads' symlink)
            # Actually, Streamlit 'st.download_button' needs a path it can read.
            # 'drive_dir' is 'downloads', which is symlinked to user drive.
            # So yielding 'downloads/file.mp4' works great.
            yield final_out_drive
        else:
            yield f"⚠️ Erro ao gerar corte {seg_num} (Arquivo Vazio/Falha FFmpeg).", 0

    yield "✅ Processamento de Lote Completado!", 100
