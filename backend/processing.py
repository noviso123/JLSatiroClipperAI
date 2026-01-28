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

    # --- RENDER PIPELINE (CPU) ---
    raw_cut_path = os.path.join(work_dir, f"raw_cut_{job_id}.mp4")
    raw_cut_audio = os.path.join(work_dir, f"raw_cut_{job_id}.wav")

    # Detect GPU capabilities FIRST - DISABLED FOR STABILITY LOCAL CPU
    use_nvenc = False
    use_cuda_filters = False

    # Smart Crop Coords (Batch Cache)
    speaker_x_norm = video_engine.get_crop_from_cache(start_t, dur, face_map)
    scaled_w = 853
    crop_w = 270

    # Calculate crop X using centralized logic
    crop_x = video_engine.calculate_crop_x(speaker_x_norm, scaled_w, crop_w)

    # Build Filter Complex (Centralized)
    filter_complex = video_engine.build_vertical_filter_complex(crop_x, crop_w, use_cuda=use_cuda_filters)

    ffmpeg_cmd = ['ffmpeg', '-y', '-max_muxing_queue_size', '9999', '-fflags', '+genpts+igndts', '-avoid_negative_ts', 'make_zero']
    # Force CPU decoding/encoding for stability
    ffmpeg_cmd.extend(['-ss', str(start_t), '-t', str(dur), '-i', video_path])
    ffmpeg_cmd.extend(['-filter_complex', filter_complex, '-r', '30', '-vsync', 'cfr'])

    # CPU x264 basic settings
    ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23'])

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

    # Force CPU Encoding (Stability)
    burn_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23'])
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
    # --- CONCAT ---
    final_out_local = os.path.join(work_dir, f"viral_clip_{seg_num}_{job_id}.mp4")
    list_txt = os.path.join(work_dir, f"list_{job_id}.txt")

    with open(list_txt, 'w') as f:
        if os.path.exists(thumb_out): f.write(f"file '{os.path.abspath(thumb_out)}'\\n")
        if os.path.exists(final_hook): f.write(f"file '{os.path.abspath(final_hook)}'\\n")
        f.write(f"file '{os.path.abspath(subtitled_cut)}'\\n")

    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_txt, '-c', 'copy', final_out_local, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "path": final_out_local,
        "seg_num": seg_num,
        "job_id": job_id,
        "clip_words": clip_words
    }

def process_video(url, video_file, settings):
    import os # Force local scope to avoid UnboundLocalError
    settings['lang'] = 'Português (BR)'

    # Optimization: Setup is now done in Installation Phase (Step 2)

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
            video_engine.download_strategy_pytubefix(url, video_path)
        except Exception as e:
             yield f"❌ Falha no Download (Pytubefix): {e}", 0; return

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
    # LOCAL CPU OPTIMIZATION: Calculate workers based on CPU Cores
    # LOCAL CPU OPTIMIZATION: Calculate workers based on CPU Cores
    # (import os moved to top level)
    try:
        cpu_cores = os.cpu_count() or 4
        # Reserve 2 cores for System/Chrome, use rest for workers (min 1)
        max_workers = max(1, cpu_cores - 2)
        print(f"🚀 Workers Dinâmicos (CPU): {max_workers} (Cores: {cpu_cores})")
    except Exception as e:
        print(f"⚠️ Erro ao calcular workers cpu: {e}")
        max_workers = 2 # Safe fallback

    state_manager.append_log(f"🚀 Iniciando Workers V23.0 ({max_workers})...")

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
