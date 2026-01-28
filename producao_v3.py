import os
import sys
import shutil
import time
from modules import downloader, transcriber, segmenter, cropper, renderer, youtube_uploader

# Configurações
VIDEO_URL = "https://www.youtube.com/watch?v=kYfNvmF0Bqw" # Simon Sinek - Performance vs Trust
WORK_DIR = "production_temp"
OUTPUT_DIR = "production_output"

def run_production():
    print("🚀 INICIANDO PRODUÇÃO TITANIUM V3 - MODO END-TO-END")
    print("-" * 60)

    # 0. Limpeza
    if os.path.exists(WORK_DIR): shutil.rmtree(WORK_DIR)
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(WORK_DIR)
    os.makedirs(OUTPUT_DIR)

    # 1. Download
    print("\n[1/6] Baixando vídeo fonte...")
    source_path = os.path.join(WORK_DIR, "source.mp4")
    dl_path = downloader.download_video(VIDEO_URL, source_path)
    if not dl_path:
        print("❌ Falha no download.")
        return

    # 2. Transcrição
    print("\n[2/6] Transcrevendo com AI Whisper (CPU)...")
    audio_path = os.path.join(WORK_DIR, "source.wav")
    os.system(f'ffmpeg -y -i "{source_path}" -vn -ac 1 -ar 16000 "{audio_path}" > nul 2>&1')
    words = transcriber.transcribe_audio(audio_path)
    full_text = " ".join([w['word'] for w in words])
    print(f"✅ Transcrição concluída: {len(full_text)} caracteres.")

    # 3. Segmentação
    print("\n[3/6] Identificando ganchos virais...")
    segments = segmenter.segment_transcript(words)
    print(f"✅ Encontrados {len(segments)} segmentos potenciais.")

    # 4. Scanning & Face Tracking
    print("\n[4/6] Escaneando enquadramento (IA Inteligente)...")
    face_map = cropper.scan_face(source_path)

    # 5. Renderização (Legendas + Crop 9:16)
    print("\n[5/6] Renderizando clips verticais...")
    clips = renderer.render_clips(source_path, segments, face_map, OUTPUT_DIR, words)
    print(f"✅ {len(clips)} vídeos gerados e prontos para o YouTube.")

    # 6. Postagem Agendada
    print("\n[6/6] Iniciando agendamento em massa (5/dia)...")
    for i, clip_path in enumerate(clips):
        title = f"Liderança Impactante #{i+1} "
        # Hashtags e comentário de exemplo
        hashtags = "#lideranca #sucesso #podcast #shorts"
        comment = "👇 Qual sua visão sobre isso? Comente abaixo!"

        try:
            print(f"📤 Subindo Clip #{i+1}...")
            video_id, publish_at = youtube_uploader.upload_short(
                clip_path, title, full_text, hashtags, comment
            )
            print(f"✅ AGENDADO: {publish_at} | Link: https://youtu.be/{video_id}")
            # Pequeno delay para API respirar
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Erro no vídeo {i+1}: {e}")

    print("\n" + "="*40)
    print("🏆 PRODUÇÃO COMPLETA CONCLUÍDA COM SUCESSO!")
    print(f"Os vídeos estão na pasta: {OUTPUT_DIR}")
    print("="*40)

if __name__ == "__main__":
    run_production()
