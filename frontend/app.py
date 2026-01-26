import streamlit as st
import os
import sys
import time

# --- Setup Paths ---
# Add root directory to path to allow importing backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from backend import processing
except ImportError:
    st.error("❌ Erro: Backend não encontrado. Verifique a estrutura de pastas.")
    st.stop()

# --- Page Config ---
st.set_page_config(
    page_title="AI Video Clipper Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styling (Dark/Premium) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stTextInput > div > div > input {
        background-color: #262730;
        color: #ffffff;
        border: 1px solid #4b4b4b;
    }
    .stButton > button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #ff3333;
        transform: scale(1.02);
    }
    .status-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #262730;
        border: 1px solid #3d3d3d;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("---")

    st.subheader("🤖 Modelo de IA")
    model_choice = st.selectbox(
        "Selecione o Motor:",
        ["Vosk (Offline/Grátis)", "Whisper (Requer API/GPU)"],
        index=0,
        help="Vosk é o padrão para uso Grátis e Offline no Colab."
    )

    st.subheader("🌍 Idioma e Legendas")
    language = st.selectbox(
        "Idioma do Vídeo:",
        ["Português (BR)", "English (US)", "Español"],
        index=0
    )

    burn_subtitles = st.checkbox("🔥 Queimar Legendas no Vídeo", value=True)

    st.markdown("---")
    st.info("ℹ️ **Status:** Pronto para rodar no Google Colab.")
    st.markdown("---")
    st.caption("v3.0.0 - Viral Ultimate")
    st.caption("🔄 Para atualizar: Pare o App e rode a Célula 1 do Notebook novamente.")

# --- Main Interface ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("# 🎬")
with col_title:
    st.title("AI Video Clipper Studio")
    st.caption("Transforme vídeos longos em clipes virais com legendas automáticas - 100% Local.")

st.markdown("---")

# Input Area
video_url = st.text_input("🔗 URL do Vídeo (YouTube):", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 Processar e Criar Clip"):
    if not video_url:
        st.warning("⚠️ Por favor, cole uma URL válida do YouTube.")
    else:
        # Layout containers
        status_container = st.container()
        progress_bar = st.progress(0)

        final_video_path = None

        try:
            with status_container:
                st.markdown('<div class="status-box">', unsafe_allow_html=True)

                # Run the Generator
                settings = {
                    "model": model_choice,
                    "lang": language,
                    "burn_subtitles": burn_subtitles
                }

                # Consume the generator
                for result in processing.process_video(video_url, settings):
                    # Backend yields (Status Message, Progress Int) OR just the Final Path String
                    if isinstance(result, tuple):
                        status_text, progress_val = result
                        st.write(f"🔄 {status_text}")
                        progress_bar.progress(progress_val)
                    elif isinstance(result, str): # Final path return is getting complicated in generator, handled below
                        pass

                # Actually, my backend yields tuples correctly, but returns the path at the end.
                # Generators in Python return the value in StopIteration, but iterating over them doesn't give it easily.
                # Let's adjust logic: The backend yields (msg, prog) until the end, and the LAST yield checks for file or we check file system.

                # Re-checking backend logic: last yield is ("✅ Processamento Finalizado!", 100).
                # The function returns clip_output. In Python `return` in a generator stops iteration.
                # To get the return value we need to catch StopIteration or just rely on file existence known path.

                start_dir = "downloads" # predefined in backend
                expected_file = os.path.join(start_dir, "viral_clip_final.mp4")
                if not burn_subtitles:
                     # Fallback logic if needed, but for now backend tries to deliver final.
                     expected_file = os.path.join(start_dir, "subtitled_cut.mp4") # Or similar fallback

                st.markdown('</div>', unsafe_allow_html=True)

            # Success State
            if os.path.exists(expected_file):
                st.balloons()
                st.success("✅ **Processamento Concluído com Sucesso!**")

                col_res1, col_res2 = st.columns(2)

                with col_res1:
                    st.subheader("📺 Preview do Resultado")
                    st.video(expected_file)

                with col_res2:
                    st.subheader("⬇️ Baixar Clip")
                    with open(expected_file, "rb") as file:
                        btn = st.download_button(
                            label="📥 Download Video (.mp4)",
                            data=file,
                            file_name="viral_clip_ai.mp4",
                            mime="video/mp4"
                        )

                    st.markdown("---")
                    st.markdown("**Arquivos Gerados:**")
                    st.code(f"downloads/\n  ├── input_video.mp4\n  ├── input_audio.wav\n  ├── clip.srt\n  └── viral_clip.mp4")
            else:
                st.error("❌ O arquivo final não foi encontrado. Algo deu errado no processamento.")

        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado: {str(e)}")
