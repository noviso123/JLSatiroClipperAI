import os
from faster_whisper import WhisperModel

# --- Global Cache ---
_CACHED_MODEL = None

def get_cached_model():
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        print(f"⚡ Carregando Modelo HYPER-SPEED (Faster-Whisper Large-V3)...")
        try:
            # float16 is native for T4. device='cuda' is mandatory.
            # OPTIMIZATION: int8_float16 uses Tensor Cores for 2-3x speedup on T4
            _CACHED_MODEL = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
        except Exception as e:
            print(f"⚠️ GPU Falhou. Usando CPU (int8)... Erro: {e}")
            _CACHED_MODEL = WhisperModel("small", device="cpu", compute_type="int8")
    return _CACHED_MODEL

def warmup_model():
    import numpy as np
    import wave
    import tempfile

    print("🔥 Aquecendo Motor Whisper (Warmup)...")
    try:
        model = get_cached_model()
        dummy_path = tempfile.mktemp(suffix=".wav")

        with wave.open(dummy_path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(np.zeros(16000, dtype=np.int16).tobytes())

        # Run dummy inference
        model.transcribe(dummy_path, beam_size=1, language="pt")
        os.remove(dummy_path)
        print("✅ Modelo Pronto e Aquecido!")
    except Exception as e:
        print(f"⚠️ Warmup falhou (não crítico): {e}")

def get_transcription(audio_path):
    """
    Transcribes audio using Faster-Whisper (CTranslate2).
    Returns list of dicts: {'word': str, 'start': float, 'end': float}
    """
    model = get_cached_model()

    print(f"⚡ Transcrevendo (Hyper-Speed C++ Engine)... {os.path.basename(audio_path)}")

    # Phase 1 Optimization: beam_size=1 (Greedy)
    segments, info = model.transcribe(
        audio_path,
        beam_size=1,
        best_of=None,
        language="pt",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False
    )

    all_words = []
    for segment in segments:
        for word in segment.words:
            all_words.append({
                "word": word.word,
                "start": word.start,
                "end": word.end
            })

    return all_words

def analyze_energy_segmentation(audio_path, full_words, target_duration=60):
    """
    Phase 6: Advanced Energy-Based Segmentation (Librosa).
    """
    try:
        import librosa
        import numpy as np

        print("⚡ Analisando Energia do Áudio (Librosa)...")
        y, sr = librosa.load(audio_path, sr=16000)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=512)

        segments = []
        current_start = 0

        while current_start < len(full_words):
            start_time = full_words[current_start]['start']
            target_end = start_time + target_duration

            best_score = -1
            best_idx = -1

            # Scan candidates around target duration (+- 10s)
            for i in range(current_start, len(full_words)):
                w = full_words[i]
                if w['end'] > (target_end + 15): break # Optimization: limit scan
                if w['end'] < (target_end - 15): continue

                # Metrics
                dist_penalty = abs(w['end'] - target_end) / 15.0 # 0.0 to 1.0 (lower is better)

                # Pause Score
                pause_dur = 0
                if i+1 < len(full_words):
                    pause_dur = full_words[i+1]['start'] - w['end']
                pause_score = min(pause_dur / 1.0, 1.0) # 1.0 = 1s pause (good)

                # Energy Score
                time_idx = np.searchsorted(times, w['end'])
                energy_score = 1.0
                if time_idx < len(rms):
                    # Invert energy: we want LOW energy cuts
                    norm_energy = rms[time_idx] / (np.max(rms) + 1e-6)
                    energy_score = 1.0 - norm_energy

                # Final Score (Weighted)
                # We want: Close to target time, High Pause, Low Energy
                score = (0.3 * (1 - dist_penalty)) + (0.4 * pause_score) + (0.3 * energy_score)

                if score > best_score:
                    best_score = score
                    best_idx = i

            if best_idx != -1:
                segments.append({'start': start_time, 'end': full_words[best_idx]['end']})
                current_start = best_idx + 1
            else:
                # Fallback: Just cut at target
                segments.append({'start': start_time, 'end': min(target_end, full_words[-1]['end'])})
                # Advance approximate words based on 150wpm (2.5 wps)
                approx_words = int(60 * 2.5)
                current_start += approx_words
                if current_start >= len(full_words): break

        print(f"⚡ Segmentação por Energia: {len(segments)} cortes refinados.")
        return segments

    except Exception as e:
        print(f"⚠️ Erro Librosa (Fallback Simples): {e}")
        return None
