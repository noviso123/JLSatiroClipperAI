import os
import shutil
import subprocess
import sys

def run_command(command):
    """Run shell command and print output"""
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar: {command}")
        sys.exit(1)

def main():
    print("🚀 [Auto-Update] Iniciando Configuração do Ambiente...")

    # 1. System Dependencies (FFmpeg + Node for LocalTunnel)
    print("📦 [1/4] Atualizando Motores de Sistema (FFmpeg & Node)...")
    run_command("apt-get update -qq")
    run_command("apt-get install ffmpeg -y -qq")
    run_command("npm install -g localtunnel") # Install LocalTunnel globally

    # 2. Python Dependencies
    print("🐍 [2/4] Instalando Dependências Python (Bibliotecas)...")
    run_command("pip install -r requirements.txt -q")

    # 3. AI Model (Vosk)
    model_dir = "model"
    if not os.path.exists(model_dir):
        print("🧠 [3/4] Baixando Cérebro da IA (Vosk Small PT)...")
        # Download and unzip logic
        run_command("wget https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip -q")
        run_command("unzip -q vosk-model-small-pt-0.3.zip")
        run_command("mv vosk-model-small-pt-0.3 model")
        run_command("rm vosk-model-small-pt-0.3.zip")
    else:
        print("🧠 [3/4] Modelo IA já instalado.")

    print("✅ [4/4] Setup Completo! Sistema 100% Atualizado.")

if __name__ == "__main__":
    main()
