import os
import json
import wave
import subprocess
import datetime
import random
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

def create_narrator_hook(hook_video, output_hook, phrase):
    narrator_audio = "narrator.mp3"
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

def generate_thumbnail(video_path, output_path, text="VIRAL CLIP"):
    try:
        frame_jpg = output_path.replace(".mp4", ".jpg")
        subprocess.run(['ffmpeg', '-ss', '00:00:30', '-i', video_path, '-frames:v', '1', '-q:v', '2', frame_jpg, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        img.save(frame_jpg)
        subprocess.run(['ffmpeg', '-loop', '1', '-i', frame_jpg, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-c:v', 'libx264', '-t', '0.1', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', output_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except: return None

def get_transcription(audio_path, model_path):
    """Reusable transcription function with Caching"""
    model = get_cached_model(model_path) # USE CACHE
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

def cleanup_temps(folder):
    """Deletes large intermediate files"""
    temps = ["input_video.mp4", "input_audio.wav", "raw_cut.mp4", "raw_cut.wav", "hook_raw.mp4", "hook.mp4", "main_clip.mp4", "thumb.mp4", "thumb.jpg", "list.txt", "narrator.mp3"]
    for f in temps:
        p = os.path.join(folder, f)
        if os.path.exists(p): os.remove(p)

def process_video(url, settings):
    settings['lang'] = 'Português (BR)'
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    video_path = f"{output_dir}/input_video.mp4"
    audio_path = f"{output_dir}/input_audio.wav"

    # 1. Download
    yield "⬇️ Baixando vídeo...", 10
    ydl_opts = {'format': 'best[ext=mp4]', 'outtmpl': video_path, 'quiet': True, 'no_warnings': True}
    if os.path.exists(video_path): os.remove(video_path)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    except Exception as e: yield f"❌ Erro Download: {e}", 0; return

    # 2. Extract Full Audio (for Discovery)
    yield "🔊 Lendo Áudio Original...", 20
    subprocess.run(['ffmpeg', '-threads', '4', '-i', video_path, '-ac', '1', '-ar', '16000', '-vn', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 3. Discovery Transcription (Find Cut Points)
    yield "🧠 Analisando Corte (Scan Rápido)...", 40
    model_path = "model"
    if not os.path.exists(model_path): yield "❌ Modelo não encontrado!", 0; return

    full_words = get_transcription(audio_path, model_path)
    if not full_words: yield "⚠️ Silêncio detectado.", 100; return video_path

    # Smart Cut Logic
    TARGET_MIN = 60.0
    start_time = 0.0
    cut_end = full_words[-1]['end']
    for word in full_words:
        if word['end'] > TARGET_MIN: cut_end = word['end']; break

    # 4. RENDER RAW CUT (Video + Audio)
    yield "✂️ Cortando Clipe Bruto...", 50
    raw_cut_path = f"{output_dir}/raw_cut.mp4"
    raw_cut_audio = f"{output_dir}/raw_cut.wav"

    subprocess.run([
        'ffmpeg', '-threads', '4', '-ss', str(start_time), '-t', str(cut_end - start_time),
        '-i', video_path,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac',
        raw_cut_path, '-y'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    subprocess.run(['ffmpeg', '-i', raw_cut_path, '-ac', '1', '-ar', '16000', '-vn', raw_cut_audio, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. PRODUCTION TRANSCRIPTION (Double Pass)
    yield "🎙️ Sincronizando Legendas (Passo 2)...", 60
    clip_words = get_transcription(raw_cut_audio, model_path) # Uses cached model

    ass_path = f"{output_dir}/subs.ass"
    ass_content = generate_karaoke_ass(clip_words)
    with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

    # 6. Burn Subtitles
    yield "🔥 Queimando Legendas...", 70
    subtitled_cut = f"{output_dir}/main_clip.mp4"
    vf = f"ass={ass_path}"
    subprocess.run(['ffmpeg', '-threads', '4', '-i', raw_cut_path, '-vf', vf, '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'copy', subtitled_cut, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # 7. Hook & Narrator
    yield "🗣️ Criando Hook com Narrador...", 85
    raw_hook = f"{output_dir}/hook_raw.mp4"
    hook_start = (cut_end - start_time) * 0.2
    subprocess.run(['ffmpeg', '-ss', str(hook_start), '-t', '3', '-i', subtitled_cut, '-c', 'copy', raw_hook, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    final_hook = f"{output_dir}/hook.mp4"
    phrases = ["Olha só o que aconteceu!", "Você não vai acreditar!", "Assista até o final!", "Isso é incrível!", "Segredo revelado!"]
    create_narrator_hook(raw_hook, final_hook, random.choice(phrases))

    thumb_out = f"{output_dir}/thumb.mp4"
    generate_thumbnail(video_path, thumb_out)

    # 8. Final Concat
    yield "🎬 Montagem Final...", 95
    final_out = f"{output_dir}/viral_clip_final.mp4"
    list_txt = f"{output_dir}/list.txt"
    with open(list_txt, 'w') as f:
        if os.path.exists(thumb_out): f.write(f"file 'thumb.mp4'\n")
        if os.path.exists(final_hook): f.write(f"file 'hook.mp4'\n")
        f.write(f"file 'main_clip.mp4'\n")
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt, '-c', 'copy', final_out, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(final_out):
        yield "🧹 Limpando Arquivos Temporários...", 98
        cleanup_temps(output_dir)
        yield "✅ Concluído!", 100
        return final_out
    else: yield "❌ Erro.", 0; return None
