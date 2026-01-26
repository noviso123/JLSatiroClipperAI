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
        try:
            for f in os.listdir(LOCAL_GALLERY):
                if f.endswith(".mp4"):
                    clips.append(os.path.join(LOCAL_GALLERY, f))
        except: pass
    # Sort by new
    try:
        clips.sort(key=os.path.getmtime, reverse=True)
    except: pass
    return clips

def start_processing(url, model_type, burn_subs, cookies_file, oauth_file, progress=gr.Progress()):
    """Generator function for Gradio Output"""
    if not url:
        yield "⚠️ Erro: URL Vazia", gr.Skip()
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
    log_history = "💎 Iniciando Motor Cobalt V13.3...\n"

    # V12.4 FIX: Use gr.skip() to avoid touching the Gallery (blocked by Drive IO)
    yield log_history, gr.skip()

    try:
        for result in processing.process_video(url, settings):
            if isinstance(result, tuple):
                status, pct = result
                # Update Visual Bar
                progress(pct / 100, desc=status)

                # Update Text Log
                log_history = f"[{pct}%] {status}\n" + log_history
                yield log_history, gr.skip() # Update logs, SKIP gallery (Fastest)

            elif isinstance(result, str):
                # Finished Clip Path - NOW we refresh gallery (Only once at end of clip)
                log_history = f"✅ CORTE PRONTO: {os.path.basename(result)}\n" + log_history
                yield log_history, scan_gallery()

        log_history = "✨ PROCESSAMENTO FINALIZADO COM SUCESSO!\n" + log_history
        progress(1, desc="Concluído!")
        yield log_history, scan_gallery() # Final update

    except Exception as e:
        log_history = f"❌ Erro Crítico: {str(e)}\n" + log_history
        yield log_history, gr.skip()

def delete_all():
    """Factory Reset"""
    try:
        shutil.rmtree("/content/temp_work", ignore_errors=True)
        if os.path.exists(LOCAL_GALLERY):
             for f in os.listdir(LOCAL_GALLERY):
                 fp = os.path.join(LOCAL_GALLERY, f)
                 if os.path.isfile(fp): os.unlink(fp)
        return "♻️ Sistema e Galeria Formatados!", scan_gallery()
    except Exception as e:
        return f"Erro ao limpar: {e}", scan_gallery()

# --- INTERFACE (V13.3 COBALT DESIGN) ---
cobalt_theme = gr.themes.Ocean(
    primary_hue="indigo",
    secondary_hue="zinc",
    neutral_hue="slate",
    text_size="lg",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"]
)

with gr.Blocks(title="JLSatiro Cobalt V15.5 (CPU)", theme=cobalt_theme) as demo:
    with gr.Column(elem_id="main_container", variant="panel"):
        gr.Markdown(
            """
            # 💎 JLSatiro Cobalt V13.3
            ### *Clean. Fast. Private. High RAM Usage.*
            """
        )

        # COBALT-STYLE: Input is King
        with gr.Group():
            url_input = gr.Textbox(
                label="",
                placeholder="Cole o link do YouTube aqui...",
                show_label=False,
                container=False,
                scale=3,
                lines=1
            )
            with gr.Row():
                model_drop = gr.Dropdown(["Vosk (Offline)", "Whisper"], value="Vosk (Offline)", show_label=False, container=False, scale=1)
                subs_check = gr.Checkbox(label="Legendas", value=True, container=False, scale=0)
                btn_run = gr.Button("BAIXAR & CORTAR", variant="primary", scale=1)

        # Hidden/Advanced (Cobalt hides complexity)
        with gr.Accordion("⚙️ Configurações Avançadas / Autenticação", open=False):
             gr.Markdown("### 🔐 Credenciais (Anti-Bot)")
             cookies_input = gr.File(label="Cookies (cookies.txt)", file_types=[".txt"])
             oauth_input = gr.File(label="Client Secret (json)", file_types=[".json"])
             btn_reset = gr.Button("🗑️ Limpar Cache", variant="secondary", size="sm")
             reset_msg = gr.Textbox(interactive=False, show_label=False)

    # Clean Output Area
    with gr.Row():
        logs = gr.TextArea(label="Terminal Cobalt", lines=8, interactive=False, show_copy_button=True)

    gr.Markdown("---")
    gr.Markdown("## 📂 Galeria")
    gallery = gr.Gallery(label="", columns=[4], rows=[2], object_fit="cover", height="auto", show_share_button=True)

    # Refresh gallery on load
    demo.load(scan_gallery, outputs=gallery)

    # Actions
    btn_run.click(start_processing, inputs=[url_input, model_drop, subs_check, cookies_input, oauth_input], outputs=[logs, gallery])
    btn_reset.click(delete_all, outputs=[reset_msg, gallery])

if __name__ == "__main__":
    # SHARE=TRUE creates the public link automatically!
    demo.launch(share=True, allowed_paths=["/content/drive"])
