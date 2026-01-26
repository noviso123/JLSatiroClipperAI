import gradio as gr
import os
import time
import shutil
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import processing

# Global Work Vars
DRIVE_GALLERY = "/content/drive/MyDrive/JLSatiro_AI_Studio"
LOCAL_GALLERY = "downloads" # Symlink

# Ensure directories
os.makedirs("downloads", exist_ok=True)

def scan_gallery():
    """Returns a list of video paths for the gallery"""
    clips = []
    if os.path.exists(LOCAL_GALLERY):
        for f in os.listdir(LOCAL_GALLERY):
            if f.endswith(".mp4"):
                clips.append(os.path.join(LOCAL_GALLERY, f))
    # Sort by new
    clips.sort(key=os.path.getmtime, reverse=True)
    # Gradio Gallery expects a list of (path, label) tuples or just paths
    return clips

def start_processing(url, model_type, burn_subs, cookies_file, progress=gr.Progress()):
    """Generator function for Gradio Output"""
    if not url:
        yield "⚠️ Erro: URL Vazia", []
        return

    # Settings
    settings = {
        "model": model_type,
        "lang": "Português (BR)",
        "burn_subtitles": burn_subs,
        "cookies_path": cookies_file.name if cookies_file else None
    }

    log_history = ""

    # Clean Start
    progress(0, desc="Iniciando...")
    yield "🚀 Iniciando Fábrica...", scan_gallery()

    try:
        for result in processing.process_video(url, settings):
            if isinstance(result, tuple):
                status, pct = result
                # Update Visual Bar
                progress(pct / 100, desc=status)

                # Update Text Log
                log_history = f"[{pct}%] {status}\n" + log_history
                yield log_history, scan_gallery()

            elif isinstance(result, str):
                # Finished Clip Path
                log_history = f"✅ CORTE PRONTO: {os.path.basename(result)}\n" + log_history
                yield log_history, scan_gallery()

        log_history = "✨ PROCESSAMENTO FINALIZADO COM SUCESSO!\n" + log_history
        progress(1, desc="Concluído!")
        yield log_history, scan_gallery()

    except Exception as e:
        yield f"❌ Erro Crítico: {str(e)}", scan_gallery()

def delete_all():
    """Factory Reset"""
    try:
        shutil.rmtree("/content/temp_work", ignore_errors=True)
        # Clear Drive? User asked for total delete.
        # But let's be safe, maybe just clean local?
        # The user's request "APAGAR POR COMPLETO" usually implies result files too.
        if os.path.exists(LOCAL_GALLERY):
             for f in os.listdir(LOCAL_GALLERY):
                 fp = os.path.join(LOCAL_GALLERY, f)
                 if os.path.isfile(fp): os.unlink(fp)
        return "♻️ Sistema e Galeria Formatados!", scan_gallery()
    except Exception as e:
        return f"Erro ao limpar: {e}", scan_gallery()

# --- INTERFACE ---
with gr.Blocks(title="JLSatiro AI Studio V7.2", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎬 JLSatiro Clipper AI - V7.2 (LIGHT EDITION)")
    gr.Markdown("### ⚡ Sistema de Cortes Virais Automáticos (Gradio)")

    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(label="YouTube URL", placeholder="https://youtube.com/...")
            model_drop = gr.Dropdown(["Vosk (Offline)", "Whisper"], label="Modelo", value="Vosk (Offline)")
            subs_check = gr.Checkbox(label="Queimar Legendas", value=True)

            with gr.Row():
                btn_run = gr.Button("🚀 INICIAR PROCESSAMENTO (Processar Fila)", variant="primary", scale=2)
                btn_reset = gr.Button("🗑️ LIMPAR TUDO", variant="stop", scale=1)

            with gr.Accordion("🔑 AUTENTICAÇÃO YOUTUBE (Anti-Bloqueio)", open=True):
                gr.Markdown("⚠️ **Obrigatório se aparecer erro de 'Sign in'**.")
                gr.Markdown("Use a extensão **'Get cookies.txt LOCALLY'** para baixar o arquivo.")
                cookies_input = gr.File(label="ARRASTE O ARQUIVO 'cookies.txt' AQUI 👇", file_types=[".txt"])

            reset_msg = gr.Textbox(label="Status do Sistema", interactive=False, placeholder="O sistema está pronto.")

        with gr.Column(scale=2):
            logs = gr.TextArea(label="📜 Log de Execução (Acompanhe aqui)", lines=12, interactive=False, show_copy_button=True)

    gr.Markdown("---")
    gr.Markdown("## 📂 Sua Galeria (Google Drive)")
    gr.Markdown("_Os vídeos aparecem aqui automaticamente assim que ficam prontos._")
    gallery = gr.Gallery(label="Cortes Prontos", columns=[3], rows=[2], object_fit="contain", height="auto", show_share_button=True)

    # Refresh gallery on load
    demo.load(scan_gallery, outputs=gallery)

    # Actions
    btn_run.click(start_processing, inputs=[url_input, model_drop, subs_check, cookies_input], outputs=[logs, gallery])
    btn_reset.click(delete_all, outputs=[reset_msg, gallery])

if __name__ == "__main__":
    # SHARE=TRUE creates the public link automatically!
    demo.launch(share=True, allowed_paths=["/content/drive"])
