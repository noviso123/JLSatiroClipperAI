import os
import shutil
import time
import subprocess
import concurrent.futures
from . import state_manager
from . import audio_engine
from . import video_engine
from . import subtitle_engine
from . import google_services

GLOBAL_GOOGLE_SERVICES = None

def init_google_services():
    global GLOBAL_GOOGLE_SERVICES
    if os.path.exists("client_secret.json"):
        try:
            GLOBAL_GOOGLE_SERVICES = google_services.GoogleServices()
            print("✅ Google Services Ativado!")
        except Exception as e:
            print(f"⚠️ Falha ao iniciar Google Services: {e}")
            GLOBAL_GOOGLE_SERVICES = None

init_google_services()

def process_single_segment(seg_data, video_path, work_dir, drive_dir):
    if len(seg_data) == 4: idx, seg, total_segs, face_map = seg_data
    else: idx, seg, total_segs = seg_data; face_map = {}

    seg_num = idx + 1
    job_id = f"{int(time.time())}_{idx+1}"

    print(f"✂️ [Thread-Worker] Iniciando Corte {seg_num}/{total_segs}...")

    start_t = seg['start']
    dur = seg['end'] - start_t

    # --- RENDER PIPELINE (GPU) ---
    raw_cut_path = os.path.join(work_dir, f"raw_cut_{job_id}.mp4")
    raw_cut_audio = os.path.join(work_dir, f"raw_cut_{job_id}.wav")

    # Smart Crop Coords (Batch Cache)
    speaker_x_norm = video_engine.get_crop_from_cache(start_t, dur, face_map)
    scaled_w = 853
    crop_w = 270
    center_px = speaker_x_norm * scaled_w
    crop_x = int(center_px - (crop_w / 2))
    if crop_x < 0: crop_x = 0
    if crop_x > (scaled_w - crop_w): crop_x = (scaled_w - crop_w)

    if use_cuda_filters:
        # Phase 7: GPU Filters (Hardware Accelerated)
        # Note: crop is usually CPU, so we download, crop, upload
        filter_complex = (
            f"[0:v]scale_cuda=-1:480,hwdownload,format=nv12,crop={crop_w}:480:{crop_x}:0,hwupload,"
            "scale_cuda=1080:1920[bg];"
            "[0:v]scale_cuda=1080:-1[fg];"
            "[bg][fg]overlay_cuda=(W-w)/2:(H-h)/2,hwdownload,format=yuv420p"
        )
    else:
        # Fallback CPU Filters
        filter_complex = (
            f"[0:v]scale=-1:480,crop={crop_w}:480:{crop_x}:0,boxblur=10:5,"
            "scale=1080:1920[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )

    use_nvenc = False
    use_cuda_filters = False
    try:
        res = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        if 'h264_nvenc' in res.stdout: use_nvenc = True

        res_flt = subprocess.run(['ffmpeg', '-filters'], capture_output=True, text=True)
        if 'scale_cuda' in res_flt.stdout and 'overlay_cuda' in res_flt.stdout:
            use_cuda_filters = True
    except: pass

    ffmpeg_cmd = ['ffmpeg', '-y', '-max_muxing_queue_size', '9999', '-fflags', '+genpts+igndts', '-avoid_negative_ts', 'make_zero']
    if use_nvenc:
        ffmpeg_cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda', '-c:v', 'h264_cuvid'])

    ffmpeg_cmd.extend(['-ss', str(start_t), '-t', str(dur), '-i', video_path])
    ffmpeg_cmd.extend(['-filter_complex', filter_complex, '-r', '30', '-vsync', 'cfr'])

    if use_nvenc:
        ffmpeg_cmd.extend([
            '-c:v', 'h264_nvenc',
            '-preset', 'p4',           # Medium (Balance Speed/Quality)
            '-tune', 'hq',
            '-profile:v', 'high',
            '-rc', 'vbr',              # Variable bitrate
            '-cq', '20',               # Quality 20 (High)
            '-b:v', '5M',
            '-maxrate', '8M',
            '-bufsize', '10M',
            '-spatial-aq', '1',
            '-temporal-aq', '1',
            '-rc-lookahead', '20'
        ])
    else:
        ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast'])

    ffmpeg_cmd.extend(['-c:a', 'aac', '-ar', '44100', raw_cut_path])

    try:
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)
        subprocess.run(['ffmpeg', '-i', raw_cut_path, '-ac', '1', '-ar', '16000', '-vn', raw_cut_audio, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"❌ Erro Render: {e}")
        return None

    # --- TRANSCRIPTION & SUBS ---
    try:
        clip_words = audio_engine.get_transcription(raw_cut_audio)
    except: return None

    ass_path = os.path.join(work_dir, f"subs_{job_id}.ass")
    ass_content = subtitle_engine.generate_karaoke_ass(clip_words)
    with open(ass_path, "w", encoding="utf-8") as f: f.write(ass_content)

    # --- BURN ---
    subtitled_cut = os.path.join(work_dir, f"main_clip_{job_id}.mp4")
    vf = f"ass={ass_path.replace(os.sep, '/')}"

    burn_cmd = ['ffmpeg', '-threads', '0', '-i', raw_cut_path, '-vf', vf, '-r', '30']
    if use_nvenc:
        burn_cmd.extend([
            '-c:v', 'h264_nvenc', '-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-cq', '20',
            '-b:v', '5M', '-maxrate', '8M', '-bufsize', '10M'
        ])
    else: burn_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast'])
    burn_cmd.extend(['-c:a', 'copy', subtitled_cut, '-y'])
    subprocess.run(burn_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # --- POST PROD (HOOK/THUMB) ---
    final_hook = os.path.join(work_dir, f"hook_{job_id}.mp4")
    thumb_out = os.path.join(work_dir, f"thumb_{job_id}.mp4")

    raw_hook = os.path.join(work_dir, f"hook_raw_{job_id}.mp4")
    hook_start = dur * 0.15
    subprocess.run(['ffmpeg', '-ss', str(hook_start), '-t', '3', '-i', subtitled_cut, '-c', 'copy', raw_hook, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    video_engine.create_narrator_hook(raw_hook, final_hook, "OLHA ISSO", job_id)
    video_engine.generate_thumbnail(raw_cut_path, thumb_out, job_id, text=f"PARTE {seg_num}")

    # --- CONCAT ---
    final_out_local = os.path.join(work_dir, f"viral_clip_{seg_num}_{job_id}.mp4")
    list_txt = os.path.join(work_dir, f"list_{job_id}.txt")

    with open(list_txt, 'w') as f:
        if os.path.exists(thumb_out): f.write(f"file '{os.path.abspath(thumb_out)}'\n")
        if os.path.exists(final_hook): f.write(f"file '{os.path.abspath(final_hook)}'\n")
        f.write(f"file '{os.path.abspath(subtitled_cut)}'\n")

    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt, '-c', 'copy', final_out_local, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "path": final_out_local,
        "seg_num": seg_num,
        "job_id": job_id,
        "clip_words": clip_words
    }

def process_video(url, video_file, settings):
    settings['lang'] = 'Português (BR)'

    try:
    try:
        # Optimization: Setup is now done in Installation Phase (Step 2)
        pass
    except: pass

    work_dir, drive_dir = video_engine.setup_directories()

    video_path = os.path.join(work_dir, "input_video.mp4")
    audio_path = os.path.join(work_dir, "input_audio.wav")

    # --- INPUT HANDLING ---
    if video_file:
         yield "📂 Arquivo Local...", 5
         try:
             input_path = video_file.name if hasattr(video_file, 'name') else video_file
             shutil.copy(input_path, video_path)
         except Exception as e:
             yield f"❌ Erro leitura: {e}", 0; return
    else:
        yield "⬇️ Baixando...", 5
        try:
            if not video_engine.download_authenticated_ytdlp(url, video_path):
                video_engine.download_strategy_pytubefix(url, video_path)
        except:
             yield "❌ Falha no Download.", 0; return

    # --- ANALYSIS ---
    yield "🔊 Extraindo Áudio...", 20
    subprocess.run(['ffmpeg', '-threads', '0', '-i', video_path, '-ac', '1', '-ar', '16000', '-vn', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    yield "🧠 Transcrevendo (Whisper)...", 30
    full_words = audio_engine.get_transcription(audio_path)
    if not full_words: yield "⚠️ Silêncio.", 100; return

    # BATCH SCAN (Phase 5)
    yield "👁️ Analisando Rosto (Global Scan)...", 33
    face_map = video_engine.scan_face_positions(video_path)

    # --- SEGMENTATION ---
    segments = []
    current_start_word = 0
    TARGET_DURATION = 60.0
    while current_start_word < len(full_words):
        start_time = full_words[current_start_word]['start']
        target_end = start_time + TARGET_DURATION
        best_end_idx = -1
        for i in range(current_start_word, len(full_words)):
            w = full_words[i]
            if w['end'] >= target_end:
                best_end_idx = i
                # Simple pause detection scan
                for j in range(i, min(len(full_words), i+30)):
                    if j+1 < len(full_words) and (full_words[j+1]['start'] - full_words[j]['end']) > 0.5:
                        best_end_idx = j; break
                break

        if best_end_idx == -1: best_end_idx = len(full_words) - 1
        seg_end_time = full_words[best_end_idx]['end']

        if (seg_end_time - start_time) >= 50.0:
            segments.append({'start': start_time, 'end': seg_end_time})

        current_start_word = best_end_idx + 1
        if current_start_word >= len(full_words): break

    yield f"📐 {len(segments)} Cortes Planejados.", 35

    # --- PARALLEL EXECUTION ---
    # DYNAMIC WORKERS: Calculate based on VRAM (Limit: 2GB per worker approx)
    max_workers = 2
    try:
        import torch
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            # Reserve 4GB for System/Whisper/LLM, use rest for workers (approx 1.5GB each for 1080p NVENC)
            # T4 (15GB) -> ~11GB Free -> ~6 Workers. Conservative: (VRAM - 4) / 1.5
            calc_workers = int((vram_gb - 4) / 1.5)
            max_workers = min(max(calc_workers, 2), 6) # Cap at 6 for stability
            print(f"🚀 Workers Dinâmicos: {max_workers} (VRAM: {vram_gb:.1f}GB)")
    except Exception as e:
        print(f"⚠️ Erro ao calcular workers dinâmicos: {e}")
        max_workers = 3 # Safe fallback

    state_manager.append_log(f"🚀 Iniciando Workers ({max_workers})...")

    seg_payloads = [(i, seg, len(segments), face_map) for i, seg in enumerate(segments)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Pass static checks to avoid pickling issues
        futures = {executor.submit(process_single_segment, p, video_path, work_dir, drive_dir): p for p in seg_payloads}

        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if not res or not os.path.exists(res['path']): continue

            # --- UPLOAD & METADATA ---
            fpath = res['path']
            snum = res['seg_num']
            cw = res['clip_words']
            jid = res['job_id']

            if GLOBAL_GOOGLE_SERVICES:
                yield f"☁️ Upload Cort {snum}...", 95
                GLOBAL_GOOGLE_SERVICES.upload_to_drive(fpath)

            if 'publish_youtube' in settings and settings['publish_youtube'] and GLOBAL_GOOGLE_SERVICES:
                yield f"📺 Publicando Corte {snum}...", 99

                # Hybrid Metadata
                meta_res = None
                try: # V20
                     from .neural_engine import NeuralEngine
                     ne = NeuralEngine()
                     if ne.client:
                         txt = " ".join([w['word'] for w in cw])
                         d = ne.generate(txt, settings.get('hashtags', ''))
                         if d:
                             from dataclasses import make_dataclass
                             MO = make_dataclass("MetaObj", [("title", str), ("description", str), ("tags", list), ("privacy", str), ("pinned_comment", str)])
                             meta_res = MO(**d)
                except: pass

                if not meta_res: # V19
                    try:
                        from .metadata_engine import MetadataEngine
                        meta_res = MetadataEngine().generate(cw, settings.get('hashtags', ''))
                    except: pass

                if meta_res:
                    ytid = GLOBAL_GOOGLE_SERVICES.upload_to_youtube(fpath, meta_res.title, meta_res.description, meta_res.tags, meta_res.privacy)
                    if ytid and meta_res.pinned_comment:
                        GLOBAL_GOOGLE_SERVICES.post_comment(ytid, meta_res.pinned_comment)

            video_engine.cleanup_temps(work_dir, jid)
            yield fpath # Return to UI

    state_manager.append_log("✅ Lote Finalizado!")
    yield "✅ Lote Finalizado!", 100
