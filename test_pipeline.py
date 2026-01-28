import os
import sys
import shutil
import subprocess
from modules import downloader, transcriber, cropper, renderer, segmenter

# Mocking Gradio-like file object for local test
class LocalFile:
    def __init__(self, path):
        self.name = path

def run_test():
    print("🧪 INICIANDO TESTE DE PONTA A PONTA (HEADLESS)...")

    WORK_DIR = "test_run"
    OUTPUT_DIR = "test_output"
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Input video from previous run
    input_video = "temp_workspace/source.mp4"
    if not os.path.exists(input_video):
        print("❌ Vídeo de teste não encontrado!")
        return

    video_path = os.path.join(WORK_DIR, "source.mp4")
    shutil.copy(input_video, video_path)

    print("🔊 Extraindo Áudio...")
    audio_path = os.path.join(WORK_DIR, "source.wav")
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path, '-vn', '-ac', '1', '-ar', '16000', audio_path
    ], check=True)

    print("📝 Transcrevendo (Whisper Small)...")
    words = transcriber.transcribe_audio(audio_path)
    print(f"✅ Transcrição: {len(words)} palavras encontradas.")

    print("✂️ Segmentando...")
    segments = segmenter.segment_transcript(words)
    print(f"✅ Segmentação: {len(segments)} cortes.")

    print("👁️ Escaneando Rosto...")
    face_map = cropper.scan_face(video_path)
    print(f"✅ Scan Facial: {len(face_map)} pontos.")

    print("🎬 Renderizando primeiro clip...")
    if segments:
        # Just test the first one to save time
        test_segments = [segments[0]]
        clips = renderer.render_clips(video_path, test_segments, face_map, OUTPUT_DIR)
        if clips:
            print(f"🎉 SUCESSO! Clip gerado em: {clips[0]}")
        else:
            print("❌ Falha na renderização.")
    else:
        print("⚠️ Nenhum segmento para testar.")

if __name__ == "__main__":
    run_test()
