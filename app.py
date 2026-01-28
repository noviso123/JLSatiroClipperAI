import gradio as gr
import os
import shutil
import subprocess
from modules import downloader, transcriber, cropper, renderer, segmenter, youtube_uploader

# CLEANUP
WORK_DIR = "temp_workspace"
OUTPUT_DIR = "output_clips"
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def pipeline(url, local_file, auto_upload, user_hashtags, pinned_comment):
    yield "⬇️ Verificando Entrada..."
    video_path = os.path.join(WORK_DIR, "source.mp4")

    # 1. Input Handling
    if local_file:
         yield "📂 Usando Arquivo Local..."
         try:
             input_path = local_file.name if hasattr(local_file, 'name') else local_file
             shutil.copy(input_path, video_path)
         except Exception as e:
             yield f"❌ Erro ao ler arquivo: {e}"
             return
    elif url:
        yield "⬇️ Baixando do YouTube..."
        dl_path = downloader.download_video(url, video_path)
        if not dl_path:
            yield "❌ Erro no Download. Verifique o link."
            return
    else:
        yield "⚠️ Por favor, forneça um Link ou um Arquivo."
        return

    # 2. Extract Audio
    yield "🔊 Extraindo Áudio..."
    audio_path = os.path.join(WORK_DIR, "source.wav")
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path, '-vn', '-ac', '1', '-ar', '16000', audio_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except:
        yield "❌ Erro no FFmpeg (Audio extraction)."
        return

    # 3. Transcribe
    yield "📝 Transcrevendo (Whisper CPU)..."
    try:
        words = transcriber.transcribe_audio(audio_path)
        full_text = " ".join([w['word'] for w in words])
    except Exception as e:
        yield f"❌ Erro Transcrição: {e}"
        return

    # 4. Segment
    segments = segmenter.segment_transcript(words)
    if not segments:
        yield "⚠️ Nenhum segmento viável encontrado."
        return

    yield f"found {len(segments)} segments. Scanning Faces..."

    # 5. Crop Scan
    yield "👁️ Escaneando Rosto (OpenCV)..."
    face_map = cropper.scan_face(video_path)

    # 6. Render
    yield "🎬 Renderizando Clips com Legendas e Ganchos..."
    clips = renderer.render_clips(video_path, segments, face_map, OUTPUT_DIR, words)

    # 7. Auto-Upload to YouTube
    if auto_upload:
        yield f"🚀 Iniciando postagem automática de {len(clips)} vídeos..."
        for i, clip_path in enumerate(clips):
            try:
                # Use context from segment for better titles
                seg_text = segments[i]['text'][:30] if i < len(segments) else "Corte Viral"
                title = f"Viral Clip #{i+1} - {seg_text}..."

                yield f"📤 Subindo e Agendando {title}..."
                video_id, publish_time = youtube_uploader.upload_short(
                    clip_path, title, full_text, user_hashtags, pinned_comment
                )
                yield f"✅ Vídeo #{i+1} AGENDADO para {publish_time}! ID: {video_id}"
            except Exception as e:
                yield f"❌ Erro no Upload do Vídeo #{i+1}: {e}"

    yield f"✅ Concluído! {len(clips)} clips gerados na pasta '{OUTPUT_DIR}'."

# UI
with gr.Blocks(title="JLSatiro Clipper V3 (Ultra Viral Edition)", analytics_enabled=False) as app:
    gr.Markdown("# 🚀 JLSatiro Clipper V3 (Titanium AI Edition)")
    gr.Markdown("Transforme vídeos em Shorts Virais com agendamento automático e inteligência de retenção.")

    with gr.Row():
        with gr.Column():
            url_input = gr.Textbox(label="Opção A: YouTube URL", placeholder="Cole o link aqui...")
            gr.Markdown("**OU**")
            file_input = gr.File(label="Opção B: Upload de Arquivo (MP4)", file_types=[".mp4"], interactive=True)

            with gr.Group():
                gr.Markdown("### ⚙️ YouTube Shorts / Postagem")
                upload_toggle = gr.Checkbox(label="Ativar Postagem Automática Agendada (5/dia)", value=True)
                hashtags_input = gr.Textbox(
                    label="Hashtags Fixas (Opcional)",
                    placeholder="Ex: #foco #podcast (Vazio = Gerar Automatico)",
                    lines=2
                )
                comment_input = gr.Textbox(
                    label="Comentário para Fixar (CTA)",
                    placeholder="Ex: Inscreva-se para mais cortes!",
                    lines=2
                )

        btn_start = gr.Button("🚀 INICIAR PRODUÇÃO GIGANTE", variant="primary")

    status_output = gr.Textbox(label="Status / Logs", interactive=False)

    btn_start.click(
        pipeline,
        inputs=[url_input, file_input, upload_toggle, hashtags_input, comment_input],
        outputs=[status_output]
    )

if __name__ == "__main__":
    # NUCLEAR SSL FIX
    os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
    import requests
    from functools import partial

    old_request = requests.Session.request
    def new_request(self, method, url, *args, **kwargs):
        kwargs['verify'] = False
        return old_request(self, method, url, *args, **kwargs)
    requests.Session.request = new_request
    requests.request = partial(requests.request, verify=False)
    requests.get = partial(requests.get, verify=False)

    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

    print("🌍 Iniciando Servidor V3 (Production)...")
    app.queue().launch(share=False, server_name="127.0.0.1", server_port=7865)
