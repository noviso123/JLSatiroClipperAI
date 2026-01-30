# Suppress DeprecationWarnings from Gradio/TensorFlow
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import gradio as gr
import os
import time
import shutil
import sys
import threading

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import processing, state_manager, video_engine

# Global Work Vars
# Global Work Vars - Now dynamic via Zenith Logic
_W, _D = video_engine.setup_directories()
LOCAL_GALLERY = _D

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

def run_worker(url, video_file, settings):
    """Background worker thread"""
    state_manager.set_running(True)
    state_manager.update_state("progress", 0)

    source = url if url else "Arquivo Local"
    state_manager.append_log(f"💎 Iniciando Motor Cobalt V24.1...\n🚀 Fonte: {source}")

    try:
        # process_video is a generator, we must consume it
        for result in processing.process_video(
            url,
            video_file,
            hashtags=settings.get('hashtags', ''),
            layout_mode=settings.get('layout', 'Dinâmico (Auto-IA)'),
            publish_youtube=settings.get('publish_youtube', False)
        ):
            # Check stop inside the loop consumption too just in case
            if state_manager.check_stop_requested():
                break

            if isinstance(result, tuple) and len(result) == 2:
                status, pct = result
                state_manager.update_state("progress", pct)
                state_manager.append_log(status)
            elif isinstance(result, str):
                 state_manager.append_log(f"✅ CORTE PRONTO: {os.path.basename(result)}")

    except Exception as e:
        state_manager.append_log(f"❌ Erro Crítico: {str(e)}")
    finally:
        state_manager.append_log("🏁 Processamento Finalizado.")
        state_manager.set_running(False)

def start_processing(url, video_file, model_type, burn_subs, publish_youtube, hashtags, cookies_file, oauth_file, layout_mode):
    """Starts the background thread"""
    if not url and not video_file:
        return "⚠️ Erro: Forneça uma URL do YouTube OU um arquivo de vídeo."

    if state_manager.get_state()['is_running']:
        return "⚠️ Já existe um processo em andamento! Aguarde ou limpe o sistema."

    # Settings
    settings = {
        "model": model_type,
        "lang": "Português (BR)",
        "burn_subtitles": burn_subs,
        "publish_youtube": publish_youtube,
        "hashtags": hashtags,
        "layout": layout_mode,
        "cookies_path": cookies_file.name if cookies_file else None,
        "oauth_path": oauth_file.name if oauth_file else None
    }

    t = threading.Thread(target=run_worker, args=(url, video_file, settings))
    t.start()
    return "✅ Processamento Iniciado em Segundo Plano!"

def poll_system():
    """Robust poller for UI updates with Heartbeat detection"""
    try:
        s = state_manager.get_state()
        log = s.get('log_history', '')
        run_status = s.get('is_running', False)
        pct = s.get('progress', 0)
        hb = s.get('heartbeat', 0)

        # Heartbeat visual logic
        is_alive = (time.time() - hb) < 5
        heart_icon = "🔥" if (int(time.time()) % 2 == 0 and is_alive) else "💎"

        status_text = f"Status: {'🟢 RODANDO' if run_status else '⚪ AGUARDANDO'} {heart_icon} | Progresso: {pct}%"
        if run_status and not is_alive:
            status_text = f"Status: ⏳ PROCESSANDO PESADO... {heart_icon} | Progresso: {pct}%"

        return log, scan_gallery(), status_text
    except Exception as e:
        return f"⚠️ Erro de Polling: {e}", [], "⚠️ Erro de Conexão Local"

def nuke_system():
    """Deep Nuke - Global Output Purge"""
    state_manager.request_stop()
    state_manager.append_log("🛑 PURGA GLOBAL ATÔMICA INICIADA...")

    # Give threads time to stop
    time.sleep(1.5)

    try:
        # Directories to purge
        w_dir, d_dir = video_engine.setup_directories()
        dirs_to_clean = [w_dir, d_dir, "output_clips", "production_output"]

        for d in dirs_to_clean:
            if os.path.exists(d):
                state_manager.append_log(f"🧹 Limpando: {d}...")
                for f in os.listdir(d):
                    fp = os.path.join(d, f)
                    try:
                        if os.path.isfile(fp): os.unlink(fp)
                        elif os.path.isdir(fp): shutil.rmtree(fp)
                    except: pass

        state_manager.clear_state()
        state_manager.clear_logs()
        state_manager.append_log("♻️ SISTEMA PURGADO COM SUCESSO. ESTADO ZERO-DAY.")
        return "♻️ Cache e Produções Limpos!", [], "Status: ⚪ Resetado"
    except Exception as e:
        return f"Erro na Purga: {e}", [], f"Erro: {e}"

# --- INTERFACE ---
try:
    cobalt_theme = gr.themes.Ocean(
        primary_hue="indigo",
        secondary_hue="zinc",
        neutral_hue="slate",
        text_size="lg",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"]
    )
except:
    cobalt_theme = gr.themes.Default()

with gr.Blocks(title="JLSatiro Clipper AI - V24.1 (TITANIUM)", theme=cobalt_theme) as demo:
    with gr.Column(elem_id="main_container", variant="panel"):
        gr.Markdown(
            """
            # 🚀 JLSatiro Clipper AI - V24.1
            ### *Dynamic Vision. Stability Engine. Deep Purge.*
            """
        )

        with gr.Row():
            with gr.Column(scale=3):
                with gr.Group():
                    gr.Markdown("### 📥 Entradas")
                    url_input = gr.Textbox(label="URL YouTube", placeholder="Cole o link aqui...", lines=1)
                    file_input = gr.File(label="Arquivo Local (MP4)", file_types=[".mp4"], file_count="single")

            with gr.Column(scale=2):
                with gr.Group():
                    gr.Markdown("### ⚙️ Configurações")
                    layout_mode_radio = gr.Radio(
                        ["Dinâmico (Auto-IA)", "Reação (Rosto/Base)", "Smart Focus", "Split-Screen (Podcast)", "Modo Gamer"],
                        label="Estilo de Enquadramento",
                        value="Dinâmico (Auto-IA)"
                    )
                    model_drop = gr.Dropdown(["Whisper V3 (Local)"], value="Whisper V3 (Local)", label="Motor Transcrição", interactive=False)

                    with gr.Row():
                        subs_check = gr.Checkbox(label="Legendas Montserrat", value=True)
                        youtube_check = gr.Checkbox(label="Postar no Shorts", value=False)

        with gr.Group():
            gr.Markdown("### 🏷️ SEO")
            hashtags_input = gr.Textbox(label="Hashtags", value="#Shorts #Viral")

        with gr.Row():
            btn_run = gr.Button("🚀 INICIAR PROCESSAMENTO", variant="primary", scale=3)
            btn_clear_logs = gr.Button("🧹 LIMPAR LOGS", variant="secondary", scale=1)
            btn_reset = gr.Button("🗑️ RESET TOTAL", variant="stop", scale=1)

        status_info = gr.Markdown("### **Status: ⚪ Aguardando...**")
        reset_msg = gr.Textbox(visible=False)

        with gr.Row():
            with gr.Column(scale=1):
                logs = gr.TextArea(label="Terminal Cobalt", lines=12, interactive=False)
            with gr.Column(scale=1):
                 gr.Markdown("### 📂 Galeria")
                 gallery = gr.Gallery(label="", columns=[2], rows=[2], object_fit="cover", height="400px")

    # --- Polling ---
    if hasattr(gr, "Timer"):
        timer = gr.Timer(1)
        timer.tick(poll_system, inputs=None, outputs=[logs, gallery, status_info])
    else:
        demo.load(poll_system, inputs=None, outputs=[logs, gallery, status_info], every=1)

    # --- Actions ---
    btn_run.click(start_processing, inputs=[url_input, file_input, model_drop, subs_check, youtube_check, hashtags_input, gr.State(None), gr.State(None), layout_mode_radio], outputs=[reset_msg])
    btn_reset.click(nuke_system, outputs=[reset_msg, gallery, status_info])
    btn_clear_logs.click(lambda: (state_manager.clear_logs(), ""), outputs=[logs, reset_msg])

if __name__ == "__main__":
    demo.launch(share=False)
