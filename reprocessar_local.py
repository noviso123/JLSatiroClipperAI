import os
import sys
import shutil
import time
from modules import downloader, transcriber, segmenter, cropper, renderer, youtube_uploader

# Configurações
WORK_DIR = "production_temp"
OUTPUT_DIR = "production_output"
SOURCE_MP4 = os.path.join(WORK_DIR, "source.mp4")

def run_local_production():
    print("🚀 INICIANDO RE-PROCESSAMENTO LOCAL TITANIUM V3")
    print("-" * 60)

    # 0. Verificação
    if not os.path.exists(SOURCE_MP4):
        print(f"❌ Erro: O vídeo fonte não foi encontrado em {SOURCE_MP4}")
        print("Certifique-se de que o download foi feito anteriormente.")
        return

    # Limpa apenas a pasta de saída para o novo teste
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 1. Transcrição (Sempre bom re-gerar para garantir que o audio_path está correto)
    print("\n[1/5] Extraindo áudio e Transcrevendo...")
    audio_path = os.path.join(WORK_DIR, "source.wav")
    os.system(f'ffmpeg -y -i "{SOURCE_MP4}" -vn -ac 1 -ar 16000 "{audio_path}" > nul 2>&1')

    words = transcriber.transcribe_audio(audio_path)
    full_text = " ".join([w['word'] for w in words])
    print(f"✅ Transcrição concluída: {len(full_text)} caracteres.")

    if not words:
        print("⚠️ Alerta: Transcrição vazia. Verificando se há áudio...")

    # 2. Segmentação
    print("\n[2/5] Identificando ganchos virais...")
    segments = segmenter.segment_transcript(words)
    print(f"✅ Encontrados {len(segments)} segmentos potenciais.")

    # 3. Scanning & Face Tracking
    print("\n[3/5] Escaneando enquadramento (IA Inteligente)...")
    face_map = cropper.scan_face(SOURCE_MP4)

    # 4. Renderização (Legendas + Crop 9:16 + TTS + Thumb)
    print("\n[4/5] Renderizando clips verticais...")
    clips = renderer.render_clips(SOURCE_MP4, segments, face_map, OUTPUT_DIR, words)
    print(f"✅ {len(clips)} vídeos gerados.")

    # 5. Tentativa de Upload (Mesmo sabendo do limite, vamos tentar para logar o resultado)
    print("\n[5/5] Iniciando tentativa de agendamento...")
    for i, clip_path in enumerate(clips):
        title = f"Teste Local Titanium #{i+1} "
        hashtags = "#testelocal #shorts #ia"
        comment = "Teste de reprocessamento local concluído!"

        try:
            print(f"📤 Subindo Clip #{i+1}...")
            video_id, publish_at = youtube_uploader.upload_short(
                clip_path, title, full_text, hashtags, comment
            )
            print(f"✅ AGENDADO: {publish_at} | Link: https://youtu.be/{video_id}")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Status de Upload: {e}")

    print("\n" + "="*40)
    print("🏆 RE-PROCESSAMENTO LOCAL CONCLUÍDO!")
    print(f"Os novos vídeos estão em: {OUTPUT_DIR}")
    print("="*40)

if __name__ == "__main__":
    run_local_production()
