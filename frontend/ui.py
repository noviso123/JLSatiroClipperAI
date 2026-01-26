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

def start_processing(url, model_type, burn_subs, cookies_file, oauth_file, progress=gr.Progress()):
    """Generator function for Gradio Output"""
    if not url:
        yield "⚠️ Erro: URL Vazia", []
        return

    # Settings
    settings = {
        "model": model_type,
        "lang": "Português (BR)",
        "burn_subtitles": burn_subs,
        "cookies_path": cookies_file.name if cookies_file else None,
        "oauth_path": oauth_file.name if oauth_file else None
    }

    # Clean Start
    progress(0, desc="Iniciando...")
    log_history = "🚀 Iniciando Fábrica...\n"

    # Cache gallery once to avoid looking at Drive every loop (V12.3 Fix)
    cached_gallery = scan_gallery()
    yield log_history, cached_gallery

    try:
        for result in processing.process_video(url, settings):
            if isinstance(result, tuple):
                status, pct = result
                # Update Visual Bar
                progress(pct / 100, desc=status)

                # Update Text Log
                log_history = f"[{pct}%] {status}\n" + log_history
                yield log_history, cached_gallery # Yield cached (fast)

            elif isinstance(result, str):
                # Finished Clip Path - NOW we refresh gallery
                log_history = f"✅ CORTE PRONTO: {os.path.basename(result)}\n" + log_history
                cached_gallery = scan_gallery() # Update cache
                yield log_history, cached_gallery

        log_history = "✨ PROCESSAMENTO FINALIZADO COM SUCESSO!\n" + log_history
        progress(1, desc="Concluído!")
        yield log_history, scan_gallery() # Final update

    except Exception as e:
        log_history = f"❌ Erro Crítico: {str(e)}\n" + log_history
        yield log_history, cached_gallery

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
with gr.Blocks(title="JLSatiro AI Studio V12.3", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎬 JLSatiro Clipper AI - V12.3 (STABLE LOGS)")
    gr.Markdown("### ⚡ Sistema de Cortes Virais Automáticos (Google API + Cookies)")

    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(label="YouTube URL", placeholder="https://youtube.com/...")
            model_drop = gr.Dropdown(["Vosk (Offline)", "Whisper"], label="Modelo", value="Vosk (Offline)")
            subs_check = gr.Checkbox(label="Queimar Legendas", value=True)

            with gr.Row():
                btn_run = gr.Button("🚀 INICIAR PROCESSAMENTO (Processar Fila)", variant="primary", scale=2)
                btn_reset = gr.Button("🗑️ LIMPAR TUDO", variant="stop", scale=1)

            # Stealth Mode Active (Default) -> Advanced Options below
            with gr.Accordion("🛡️ Acesso Avançado / Anti-Bot (Cookies & API)", open=False):
                gr.Markdown("### 🔐 Área de Credenciais (Opcional)")
                gr.Markdown("Se tiver problemas, suba seus arquivos aqui. O sistema salva automaticamente.")
                with gr.Row():
                    cookies_input = gr.File(label="1. Cookies (cookies.txt)", file_types=[".txt"])
                    oauth_input = gr.File(label="2. Client Secret (client_secret.json)", file_types=[".json"])

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
    btn_run.click(start_processing, inputs=[url_input, model_drop, subs_check, cookies_input, oauth_input], outputs=[logs, gallery])
    btn_reset.click(delete_all, outputs=[reset_msg, gallery])

if __name__ == "__main__":
    # SHARE=TRUE creates the public link automatically!
    demo.launch(share=True, allowed_paths=["/content/drive"])
