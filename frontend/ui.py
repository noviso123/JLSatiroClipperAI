import gradio as gr
import os
import time
import shutil
import sys
import threading

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import processing, state_manager

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

def run_worker(url, video_file, settings):
    """Background worker thread"""
    state_manager.set_running(True)
    state_manager.update_state("progress", 0)

    source = url if url else "Arquivo Local"
    state_manager.append_log(f"💎 Iniciando Motor Cobalt V13.3...\n🚀 Fonte: {source}")

    try:
        # process_video is a generator, we must consume it
        for result in processing.process_video(url, video_file, settings):
            # Check stop inside the loop consumption too just in case
            if state_manager.check_stop_requested():
                break

            if isinstance(result, str):
                 state_manager.append_log(f"✅ CORTE PRONTO: {os.path.basename(result)}")

    except Exception as e:
        state_manager.append_log(f"❌ Erro Crítico: {str(e)}")
    finally:
        state_manager.append_log("🏁 Processamento Finalizado.")
        state_manager.set_running(False)

def start_processing(url, video_file, model_type, burn_subs, publish_youtube, hashtags, cookies_file, oauth_file):
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
        "cookies_path": cookies_file.name if cookies_file else None,
        "oauth_path": oauth_file.name if oauth_file else None
    }

    t = threading.Thread(target=run_worker, args=(url, video_file, settings))
    t.start()
    return "✅ Processamento Iniciado em Segundo Plano!"

def poll_system():
    """Poller for UI updates"""
    s = state_manager.get_state()
    log = s.get('log_history', '')
    run_status = s.get('is_running', False)
    pct = s.get('progress', 0)

    status_text = f"Status: {'🟢 RODANDO' if run_status else '⚪ AGUARDANDO'} | Progresso Global: {pct}%"

    return log, scan_gallery(), status_text

def nuke_system():
    """Factory Reset - Clear All"""
    state_manager.request_stop()
    state_manager.append_log("🛑 INTERROMPENDO TUDO E LIMPANDO...")

    # Wait briefly for thread to notice stop
    time.sleep(1.5)

    try:
        shutil.rmtree("/content/temp_work", ignore_errors=True)
        if os.path.exists(LOCAL_GALLERY):
             for f in os.listdir(LOCAL_GALLERY):
                 fp = os.path.join(LOCAL_GALLERY, f)
                 if os.path.isfile(fp): os.unlink(fp)

        state_manager.clear_state()
        state_manager.append_log("♻️ SISTEMA FORMATADO COM SUCESSO.")
        return "♻️ Login/Cache/Arquivos Limpos!", scan_gallery(), "Status: ⚪ Resetado"
    except Exception as e:
        return f"Erro ao limpar: {e}", scan_gallery(), f"Erro: {e}"

# --- INTERFACE (V13.3 COBALT DESIGN) ---
cobalt_theme = gr.themes.Ocean(
    primary_hue="indigo",
    secondary_hue="zinc",
    neutral_hue="slate",
    text_size="lg",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"]
)

with gr.Blocks(title="JLSatiro Clipper AI - V17.0 (EXTREME AGENT)", theme=cobalt_theme) as demo:
    with gr.Column(elem_id="main_container", variant="panel"):
        gr.Markdown(
            """
            # 🚀 JLSatiro Clipper AI - V17.0 (EXTREME AGENT)
            ### *RamDisk Engine. NVENC P2. Smart Blur. Max Performance.*
            """
        )

        with gr.Group():
            with gr.Row():
                url_input = gr.Textbox(
                    label="URL do YouTube",
                    placeholder="Cole o link do YouTube aqui...",
                    show_label=True,
                    scale=3,
                    lines=1
                )
                file_input = gr.File(
                    label="OU Carregue um Vídeo (MP4)",
                    file_types=[".mp4"],
                    file_count="single",
                    scale=2
                )

            with gr.Row():
                model_drop = gr.Dropdown(["Hyper-Whisper V3 (GPU)"], value="Hyper-Whisper V3 (GPU)", interactive=False, show_label=False, container=False, scale=1)
                subs_check = gr.Checkbox(label="Legendas", value=True, container=False, scale=0)
                youtube_check = gr.Checkbox(label="Publicar YouTube (Shorts)", value=False, container=False, scale=0)
                btn_run = gr.Button("BAIXAR/CARREGAR & CORTAR (EXTREME MODE)", variant="primary", scale=1)

            with gr.Row():
                hashtags_input = gr.Textbox(
                    label="Hashtags Obrigatórias (Opcional - Sistema completará se houver espaço)",
                    value="#Shorts #Viral",
                    placeholder="#SeuNicho #SuaMarca (Deixe vazio para automático)",
                    scale=4
                )

        # Status Display
        status_info = gr.Markdown("**Status: ⚪ Pronto para Decolar**")

        with gr.Accordion("⚙️ Configurações Avançadas / Autenticação", open=False):
             gr.Markdown("### 🔐 Credenciais & Controle")
             cookies_input = gr.File(label="Cookies (cookies.txt)", file_types=[".txt"])
             oauth_input = gr.File(label="Client Secret (json)", file_types=[".json"])

             # The Requested "Kill All" Button
             btn_reset = gr.Button("🗑️ EXCLUIR TUDO (CACHE, PROCESSOS, ARQUIVOS)", variant="stop", size="sm")
             reset_msg = gr.Textbox(interactive=False, show_label=False)

    with gr.Row():
        logs = gr.TextArea(label="Terminal Cobalt (Histórico Persistente)", lines=12, interactive=False, show_copy_button=True)

    gr.Markdown("---")
    gr.Markdown("## 📂 Galeria")
    gallery = gr.Gallery(label="", columns=[4], rows=[2], object_fit="cover", height="auto", show_share_button=True)

    # Poll system state every 1 second - This enables PERSISTENCE on reload

    # Initial Load
    demo.load(poll_system, inputs=None, outputs=[logs, gallery, status_info])

    # Polling with Timer (Modern Gradio approach)
    timer = gr.Timer(1)
    timer.tick(poll_system, inputs=None, outputs=[logs, gallery, status_info])

    # Actions
    btn_run.click(
        start_processing,
        inputs=[url_input, file_input, model_drop, subs_check, youtube_check, hashtags_input, cookies_input, oauth_input],
        outputs=[reset_msg] # Output to small msg box, monitoring happens via poll
    )

    # Handle File Upload for Client Secret immediately
    def update_secret(file):
        if file:
            shutil.copy(file.name, "client_secret.json")
            from backend.processing import init_google_services
            init_google_services()
            return "✅ Credencial Atualizada!"

    oauth_input.upload(update_secret, inputs=oauth_input, outputs=reset_msg)

    btn_reset.click(
        nuke_system,
        outputs=[reset_msg, gallery, status_info]
    )

if __name__ == "__main__":
    demo.launch(share=True, allowed_paths=["/content/drive"])
