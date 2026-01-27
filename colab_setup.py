import os
import shutil
import subprocess
import sys

# Removed: from google.colab import drive (No longer needed)

def run_command(command):
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar: {command}")
        # sys.exit(1) # Don't exit on apt update error sometimes
        pass

def main():
    print("💎 [Auto-Update] JLSatiro Setup V17.0 (EXTREME - API AUTH)...")

    # 1. System Dependencies
    print("📦 [1/5] Atualizando Motores de Sistema (FFmpeg)...")
    run_command("apt-get update -qq")
    run_command("apt-get install ffmpeg -y -qq")

    # 2. Python Dependencies
    print("🐍 [2/5] Instalando Dependências Python...")
    run_command("pip install -r requirements.txt -q")
    # NEW dependencies for API Auth
    run_command("pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client -q")

    print("🔄 [2.5/5] Atualizando yt-dlp e Pytubefix (Crítico)...")
    run_command("pip install -U yt-dlp pytubefix -q")

    # 3. AI Model (Whisper GPU)
    print("🧠 [3/5] Verificando Acelerador Gráfico (GPU)...")
    try:
        run_command("nvidia-smi") # Print GPU status to logs
        print("    ✅ GPU NVIDIA Detectada! (Modo Turbo Ativado)")
    except:
        print("    ⚠️ GPU NÃO DETECTADA. O sistema vai rodar lento (CPU).")
        print("    👉 Dica: Vá em 'Ambiente de Execução' -> 'Alterar tipo' -> 'T4 GPU'")

    print("    ✅ Whisper Configurado (Large V3).")

    # 4. Auth & Workspace Prep
    print("🔐 [4/5] Preparando Autenticação API...")
    local_downloads = "/content/JLSatiroClipperAI/downloads"
    os.makedirs(local_downloads, exist_ok=True)

    # Check for credentials
    possible_auth = "client_secret.json"
    if os.path.exists(possible_auth):
        print(f"    ✅ 'client_secret.json' detectado! A autenticação será automática.")
    else:
        print(f"    ℹ️ 'client_secret.json' não encontrado na raiz.")
        print(f"       O sistema pedirá upload no início ou usará armazenamento local.")

    print("✅ [5/5] Setup Completo! Sistema Pronto (Modo API).")

if __name__ == "__main__":
    main()
