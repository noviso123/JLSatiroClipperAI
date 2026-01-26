import streamlit as st
import os
import sys
import shutil
from datetime import datetime

# --- Setup Paths ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from backend import processing
except ImportError:
    st.error("❌ Erro: Backend não encontrado.")
    st.stop()

# --- Page Config ---
st.set_page_config(page_title="AI Video Clipper Studio", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")

# --- Custom Styling ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTextInput > div > div > input { background-color: #262730; color: #ffffff; border: 1px solid #4b4b4b; }
    .stButton > button { background-color: #FF4B4B; color: white; border-radius: 8px; font-weight: bold; width: 100%; transition: all 0.3s; }
    .stButton > button:hover { background-color: #ff3333; transform: scale(1.02); }
    .status-box { padding: 1rem; border-radius: 8px; background-color: #262730; border: 1px solid #3d3d3d; margin-bottom: 1rem; }
    .clip-box { background-color: #1e1e1e; padding: 10px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("---")

    st.subheader("🤖 Modelo de IA")
    model_choice = st.selectbox("Selecione o Motor:", ["Vosk (Offline/Grátis)", "Whisper (Requer API/GPU)"], index=0)

    st.subheader("🌍 Idioma e Legendas")
    st.info("🔒 Travado em Português (BR)")
    language = "Português (BR)"
    burn_subtitles = st.checkbox("🔥 Queimar Legendas no Vídeo", value=True)

    st.markdown("---")
    st.subheader("☁️ Armazenamento")

    drive_path = "/content/drive/MyDrive"
    save_to_drive = False

    # Check symlink or drive mount
    if os.path.exists(drive_path):
        st.success("✅ Google Drive Detectado")
        save_to_drive = True # Force True as we are symlinked now
    else:
        st.warning("⚠️ Drive Não Conectado")

    st.markdown("---")
    st.caption("v4.2.0 - Cloud Gallery")
    if st.button("🔄 Checar Atualizações do Sistema"):
        try:
            os.system("git pull origin main")
            st.success("Sistema Atualizado! Recarregue a página.")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

# --- Helper: Gallery ---
def load_gallery():
    """Scans the output folder for existing clips"""
    gallery_path = "downloads"
    clips = []
    if os.path.exists(gallery_path):
        # Look for 'viral_clip_' files which are the final outputs
        for f in os.listdir(gallery_path):
            if f.startswith("viral_clip_") and f.endswith(".mp4"):
                clips.append(os.path.join(gallery_path, f))

    # Sort by modification time (newest first)
    clips.sort(key=os.path.getmtime, reverse=True)
    return clips

# --- Main Interface ---
col_logo, col_title = st.columns([1, 5])
with col_logo: st.markdown("# 🏭")
with col_title:
    st.title("Fábrica de Cortes Virais IA")
    st.caption("Gera 10+ Cortes Automáticos por vídeo • 100% Autônomo • Salvo no Drive")

# 1. New Processing Section
st.markdown("### 🆕 Novo Processamento")
video_url = st.text_input("🔗 URL do Vídeo (YouTube):", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 Iniciar Fábrica de Cortes"):
    if not video_url:
        st.warning("⚠️ Insira uma URL válida.")
    else:
        st.error("⚠️ **NÃO RECARREGUE A PÁGINA** enquanto o processamento estiver rodando! (Você perderá o progresso visual)")

        status_container = st.status("🏗️ Iniciando Processos...", expanded=True)
        progress_bar = status_container.progress(0)

        clip_count = 0

        try:
            settings = {"model": model_choice, "lang": language, "burn_subtitles": burn_subtitles}

            for result in processing.process_video(video_url, settings):
                if isinstance(result, tuple):
                    status_text, progress_val = result
                    status_container.write(f"⚙️ {status_text}")
                    progress_bar.progress(progress_val)

                elif isinstance(result, str): # Found a FILE PATH (Finished Clip)
                    file_path = result
                    clip_count += 1
                    status_container.write(f"✅ **Corte #{clip_count} Finalizado!**")
                    # It's already in Drive/Downloads thanks to symlink logic
                    st.toast(f"Corte #{clip_count} Salvo no Drive!", icon="💾")

            if clip_count > 0:
                status_container.update(label="✅ Processamento Concluído!", state="complete", expanded=False)
                st.balloons()
                st.success(f"**Sucesso! {clip_count} Cortes Gerados.** Veja abaixo na Galeria.")
                time.sleep(2)
                st.rerun() # Refresh to show in gallery
            else:
                status_container.update(label="❌ Falha", state="error")
                st.error("Nenhum corte foi gerado.")

        except Exception as e:
            status_container.update(label="❌ Erro Crítico", state="error")
            st.error(f"Erro: {str(e)}")

st.markdown("---")

# 2. Persistent Gallery Section
st.markdown("### 📂 Galeria (Seu Drive)")
st.caption("Arquivos salvos em: 'Meu Drive > JLSatiro_AI_Studio'")

existing_clips = load_gallery()

if not existing_clips:
    st.info("Nenhum corte encontrado na pasta. Gere o primeiro acima! 👆")
else:
    for f_path in existing_clips:
        with st.expander(f"🎬 {os.path.basename(f_path)}", expanded=False):
            c1, c2 = st.columns([3, 1])
            with c1: st.video(f_path)
            with c2:
                try:
                    with open(f_path, "rb") as f:
                        st.download_button(
                            "📥 Baixar Arquivo",
                            f,
                            os.path.basename(f_path),
                            "video/mp4",
                            key=f_path
                        )
                except: st.error("Arquivo indisponível")
