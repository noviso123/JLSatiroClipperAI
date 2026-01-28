import os
import subprocess
import pyttsx3
from .cropper import get_crop_center
from .hooks import find_impact_hook

def generate_tts(text, output_path):
    """Gera áudio TTS usando pyttsx3 (100% Offline)."""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    # Tenta encontrar uma voz em Português
    pt_voice = None
    for voice in voices:
        if "brazil" in voice.name.lower() or "portuguese" in voice.lang.lower() or "pt-br" in voice.id.lower():
            pt_voice = voice.id
            break

    if pt_voice:
        engine.setProperty('voice', pt_voice)

    engine.setProperty('rate', 180) # Velocidade natural
    engine.save_to_file(text, output_path)
    engine.runAndWait()

    # Se o arquivo gerado for WAV (comum no Windows), converte para MP3 se necessário
    # mas o FFmpeg aceita WAV, então vamos manter o path original.
    # pyttsx3 no Windows geralmente salva como o que ele decidir (wav ou mp3).

def format_timestamp(seconds):
    td = float(seconds)
    hours = int(td // 3600)
    minutes = int((td % 3600) // 60)
    secs = int(td % 60)
    millis = int((td % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def create_srt(words, clip_start, clip_end, srt_path, offset=0):
    with open(srt_path, "w", encoding="utf-8") as f:
        counter = 1
        chunk_size = 3
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i+chunk_size]
            w_start = (chunk[0]['start'] - clip_start) + offset
            w_end = (chunk[-1]['end'] - clip_start) + offset
            if w_start < 0: w_start = 0

            text = " ".join([w['word'].strip() for w in chunk])
            f.write(f"{counter}\n")
            f.write(f"{format_timestamp(w_start)} --> {format_timestamp(w_end)}\n")
            f.write(f"{text.upper()}\n\n")
            counter += 1

def render_clips(video_path, segments, face_map, output_dir, original_words):
    results = []
    os.makedirs(output_dir, exist_ok=True)
    audio_path = video_path.replace(".mp4", ".wav")

    # Detect source dimensions
    try:
        probe = subprocess.run([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0',
            video_path
        ], capture_output=True, text=True, check=True)
        src_w, src_h = map(int, probe.stdout.strip().split('x'))
    except:
        src_w, src_h = 1920, 1080

    for i, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        duration = end - start

        # --- ENGAGEMENT UPGRADE: FIND HOOK ---
        print(f"🔥 Buscando Hook de Impacto para Clip {i+1}...")
        hook_start = find_impact_hook(audio_path, start, end)
        hook_duration = 3.0

        # --- ENGAGEMENT UPGRADE: AI NARRATOR (PT-BR) ---
        tts_file = os.path.join(output_dir, f"tts_{i+1}.mp3")
        narrative_text = "Assista até o final, isso vai te surpreender!"
        print(f"🎙️ Gerando Narração AI: '{narrative_text}'")
        generate_tts(narrative_text, tts_file)

        # --- ENGAGEMENT UPGRADE: THUMBNAIL WITH TEXT ---
        thumb_file = os.path.join(output_dir, f"thumb_{i+1}.jpg")
        viral_title = "ESTRATÉGIA VIRAL"
        try:
             # Usa drawtext para por o titulo na thumb perfeitamente centralizado com fundo preto
             subprocess.run([
                 'ffmpeg', '-y', '-ss', str(hook_start), '-i', video_path,
                 '-vf', f"drawtext=text='{viral_title}':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.8:boxborderw=20",
                 '-vframes', '1', '-q:v', '2', thumb_file
             ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

        # 1. Subtitles with 3s Offset
        clip_words = [w for w in original_words if w['start'] >= start and w['end'] <= end]
        srt_file = os.path.join(output_dir, f"sub_{i+1}.srt")
        create_srt(clip_words, start, end, srt_file, offset=hook_duration)

        # 2. Framing
        centers_norm = get_crop_center(start, end, face_map)

        output_file = os.path.join(output_dir, f"clip_{i+1}.mp4")
        print(f"🎬 Renderizando Clip {i+1} (Hook + TTS + Subtitles)...")

        escaped_srt = srt_file.replace("\\", "/").replace(":", "\\:")
        hook_text = "ASSISTA ATÉ O FINAL ⚠️"

        if len(centers_norm) == 2:
            # DUAL SPEAKER STACKED LAYOUT
            c1_norm, c2_norm = centers_norm
            crop_h = src_h
            # Each part will be 720x640 (9:8). Crop w = crop_h * (9/8)
            crop_w = int(src_h * (9/8))

            x1 = int(c1_norm * src_w - (crop_w / 2))
            x1 = max(0, min(x1, src_w - crop_w))

            x2 = int(c2_norm * src_w - (crop_w / 2))
            x2 = max(0, min(x2, src_w - crop_w))

            # CAPTION FIX: Place in the middle for split screen
            # MarginV=640 places it right at the center of 1280 height
            style = "ForceStyle=Alignment=2,Outline=2,Shadow=1,FontSize=28,MarginV=620,PrimaryColour=&H00FFFF"

            filter_str = (
                f"[0:v]trim=start={hook_start}:end={hook_start+hook_duration},setpts=PTS-STARTPTS[vhook_raw]; "
                f"[vhook_raw]crop={crop_w}:{crop_h}:{x1}:0,scale=720:1280[vhook]; "
                f"[0:a]atrim=start={hook_start}:end={hook_start+hook_duration},asetpts=PTS-STARTPTS,volume=0.1[ahook_bg]; "
                f"[1:a]asetpts=PTS-STARTPTS,volume=1.0[atts]; "
                f"[ahook_bg][atts]amix=inputs=2:duration=first[ahook_mixed]; "
                f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[vmain_raw]; "
                f"[vmain_raw]split=2[v_top_raw][v_bot_raw]; "
                f"[v_top_raw]crop={crop_w}:{crop_h}:{x1}:0,scale=720:640[v_top]; "
                f"[v_bot_raw]crop={crop_w}:{crop_h}:{x2}:0,scale=720:640[v_bot]; "
                f"[v_top][v_bot]vstack=inputs=2[vmain]; "
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,volume=1.0[amain]; "
                f"[vhook][ahook_mixed][vmain][amain]concat=n=2:v=1:a=1[vraw][araw]; "
                f"[vraw]drawtext=text='{hook_text}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h*0.2:enable='between(t,0,3)',"
                f"subtitles='{escaped_srt}':force_style='{style}'[vout]"
            )
        else:
            # SINGLE SPEAKER CROP
            center_norm = centers_norm[0]
            crop_h = src_h
            crop_w = int(src_h * (9/16))
            crop_x = int(center_norm * src_w - (crop_w / 2))
            crop_x = max(0, min(crop_x, src_w - crop_w))

            # CAPTION FIX: Shift UP to avoid mobile UI overlap (MarginV=200 -> 320)
            style = "ForceStyle=Alignment=2,Outline=2,Shadow=1,FontSize=28,MarginV=320,PrimaryColour=&H00FFFF"

            filter_str = (
                f"[0:v]trim=start={hook_start}:end={hook_start+hook_duration},setpts=PTS-STARTPTS[vhook_raw]; "
                f"[vhook_raw]crop={crop_w}:{crop_h}:{crop_x}:0,scale=720:1280[vhook]; "
                f"[0:a]atrim=start={hook_start}:end={hook_start+hook_duration},asetpts=PTS-STARTPTS,volume=0.1[ahook_bg]; "
                f"[1:a]asetpts=PTS-STARTPTS,volume=1.0[atts]; "
                f"[ahook_bg][atts]amix=inputs=2:duration=first[ahook_mixed]; "
                f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[vmain_raw]; "
                f"[vmain_raw]crop={crop_w}:{crop_h}:{crop_x}:0,scale=720:1280[vmain]; "
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,volume=1.0[amain]; "
                f"[vhook][ahook_mixed][vmain][amain]concat=n=2:v=1:a=1[vraw][araw]; "
                f"[vraw]drawtext=text='{hook_text}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h*0.2:enable='between(t,0,3)',"
                f"subtitles='{escaped_srt}':force_style='{style}'[vout]"
            )

        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', tts_file,
            '-filter_complex', filter_str,
            '-map', '[vout]', '-map', '[araw]',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '26',
            '-c:a', 'aac',
            output_file
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            results.append(output_file)
        except Exception as e:
            print(f"❌ Erro Render Clip {i+1}: {e}")

    return results
