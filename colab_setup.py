import os
import shutil
import subprocess
import sys
from google.colab import drive

def run_command(command):
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar: {command}")
        # sys.exit(1) # Don't exit on apt update error sometimes
        pass

def main():
    print("💎 [Auto-Update] JLSatiro Setup V15.3 (SAFE MODE)...")

    # 0. DRIVE DEEP INTEGRATION
    print("☁️ [0/4] Conectando Google Drive (Modo Produção)...")
    if not os.path.exists('/content/drive'):
        try:
            drive.mount('/content/drive')
        except:
            print("⚠️ Aviso: Drive não montado (Rodando Local?).")

    # Setup Workspace on Drive
    drive_workspace = "/content/drive/MyDrive/JLSatiro_AI_Studio"
    local_downloads = "/content/JLSatiroClipperAI/downloads"

    if os.path.exists('/content/drive'):
        print(f"📂 Criando Workspace no Drive: {drive_workspace}")
        os.makedirs(drive_workspace, exist_ok=True)

        # Symlink Logic
        if os.path.exists(local_downloads):
            if os.path.islink(local_downloads):
                os.remove(local_downloads) # Remove old link
            else:
                shutil.rmtree(local_downloads) # Remove local dir

        print("🔗 Criando Ponte (Symlink) para o Drive...")
        os.symlink(drive_workspace, local_downloads)
        print("✅ Ponte Criada! Arquivos serão salvos direto na Nuvem.")
    else:
        print("⚠️ Drive não disponível. Usando armazenamento temporário.")
        os.makedirs(local_downloads, exist_ok=True)

    # 1. System Dependencies
    print("📦 [1/4] Atualizando Motores de Sistema (FFmpeg)...")
    run_command("apt-get update -qq")
    run_command("apt-get install ffmpeg -y -qq")

    # 2. Python Dependencies
    print("🐍 [2/4] Instalando Dependências Python...")
    run_command("pip install -r requirements.txt -q")
    print("🔄 [2.5/4] Atualizando yt-dlp e Pytubefix (Crítico)...")
    run_command("pip install -U yt-dlp pytubefix -q")

    # 3. AI Model (Vosk Smart Download)
    model_dir = "model"
    if not os.path.exists(model_dir):
        print("🧠 [3/4] Baixando Cérebro da IA...")

        # TENTATIVA 1: LARGE MODEL (1.5GB)
        print("    ↳ Tentando Modelo LARGE (1.5GB) para máxima qualidade...")
        try:
            # Remove -q to let user see progress
            run_command("wget https://alphacephei.com/vosk/models/vosk-model-pt-0.3.zip")
            run_command("unzip -q vosk-model-pt-0.3.zip")
            run_command("mv vosk-model-pt-0.3 model")
            run_command("rm vosk-model-pt-0.3.zip")
            print("    ✅ Modelo LARGE Instalado com Sucesso!")
        except:
            print("    ❌ Falha no download do Modelo Large. (Server pode estar lento)")
            print("    ⚠️ Ativando FALLBACK para Modelo Small (50MB)...")

            # TENTATIVA 2: SMALL MODEL (Fallback)
            if os.path.exists("vosk-model-pt-0.3.zip"): os.remove("vosk-model-pt-0.3.zip") # Cleanup partial

            try:
                run_command("wget https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip")
                run_command("unzip -q vosk-model-small-pt-0.3.zip")
                run_command("mv vosk-model-small-pt-0.3 model")
                run_command("rm vosk-model-small-pt-0.3.zip")
                print("    ✅ Modelo SMALL Instalado com Sucesso! (Sistema Operacional)")
            except Exception as e:
                print(f"    ❌ ERRO CRÍTICO: Nenhum modelo pôde ser baixado. {e}")
    else:
        print("🧠 [3/4] Modelo IA já instalado.")

    print("✅ [4/4] Setup Completo! Sistema Pronto.")

if __name__ == "__main__":
    main()
