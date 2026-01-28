import os
from faster_whisper import WhisperModel

# Global Model Cache
_MODEL = None

def load_model():
    global _MODEL
    if _MODEL is None:
        # STRICT OFFLINE PATH
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "models", "whisper-tiny")

        print(f"🧠 Carregando Modelo Local (HYPER-TURBO): {model_path} ...")

        if not os.path.exists(model_path):
             print(f"❌ ERRO CRÍTICO: Modelo não encontrado em '{model_path}'!")
             print("👉 Execute o arquivo 'setup_models.bat' (Download Manual) primeiro.")
             raise FileNotFoundError("Modelo offline não encontrado.")

        try:
            # FORCE CPU / INT8 - Local Path - 12 THREADS (MAX)
            _MODEL = WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=12, local_files_only=True)
            print("✅ Modelo Carregado (Modo HYPER-TURBO Offline).")
        except Exception as e:
            print(f"⚠️ Erro Fatal no Modelo Offline: {e}")
            raise e
    return _MODEL

def transcribe_audio(audio_path):
    """
    Transcribes audio and returns word-level timestamps.
    """
    model = load_model()
    print(f"📝 Transcrevendo (Beam 1)...")

    # Beam Size 1 = Greedy = Fastest
    segments, info = model.transcribe(
        audio_path,
        beam_size=1,
        language="pt",
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False
    )

    words = []
    for segment in segments:
        for word in segment.words:
            words.append({
                "word": word.word,
                "start": word.start,
                "end": word.end
            })

    return words
