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
            _CACHED_MODEL = WhisperModel("large-v3", device="cuda", compute_type="float16")
        except Exception as e:
            print(f"⚠️ GPU Falhou. Usando CPU (int8)... Erro: {e}")
            _CACHED_MODEL = WhisperModel("small", device="cpu", compute_type="int8")
    return _CACHED_MODEL

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
