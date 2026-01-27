import os
import subprocess
import sys

# Model Config
MODEL_URL = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_PATH = "model.gguf"

def is_colab():
    try:
        import google.colab
        return True
    except ImportError:
        return False

def setup_neural_env():
    """
    Installs Llama-cpp-python with CUDA support and downloads the model.
    Only runs if explicitly requested or if on Colab.
    """
    if not is_colab() and not os.path.exists("/dev/shm"):
        print("💻 Ambiente Local Detectado. Pulando setup Neural (GPU requerida).")
        return False

    print("🚀 Iniciando Setup NEURAL ENGINE (V20.0)...")

    # 1. Install Llama-cpp (CUDA)
    try:
        import llama_cpp
        print("✅ Llama-cpp já instalado.")
    except ImportError:
        print("⚡ Compilando Llama-cpp com suporte a CUDA (T4)...")
        # Force reinstall with CUDA flags
        cmd = 'CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir'
        subprocess.run(cmd, shell=True)
        subprocess.run('pip install instructor mediapipe opencv-python-headless', shell=True)

    # 2. Download Model
    if not os.path.exists(MODEL_PATH):
        print(f"📥 Baixando Modelo Neural ({MODEL_URL})...")
        # Use wget via subprocess
        subprocess.run(f"wget {MODEL_URL} -O {MODEL_PATH}", shell=True)

    if os.path.exists(MODEL_PATH):
        print("✅ Modelo Neural Pronto!")
        return True
    else:
        print("❌ Falha ao baixar modelo.")
        return False

if __name__ == "__main__":
    setup_neural_env()
