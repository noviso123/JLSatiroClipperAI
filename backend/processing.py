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

# --- Helpers ---

def seconds_to_ass_time(seconds):
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    centis = int((seconds * 100) % 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"

def generate_karaoke_ass(words, start_offset=0.0):
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
        w_start = word['start'] - start_offset
        w_end = word['end'] - start_offset
        if not chunk: chunk_start = w_start
        chunk.append(word)
        current_duration = w_end - chunk_start
        if len(chunk) >= 3 or current_duration > 1.5:
            c_text = " ".join([w['word'] for w in chunk]).upper()
            c_end = chunk[-1]['end'] - start_offset
            events += f"Dialogue: 0,{seconds_to_ass_time(chunk_start)},{seconds_to_ass_time(c_end)},Viral,,0,0,0,,{c_text}\n"
            chunk = []
    if chunk:
        c_text = " ".join([w['word'] for w in chunk]).upper()
        c_end = chunk[-1]['end'] - start_offset
        events += f"Dialogue: 0,{seconds_to_ass_time(chunk_start)},{seconds_to_ass_time(c_end)},Viral,,0,0,0,,{c_text}\n"
    return header + events

# --- Narrator Logic ---
async def generate_narrator_audio(text, output_file):
    """Generates audio using Edge-TTS (Free)"""
    voice = "pt-BR-AntonioNeural" # Male impactful voice
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_narrator_hook(hook_video, output_hook, phrase):
    """
    Mixes Narrator Audio with Video Audio (Ducking).
    """
    narrator_audio = "narrator.mp3"
    # Run async tts
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(generate_narrator_audio(phrase, narrator_audio))

    # FFmpeg Mixing:
    # 0:v (video), 0:a (original audio), 1:a (narrator)
    # Filter: [0:a]volume=0.3[a0];[1:a]volume=1.5[a1];[a0][a1]amix=inputs=2:duration=first[out]
    # Note: 'duration=first' ensures we don't extend video if narrator is too long (though we pick short phrases)

    cmd = [
        'ffmpeg', '-i', hook_video, '-i', narrator_audio,
        '-filter_complex', '[0:a]volume=0.1[original];[1:a]volume=2.0[narrator];[original][narrator]amix=inputs=2:duration=first[a_out]',
        '-map', '0:v', '-map', '[a_out]',
        '-c:v', 'copy', '-c:a', 'aac',
        output_hook, '-y'
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if os.path.exists(narrator_audio): os.remove(narrator_audio)

    # Check if mix succeeded, else return original
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

def process_video(url, settings):
    # FORCE PT-BR
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

    # 2. Extract Audio
    yield "🔊 Extraindo áudio...", 20
    subprocess.run(['ffmpeg', '-i', video_path, '-ac', '1', '-ar', '16000', '-vn', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 3. Transcribe
    yield "🎙️ Transcrevendo (Vosk)...", 40
    model_path = "model"
    if not os.path.exists(model_path): yield "❌ Modelo não encontrado!", 0; return
    model = Model(model_path); wf = wave.open(audio_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate()); rec.SetWords(True)
    all_words = []
    while True:
        data = wf.readframes(4000);
        if len(data) == 0: break
        if rec.AcceptWaveform(data):
            part = json.loads(rec.Result())
            if 'result' in part: all_words.extend(part['result'])
    final_res = json.loads(rec.FinalResult());
    if 'result' in final_res: all_words.extend(final_res['result'])
    wf.close()
    if not all_words: yield "⚠️ Silêncio detectado.", 100; return video_path

    # 4. Cuts & Subs
    yield "🧠 Inteligência Viral...", 60
    TARGET_MIN = 60.0; start_time = 0.0; cut_end = all_words[-1]['end']
    for word in all_words:
        if word['end'] > TARGET_MIN: cut_end = word['end']; break

    ass_path = f"{output_dir}/subs.ass"; clip_words = [w for w in all_words if w['start'] >= start_time and w['end'] <= cut_end]
    ass_content = generate_karaoke_ass(clip_words, start_offset=start_time)
    with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

    # 5. Render Main
    yield "🔥 Queimando Legendas...", 70
    main_clip_out = f"{output_dir}/main_clip.mp4"
    vf = f"ass={ass_path}"
    subprocess.run(['ffmpeg', '-ss', str(start_time), '-t', str(cut_end - start_time), '-i', video_path, '-vf', vf, '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', main_clip_out, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # 6. Hook & Narrator
    yield "🗣️ Adicionando Narrador IA...", 85
    raw_hook = f"{output_dir}/hook_raw.mp4"
    hook_start = (cut_end - start_time) * 0.2
    subprocess.run(['ffmpeg', '-ss', str(hook_start), '-t', '3', '-i', main_clip_out, '-c', 'copy', raw_hook, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Narrator Mix
    phrases = ["Olha só o que aconteceu!", "Você não vai acreditar!", "Assista até o final!", "Isso é incrível!", "Segredo revelado!"]
    phrase = random.choice(phrases)
    final_hook = f"{output_dir}/hook.mp4"
    create_narrator_hook(raw_hook, final_hook, phrase)

    thumb_out = f"{output_dir}/thumb.mp4"
    generate_thumbnail(video_path, thumb_out)

    # 7. Concat
    yield "🎬 Finalizando...", 95
    final_out = f"{output_dir}/viral_clip_final.mp4"
    list_txt = f"{output_dir}/list.txt"
    with open(list_txt, 'w') as f:
        if os.path.exists(thumb_out): f.write(f"file 'thumb.mp4'\n")
        if os.path.exists(final_hook): f.write(f"file 'hook.mp4'\n")
        f.write(f"file 'main_clip.mp4'\n")
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt, '-c', 'copy', final_out, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(final_out):
        yield "✅ Concluído!", 100
        return final_out
    else: yield "❌ Erro.", 0; return None
