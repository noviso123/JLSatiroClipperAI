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
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("---")

    st.subheader("🤖 Modelo de IA")
    model_choice = st.selectbox("Selecione o Motor:", ["Vosk (Offline/Grátis)", "Whisper (Requer API/GPU)"], index=0)

    st.subheader("🌍 Idioma e Legendas")
    language = st.selectbox("Idioma do Vídeo:", ["Português (BR)", "English (US)", "Español"], index=0)
    burn_subtitles = st.checkbox("🔥 Queimar Legendas no Vídeo", value=True)

    st.markdown("---")
    st.subheader("☁️ Armazenamento")

    # Auto-Drive Detection
    drive_path = "/content/drive/MyDrive"
    save_to_drive = False
    if os.path.exists(drive_path):
        st.success("✅ Google Drive Detectado")
        save_to_drive = st.checkbox("Salvar Cópia no Drive", value=True)
    else:
        st.warning("⚠️ Drive Não Conectado")

    st.markdown("---")
    st.caption("v3.2.0 - Drive Edition")
    st.caption("🔄 Para atualizar: Reinicie Célula 1 do Notebook.")

# --- Main Interface ---
col_logo, col_title = st.columns([1, 5])
with col_logo: st.markdown("# 🎬")
with col_title:
    st.title("AI Video Clipper Studio")
    st.caption("Cortes Virais Automáticos + Backup na Nuvem ☁️")

st.markdown("---")

# Input
video_url = st.text_input("🔗 URL do Vídeo (YouTube):", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 Processar e Criar Clip"):
    if not video_url:
        st.warning("⚠️ Insira uma URL válida.")
    else:
        status_container = st.container()
        progress_bar = st.progress(0)

        try:
            with status_container:
                st.markdown('<div class="status-box">', unsafe_allow_html=True)
                settings = {"model": model_choice, "lang": language, "burn_subtitles": burn_subtitles}

                final_file = None
                for result in processing.process_video(video_url, settings):
                    if isinstance(result, tuple):
                        status_text, progress_val = result
                        st.write(f"🔄 {status_text}")
                        progress_bar.progress(progress_val)

                # Check for output
                start_dir = "downloads"
                expected_file = os.path.join(start_dir, "viral_clip_final.mp4")
                if not burn_subtitles: expected_file = os.path.join(start_dir, "subtitled_cut.mp4")

                st.markdown('</div>', unsafe_allow_html=True)

            if os.path.exists(expected_file):
                st.balloons()
                st.success("✅ **Processamento Concluído!**")

                # --- Drive Backup Logic ---
                if save_to_drive:
                    try:
                        folder_name = "Cortes_IA_Studio"
                        dest_folder = os.path.join(drive_path, folder_name)
                        os.makedirs(dest_folder, exist_ok=True)

                        # Generate unique name
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest_path = os.path.join(dest_folder, f"clip_{timestamp}.mp4")
                        shutil.copy2(expected_file, dest_path)
                        st.success(f"📂 Salvo no Drive: `MyDrive/{folder_name}/clip_{timestamp}.mp4`")
                    except Exception as e:
                        st.error(f"⚠️ Erro ao salvar no Drive: {e}")

                col1, col2 = st.columns(2)
                with col1: st.video(expected_file)
                with col2:
                    with open(expected_file, "rb") as f:
                        st.download_button("📥 Download Local (.mp4)", f, "viral_clip.mp4", "video/mp4")
            else:
                st.error("❌ Arquivo final não encontrado.")

        except Exception as e:
            st.error(f"❌ Erro Crítico: {str(e)}")
