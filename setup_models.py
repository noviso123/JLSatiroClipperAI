import os
import sys

# Bypass SSL (Titanium Protocol)
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except: pass

from faster_whisper import WhisperModel
import shutil
import requests # Added for Haarcascade download

def download_all():
    # 1. WHISPER
    whisper_dir = os.path.join(os.getcwd(), "models", "whisper-tiny")
    if not os.path.exists(whisper_dir):
        print("📦 Provisionando Whisper Tiny...")
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id="Systran/faster-whisper-tiny", local_dir=whisper_dir, local_dir_use_symlinks=False)
        except Exception as e: print(f"⚠️ Erro Whisper: {e}")
    else: print("✅ Whisper já presente.")

    # 2. LLAMA GGUF (Neural Engine)
    llama_dir = os.path.join(os.getcwd(), "models", "llama")
    os.makedirs(llama_dir, exist_ok=True)
    model_path = os.path.join(llama_dir, "model.gguf")
    if not os.path.exists(model_path):
        print("📦 Provisionando Llama-3.2-3B-GGUF (Processamento de Metadados)...")
        # Direct URL to the Q4_K_M model on Hugging Face
        url = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
        try:
            r = requests.get(url, stream=True, verify=False)
            total_size = int(r.headers.get('content-length', 0))
            block_size = 1024 * 1024 # 1MB

            with open(model_path, 'wb') as f:
                downloaded = 0
                for data in r.iter_content(block_size):
                    f.write(data)
                    downloaded += len(data)
                    done = int(50 * downloaded / total_size)
                    sys.stdout.write(f"\r🚀 Download: [{'=' * done}{' ' * (50-done)}] {downloaded//(1024*1024)}MB / {total_size//(1024*1024)}MB")
                    sys.stdout.flush()
            print("\n✅ Llama GGUF Provisionado!")
        except Exception as e: print(f"\n⚠️ Erro Llama: {e}")
    else: print("✅ Llama já presente.")

    # 3. HAARCASCADE (OpenCV)
    hc_path = "haarcascade_frontalface_default.xml"
    if not os.path.exists(hc_path):
        print("📦 Provisionando Haarcascade (OpenCV Face Detection)...")
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        try:
            r = requests.get(url, verify=False)
            with open(hc_path, 'wb') as f: f.write(r.content)
            print("✅ Haarcascade Provisionado!")
        except Exception as e: print(f"⚠️ Erro Haarcascade: {e}")
    else: print("✅ Haarcascade já presente.")

if __name__ == "__main__":
    download_all()
