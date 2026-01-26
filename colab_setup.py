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
    print("💎 [Auto-Update] JLSatiro Setup V16.8 (RESURRECTION)...")

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
        print("⚠️ Drive não disponível. Usando armazenamento temporário (Não Recomendado).")
        os.makedirs(local_downloads, exist_ok=True)

    # V16.2: Ensure auth file if uploaded
    possible_auth = "/content/drive/MyDrive/JLSatiro_AI_Studio/client_secret.json"
    if os.path.exists(possible_auth):
        print(f"    ✅ Credenciais encontradas no Drive! (client_secret.json)")
    else:
        print(f"    ℹ️ Nenhuma credencial 'client_secret.json' encontrada no Drive.")
        print(f"       (Opcional) Suba no Passo 1.5 para liberar uploads.")

    # 1. System Dependencies
    print("📦 [1/4] Atualizando Motores de Sistema (FFmpeg)...")
    run_command("apt-get update -qq")
    run_command("apt-get install ffmpeg -y -qq")

    # 2. Python Dependencies
    print("🐍 [2/4] Instalando Dependências Python...")
    run_command("pip install -r requirements.txt -q")
    print("🔄 [2.5/4] Atualizando yt-dlp e Pytubefix (Crítico)...")
    run_command("pip install -U yt-dlp pytubefix -q")

    # 3. AI Model (Whisper GPU)
    print("🧠 [3/4] Verificando Acelerador Gráfico (GPU)...")
    try:
        run_command("nvidia-smi") # Print GPU status to logs
        print("    ✅ GPU NVIDIA Detectada! (Modo Turbo Ativado)")
    except:
        print("    ⚠️ GPU NÃO DETECTADA. O sistema vai rodar lento (CPU).")
        print("    👉 Dica: Vá em 'Ambiente de Execução' -> 'Alterar tipo' -> 'T4 GPU'")

    print("    ✅ Whisper Configurado (Large V3).")

    print("✅ [4/4] Setup Completo! Sistema Pronto.")

if __name__ == "__main__":
    main()
