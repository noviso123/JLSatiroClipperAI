import os
import ssl
from faster_whisper import WhisperModel

# Titanium Global SSL Bypass: Mandatory for restricted network environments
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except: pass

# --- Global Cache ---
_CACHED_MODEL = None

def get_cached_model():
    global _CACHED_MODEL
    if _CACHED_MODEL is None:
        # Titanium Hermetic Protocol: Strictly Local
        local_project_model = os.path.join(os.getcwd(), "models", "whisper-tiny")

        if os.path.exists(local_project_model):
            print(f"📦 Carregando Cérebro Whisper (OFFLINE)...")
            try:
                cpu_cores = os.cpu_count() or 4
                _CACHED_MODEL = WhisperModel(local_project_model, device="cpu", compute_type="int8", cpu_threads=cpu_cores, num_workers=cpu_cores, local_files_only=True)
                return _CACHED_MODEL
            except Exception as e:
                print(f"❌ Erro ao carregar inteligência local: {e}")
        else:
            print(f"🚨 ERRO CRÍTICO: Inteligência não encontrada em {local_project_model}")
            print("👉 Certifique-se de que a pasta 'models' está presente na raiz.")

        _CACHED_MODEL = None
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

    # Titanium Hermetic: Using only essential stable arguments
    segments, info = model.transcribe(
        audio_path,
        beam_size=1,
        language="pt",
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False
    )

    from backend import state_manager
    all_words = []

    # Track segment progress for real-time feedback
    seg_count = 0
    for segment in segments:
        seg_count += 1
        txt = segment.text.strip()
        if txt:
            state_manager.append_log(f"🎙️ [Transcrição] {txt}")
            state_manager.beat() # Keep UI alive

        for word in segment.words:
            all_words.append({
                "word": word.word,
                "start": word.start,
                "end": word.end
            })

    state_manager.append_log(f"✅ Transcrição Concluída ({seg_count} frases).")
    return all_words

def generate_hook_narrator(text, output_path):
    """
    Titan Resilient Narrator: Prioritizes local files, then downloads with SSL bypass.
    """
    import asyncio
    import edge_tts
    import ssl
    import hashlib
    import subprocess
    import shutil

    # 1. Local Cache Check (Avoid SSL problems)
    clean_text = "".join([c for c in text.upper() if c.isalnum() or c.isspace()]).strip()
    hash_txt = hashlib.md5(clean_text.encode()).hexdigest()[:10]
    local_hook = os.path.join("models", "hooks", f"{hash_txt}.mp3")

    if os.path.exists(local_hook):
        print(f"💎 Usando Hook Offline: {text}")
        shutil.copy(local_hook, output_path)
        return True

    # 2. Online Attempt with SSL Bypass
    print(f"🎙️ Tentando gerar Narrador online: {text}")
    try:
        ssl_ctx = ssl._create_unverified_context()
        VOICE = "pt-BR-AntonioNeural"

        async def _download():
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(output_path)
            # Try to cache for next time
            os.makedirs(os.path.dirname(local_hook), exist_ok=True)
            try: shutil.copy(output_path, local_hook)
            except: pass
            return True

        asyncio.run(_download())
        return os.path.exists(output_path)
    except Exception as e:
        print(f"⚠️ Falha no Narrador TTS: {e}")
        # Final Fallback: 3s Silence to maintain video timing
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-t', '3', '-c:a', 'aac', '-ar', '44100', output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False
