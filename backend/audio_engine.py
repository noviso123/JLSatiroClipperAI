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
