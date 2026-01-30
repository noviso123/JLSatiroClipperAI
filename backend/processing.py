import os
import shutil
import time
import subprocess
import concurrent.futures
import random
import json
import hashlib
from . import state_manager
from . import audio_engine
from . import video_engine
from . import subtitle_engine

def run_ffmpeg(cmd, name="FFmpeg"):
    """Titan Utility: Runs FFmpeg and captures errors for diagnosis."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Erro no {name}:")
        print(res.stderr[-1000:]) # Show last 1000 chars of error
        return False
    return True

def process_single_segment(seg_data, video_path, work_dir, drive_dir):
    try:
        if len(seg_data) == 8: idx, seg, total_segs, face_map, settings, batch_id, full_words, global_host = seg_data
        else: return None

        seg_num = idx + 1
        job_id = f"{batch_id}_{seg_num}"
        start_t = seg['start']
        dur = seg['end'] - start_t

        print(f"🔨 [TITAN-V24.6] Iniciando Render {seg_num}/{total_segs} (Dur: {dur:.1f}s)")

        raw_cut_path = os.path.join(work_dir, f"r_{job_id}.mp4").replace("\\", "/")
        v_encoder, v_preset = video_engine.get_best_encoder()

        # --- DUAL SEEK (ULTRA PRECISION) ---
        fast_ss = max(0, start_t - 30)
        accurate_ss = start_t - fast_ss

        zones = video_engine.get_layout_zones(start_t, dur, face_map)
        local_speaker = video_engine.get_crop_from_cache(start_t, dur, face_map)
        v_w, v_h = video_engine.get_video_dimensions(video_path)

        # New Scale Factors for V24.13 (Targeting 600px/640px height)
        s_w_600 = int(v_w * (600 / v_h))
        crop_w = 720

        def cx_calc_600(val): return max(0, min(s_w_600 - 720, int(val * s_w_600) - 360))

        # Guest determination (Reaction / Split content)
        centers = []
        for v in face_map.values():
            if isinstance(v, dict) and "faces" in v and v["faces"]:
                centers.append(v["faces"][0]["center"])
        guest_v = 0.5

        g_host = 0.5
        g_host_y = 0.35 # Default to upper third if unknown

        if face_map:
            centers_x = []
            centers_y = []
            for v in face_map.values():
                if isinstance(v, dict) and "faces" in v and v["faces"]:
                    # Look at primary face
                    f = v["faces"][0]
                    centers_x.append(f.get("center", 0.5))
                    centers_y.append(f.get("center_y", 0.35))

            if centers_x:
                # Simple average for stability across the clip
                g_host = sum(centers_x) / len(centers_x)
                g_host_y = sum(centers_y) / len(centers_y)

                # Recalculate guest for V30 (Extreme Isolation)
                # Scale 900 + Target 0.75 ensures we crop purely the right side (Screen),
                # cutting off the host's shoulder completely.
                if g_host < 0.5: guest_v = 0.75
                else: guest_v = 0.25

        is_gamer = (settings.get('layout') == 'Modo Gamer')
        is_reaction = (settings.get('layout') == 'Reação (Rosto/Base)')

        # Calculate Aspect Ratio
        # video_info should have width/height ideally, or we assume 16:9 if missing
        # We don't have video_info explicitly passed here unless we query it?
        # IMPORTANT: processing.py usually knows input dimensions via ffmpeg probe earlier
        # For now, we deduce AR from crop_w? No, crop_w is output width?
        # Assuming we access 'video_w' and 'video_h' if available, else 1.777
        vid_w = v_w # Default fallback
        vid_h = v_h
        input_ar = vid_w / vid_h if vid_h != 0 else 1.777

        # Try to find dimensions in global scope or args?
        # Actually 'cx_calc_600' used 'video_w' in older versions?
        # Let's rely on standard 16:9 DEFAULT if we can't probe,
        # but since 'processing.process_video' usually does probe...
        # We will assume 1.777 for now as refactor barrier, but ready for parameter injection.

        vf_logic = video_engine.build_dynamic_filter_complex(
            zones,
            cx_calc_600(local_speaker),
            g_host,
            g_host_y,
            guest_v,
            crop_w,
            input_ar=input_ar,
            is_gamer=is_gamer,
            is_reaction=is_reaction
        )

        cmd_base = [
            'ffmpeg', '-y',
            '-ss', str(fast_ss), '-i', video_path.replace("\\", "/"),
            '-ss', str(accurate_ss), '-t', str(dur),
            '-filter_complex', vf_logic + ",setsar=1/1",
            '-c:v', v_encoder,
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-af', 'aresample=async=1', '-avoid_negative_ts', 'make_zero'
        ]

        if v_encoder == 'libx264': cmd_base.extend(['-preset', 'ultrafast'])
        else: cmd_base.extend(['-quality', v_preset, '-rc', 'vbr_latency'])

        cmd_base.append(raw_cut_path)

        if not run_ffmpeg(cmd_base, f"Base-Render {job_id}"):
            if v_encoder != 'libx264':
                print(f"⚠️ Falha no hardware encoder, tentando CPU...")
                cmd_base[cmd_base.index(v_encoder)] = 'libx264'
                # Clean hardware specific flags
                cmd_base = [c for c in cmd_base if c not in ['-quality', v_preset, '-rc', 'vbr_latency']]
                cmd_base.insert(cmd_base.index('libx264')+1, '-preset')
                cmd_base.insert(cmd_base.index('-preset')+1, 'ultrafast')
                if not run_ffmpeg(cmd_base, f"CPU-Fallback {job_id}"): return None
            else: return None

        # --- SUBTITLES ---
        subtitled_cut = os.path.join(work_dir, f"s_{job_id}.mp4").replace("\\", "/")
        clip_w = [w for w in full_words if w['start'] >= (start_t - 0.5) and w['end'] <= (start_t + dur + 0.5)]
        for cw in clip_w:
            cw['start'] = max(0, cw['start'] - start_t)
            cw['end'] = cw['end'] - start_t

        ass_path = os.path.join(work_dir, f"sub_{job_id}.ass")
        with open(ass_path, "w", encoding="utf-8") as f: f.write(subtitle_engine.generate_karaoke_ass(clip_w))

        # Windows-Safe ASS Filter Path
        escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")

        cmd_sub = [
            'ffmpeg', '-y', '-i', raw_cut_path,
            '-vf', f"ass='{escaped_ass}',setsar=1/1",
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-af', 'aresample=async=1',
            subtitled_cut
        ]
        if not run_ffmpeg(cmd_sub, f"Subtitle-Render {job_id}"): return None

        # --- POST PROD ---
        thumb_p = os.path.join(work_dir, f"t_{job_id}.mp4").replace("\\", "/")
        video_engine.generate_thumbnail(raw_cut_path, thumb_p, job_id, text=f"PARTE {seg_num}")

        final_hook = os.path.join(work_dir, f"h_{job_id}.mp4").replace("\\", "/")
        narr_p = os.path.join(work_dir, f"n_{job_id}.mp3")
        txt_h = random.choice(["O SEGREDO!", "ISSO É INSANO!", "OLHA ISSO!", "VOCÊ SABIA?"])
        audio_engine.generate_hook_narrator(txt_h, narr_p)

        raw_h = os.path.join(work_dir, f"hr_{job_id}.mp4").replace("\\", "/")
        h_start = min(dur * 0.15, max(0, dur - 3.1))
        cmd_hr = [
            'ffmpeg', '-y', '-ss', str(h_start), '-t', '3', '-i', subtitled_cut,
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-af', 'aresample=async=1', '-avoid_negative_ts', 'make_zero',
            raw_h
        ]
        if not run_ffmpeg(cmd_hr, f"Hook-Extraction {job_id}"): return None

        video_engine.create_narrator_hook(raw_h, final_hook, txt_h, job_id, narr_p)

        # --- FINAL FUSION (V24.7 FIX) ---
        prod_out = os.path.join(work_dir, f"out_{job_id}.mp4").replace("\\", "/")
        final_drive = os.path.join(drive_dir, f"clip_{batch_id}_{seg_num}.mp4").replace("\\", "/")

        inputs = []
        if os.path.exists(thumb_p): inputs.extend(['-i', thumb_p])
        if os.path.exists(final_hook): inputs.extend(['-i', final_hook])
        if os.path.exists(subtitled_cut): inputs.extend(['-i', subtitled_cut])
        else: return None

        n_ins = len(inputs) // 2

        # Sincronia Titanium: aresample=async=1 integrado na fusão
        f_concat = "".join([f"[{i}:v][{i}:a]" for i in range(n_ins)])
        f_concat += f"concat=n={n_ins}:v=1:a=1[v_raw][a_raw];"
        f_concat += "[v_raw]setsar=1/1[vf];"
        f_concat += "[a_raw]aresample=async=1[af]"

        cmd_final = [
            'ffmpeg', '-y'] + inputs + [
            '-filter_complex', f_concat,
            '-map', '[vf]', '-map', '[af]',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-avoid_negative_ts', 'make_zero',
            prod_out
        ]
        if run_ffmpeg(cmd_final, f"Final-Fusion {job_id}"):
            shutil.copy(prod_out, final_drive)
            print(f"✅ [SUCCESS] {job_id} -> {final_drive}")
            return {"path": final_drive, "seg_num": seg_num}

        return None
    except Exception as e:
        print(f"❌ Titan Crash: {e}")
        return None

def process_video(url, video_file, hashtags="", layout_mode="Dinâmico (Auto-IA)", publish_youtube=False):
    import hashlib
    batch_id = hashlib.md5((url or "file").encode()).hexdigest()[:8]
    work_dir, drive_dir = video_engine.setup_directories()
    v_p = os.path.join(work_dir, "input.mp4").replace("\\", "/")
    a_p = os.path.join(work_dir, "input.wav").replace("\\", "/")

    if not os.path.exists(v_p):
        yield "⬇️ Baixando Vídeo...", 10
        if video_file: shutil.copy(video_file.name if hasattr(video_file, 'name') else video_file, v_p)
        else: video_engine.download_strategy_yt_dlp(url, v_p)

    if not os.path.exists(a_p):
        yield "🔊 Extraindo Áudio...", 20
        subprocess.run(['ffmpeg', '-y', '-i', v_p, '-vn', '-ac', '1', '-ar', '16000', a_p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    yield "🧠 Inteligência Whisper...", 30
    words = audio_engine.get_transcription(a_p)
    yield "👁️ Scan Facial...", 40
    f_map = video_engine.scan_face_positions(v_p)

    g_host = 0.5
    if f_map:
        centers = []
        for v in f_map.values():
            if isinstance(v, dict) and "faces" in v and v["faces"]:
                centers.append(v["faces"][0]["center"])
        if centers:
            cts = {}
            for c in centers: cts[round(c, 1)] = cts.get(round(c, 1), 0) + 1
            g_host = max(cts, key=cts.get)

    segments = []
    c = 0
    while c < len(words):
        st = words[c]['start']
        et = st + 60
        e_idx = c
        while e_idx < len(words) and words[e_idx]['end'] < et: e_idx += 1
        segments.append({'start': st, 'end': words[min(e_idx, len(words)-1)]['end']})
        c = e_idx + 1

    yield f"🚀 Processando {len(segments)} Cortes...", 50
    total = len(segments)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        payloads = [(i, s, total, f_map, {'layout': layout_mode}, batch_id, words, g_host) for i, s in enumerate(segments)]
        futures = [executor.submit(process_single_segment, p, v_p, work_dir, drive_dir) for p in payloads]
        done = 0
        for f in concurrent.futures.as_completed(futures):
            done += 1
            res = f.result()
            if res:
                yield f"✅ Corte {res['seg_num']} OK", int(50 + (done/total*50))

                # --- AUTOMATIC YOUTUBE PUBLISH (V24.10) ---
                if publish_youtube:
                    try:
                        from backend import youtube_uploader
                        title = f"Destaque {job_id} #shorts"
                        youtube_uploader.upload_video(res['path'], title, hashtags)
                        yield f"🚀 Publicado no YouTube: {res['seg_num']}", int(50 + (done/total*50))
                    except Exception as e:
                        print(f"⚠️ Erro ao publicar: {e}")

                yield res['path']
    yield "✅ Finalizado!", 100
