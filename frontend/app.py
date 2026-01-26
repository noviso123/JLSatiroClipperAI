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
    if os.path.exists(drive_path):
        st.success("✅ Google Drive Detectado")
        save_to_drive = st.checkbox("Salvar Cópia no Drive", value=True)
    else:
        st.warning("⚠️ Drive Não Conectado")

    st.markdown("---")
    st.caption("v3.6.0 - Factory Mode")
    st.caption("🔄 Para atualizar: Reinicie Célula 1 do Notebook.")

# --- Main Interface ---
col_logo, col_title = st.columns([1, 5])
with col_logo: st.markdown("# 🏭")
with col_title:
    st.title("Fábrica de Cortes Virais IA")
    st.caption("Gera 10+ Cortes Automáticos por vídeo • 100% Autônomo")

st.markdown("---")

video_url = st.text_input("🔗 URL do Vídeo (YouTube):", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 Iniciar Fábrica de Cortes"):
    if not video_url:
        st.warning("⚠️ Insira uma URL válida.")
    else:
        status_container = st.container()
        progress_bar = st.progress(0)
        results_area = st.container()

        try:
            with status_container:
                st.markdown('<div class="status-box">', unsafe_allow_html=True)
                settings = {"model": model_choice, "lang": language, "burn_subtitles": burn_subtitles}

                # Logic for Multi-Clip Handling
                clip_count = 0

                for result in processing.process_video(video_url, settings):
                    if isinstance(result, tuple):
                        status_text, progress_val = result
                        st.write(f"🔄 {status_text}")
                        progress_bar.progress(progress_val)

                    elif isinstance(result, str): # Found a FILE PATH (Finished Clip)
                        file_path = result
                        clip_count += 1

                        # --- Drive Logic ---
                        drive_msg = ""
                        if save_to_drive:
                            try:
                                folder_name = "Cortes_IA_Studio"
                                dest_folder = os.path.join(drive_path, folder_name)
                                os.makedirs(dest_folder, exist_ok=True)
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = os.path.basename(file_path).replace(".mp4", f"_{timestamp}.mp4")
                                dest_path = os.path.join(dest_folder, filename)
                                shutil.copy2(file_path, dest_path)
                                drive_msg = f"☁️ Salvo no Drive: {filename}"
                            except Exception as e:
                                drive_msg = f"⚠️ Erro Drive: {e}"

                        # --- Display Result (Streamed) ---
                        with results_area:
                            st.markdown(f'<div class="clip-box">', unsafe_allow_html=True)
                            st.subheader(f"🎬 Corte #{clip_count}")
                            if drive_msg: st.caption(drive_msg)

                            c1, c2 = st.columns([2, 1])
                            with c1: st.video(file_path)
                            with c2:
                                with open(file_path, "rb") as f:
                                    st.download_button(
                                        f"📥 Baixar Corte #{clip_count}",
                                        f,
                                        os.path.basename(file_path),
                                        "video/mp4",
                                        key=f"dl_{clip_count}_{file_path}"
                                    )
                            st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            if clip_count > 0:
                st.balloons()
                st.success(f"✅ **Fábrica Finalizada! {clip_count} Cortes Gerados.**")
            else:
                st.error("❌ Nenhum corte foi gerado. Verifique o vídeo.")

        except Exception as e:
            st.error(f"❌ Erro Crítico: {str(e)}")
