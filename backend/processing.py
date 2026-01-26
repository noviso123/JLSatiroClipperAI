import os
import json
import wave
import subprocess
import datetime
import random
import yt_dlp
from vosk import Model, KaldiRecognizer
from PIL import Image, ImageDraw, ImageFont

# --- Helpers ---

def seconds_to_ass_time(seconds):
    """Converts seconds to ASS timestamp format (H:MM:SS.cs)"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    centis = int((seconds * 100) % 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"

def generate_karaoke_ass(words, start_offset=0.0):
    """
    Generates ASS subtitle file content for 'Karaoke/Viral' look.
    Focus: Large Yellow Text, Outline, 1-3 words per line for speed.
    """
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
    # Group words into chunks of max 3 words or max 1.5 seconds to create pace
    chunk = []
    chunk_start = 0

    for i, word in enumerate(words):
        w_start = word['start'] - start_offset
        w_end = word['end'] - start_offset
        text = word['word']

        if not chunk:
            chunk_start = w_start

        chunk.append(word)
        current_duration = w_end - chunk_start

        # Break chunk if: 3 words reached OR duration > 1.5s OR valid pause detected
        if len(chunk) >= 3 or current_duration > 1.5:
            # Commit chunk
            c_text = " ".join([w['word'] for w in chunk]).upper()
            c_end = chunk[-1]['end'] - start_offset

            # Karaoke Effect: Just display the block for now (simpler and cleaner than per-char karaoke)
            # The 'Viral' style defined above handles the look.
            events += f"Dialogue: 0,{seconds_to_ass_time(chunk_start)},{seconds_to_ass_time(c_end)},Viral,,0,0,0,,{c_text}\n"
            chunk = []

    # Final chunk
    if chunk:
        c_text = " ".join([w['word'] for w in chunk]).upper()
        c_end = chunk[-1]['end'] - start_offset
        events += f"Dialogue: 0,{seconds_to_ass_time(chunk_start)},{seconds_to_ass_time(c_end)},Viral,,0,0,0,,{c_text}\n"

    return header + events

def generate_thumbnail(video_path, output_path, text="VIRAL CLIP"):
    """
    Extracts a frame from the middle and draws clickbait text.
    """
    try:
        # Extract frame
        frame_jpg = output_path.replace(".mp4", ".jpg")
        subprocess.run([
            'ffmpeg', '-ss', '00:00:30', '-i', video_path,
            '-frames:v', '1', '-q:v', '2', frame_jpg, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(frame_jpg):
            return None # Fail silently

        # Draw Text with Pillow
        img = Image.open(frame_jpg)
        draw = ImageDraw.Draw(img)

        # Simple Logic: Big Red Text Centered
        W, H = img.size
        # Try to load a font, fallback to default or linux path
        font = None
        font_paths = [
            "arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]

        for path in font_paths:
            try:
                font = ImageFont.truetype(path, 100)
                break
            except:
                continue

        if not font:
             font = ImageFont.load_default()

        # Draw Background Rectangle for text
        w_text, h_text = 600, 150 # Approx
        x, y = (W - w_text)/2, (H - h_text)/2

        # Clickbait Colors
        draw.text((x, y), text, fill="yellow", stroke_width=3, stroke_fill="black", font=font)

        img.save(frame_jpg)

        # Convert Image to 0.1s Video WITH SILENT AUDIO (Critical for concat)
        # We generate a blank audio track for 0.1s
        subprocess.run([
            'ffmpeg', '-loop', '1', '-i', frame_jpg,
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-c:v', 'libx264', '-t', '0.1', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-shortest',
            output_path, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return output_path
    except Exception as e:
        print(f"Thumb error: {e}")
        return None

def process_video(url, settings):
    """
    Full Pipeline: Thumb 0.1s -> Hook 3s -> Main Clip >60s
    """
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    video_path = f"{output_dir}/input_video.mp4"
    audio_path = f"{output_dir}/input_audio.wav"

    # 1. Download
    yield "⬇️ Baixando vídeo (High Speed)...", 10
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': video_path,
        'quiet': True, 'no_warnings': True
    }
    # Cleanup
    if os.path.exists(video_path): os.remove(video_path)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        yield f"❌ Erro Download: {e}", 0; return

    # 2. Extract Audio
    yield "🔊 Extraindo áudio...", 20
    subprocess.run(['ffmpeg', '-i', video_path, '-ac', '1', '-ar', '16000', '-vn', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 3. Transcribe
    yield "🎙️ Transcrevendo (Vosk Offline)...", 40
    model_path = "model"
    if not os.path.exists(model_path): yield "❌ Modelo não encontrado!", 0; return

    model = Model(model_path)
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

    if not all_words: yield "⚠️ Silêncio detectado.", 100; return video_path

    # 4. Smart Cut Logic (Min 60s)
    yield "🧠 Calculando Cortes...", 60
    TARGET_MIN = 60.0
    start_time = 0.0
    end_time = all_words[-1]['end']

    # Find word ending after 60s
    cut_end = end_time
    for word in all_words:
        if word['end'] > TARGET_MIN:
            cut_end = word['end']
            break

    # Refine cut (start 0 for now)

    # Generate ASS Subtitles
    ass_path = f"{output_dir}/subs.ass"
    clip_words = [w for w in all_words if w['start'] >= start_time and w['end'] <= cut_end]
    ass_content = generate_karaoke_ass(clip_words, start_offset=start_time)
    with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

    # 5. Render Main Clip (Burn ASS)
    yield "🔥 Renderizando Clip Principal (+ Legendas)...", 70
    main_clip_out = f"{output_dir}/main_clip.mp4"

    # Apply ASS. Note: escaped path for filter
    # simple relative path works best in colab
    vf = f"ass={ass_path}"

    subprocess.run([
        'ffmpeg', '-ss', str(start_time), '-t', str(cut_end - start_time),
        '-i', video_path, '-vf', vf,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac',
        main_clip_out, '-y'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # 6. Hook (3s from 20%) & Thumbnail
    yield "🪝 Gerando Hook e Thumbnail...", 85

    hook_out = f"{output_dir}/hook.mp4"
    hook_start = (cut_end - start_time) * 0.2
    subprocess.run([
        'ffmpeg', '-ss', str(hook_start), '-t', '3',
        '-i', main_clip_out, '-c', 'copy', hook_out, '-y'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    thumb_out = f"{output_dir}/thumb.mp4"
    generate_thumbnail(video_path, thumb_out) # Generates 0.1s video

    # 7. Final Concatenation
    yield "🎬 Montagem Final...", 95
    final_out = f"{output_dir}/viral_clip_final.mp4"
    list_txt = f"{output_dir}/list.txt"

    with open(list_txt, 'w') as f:
        # Check if thumb exists
        if os.path.exists(thumb_out): f.write(f"file 'thumb.mp4'\n")
        # Check if hook exists
        if os.path.exists(hook_out): f.write(f"file 'hook.mp4'\n")
        # Main
        f.write(f"file 'main_clip.mp4'\n")

    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt,
        '-c', 'copy', final_out, '-y'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(final_out):
        yield "✅ Concluído!", 100
        return final_out
    else:
        yield "❌ Erro na montagem.", 0
        return None
