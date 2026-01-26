import subprocess
import time
import os
import sys
from pyngrok import ngrok

def run_command(command, background=False):
    if background:
        return subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        return subprocess.run(command, shell=True, check=True)

def main():
    print("🚀 [Launcher] Iniciando Aplicação V4.0 (Ngrok Edition)...")

    # 0. Auth Ngrok
    NGROK_TOKEN = "2tvNFAWzP9KMYZGpfCqx1EQmmwN_NPCQKjeqHD7pomCtJFVA"

    # -1. FORCE UPDATE (Redundancy)
    print("🔄 [Launcher] Verificando Atualizações...")
    try:
        run_command("git pull origin main")
    except Exception as e:
        print(f"⚠️ Aviso: Falha ao atualizar git ({e}). Seguindo com versão atual.")

    print("🔑 Autenticando Ngrok...")
    ngrok.set_auth_token(NGROK_TOKEN)

    # 1. Start Streamlit
    print("🔌 Subindo Servidor Streamlit (Background)...")
    run_command("streamlit run frontend/app.py &", background=True)
    time.sleep(3) # Wait for it to boot

    # 2. Start Ngrok Tunnel
    print("🔗 Criando Túnel Seguro (Ngrok)...")
    # Kill previous process if any
    ngrok.kill()

    try:
        # Create tunnel
        public_url = ngrok.connect(8501).public_url
        print("\n==================================================")
        print("🎉 ACESSE SEU APP AQUI (100% Estável):")
        print(f"👉 {public_url}")
        print("==================================================")
        print("ℹ️ Mantenha esta célula rodando.")

        # Keep alive
        process = subprocess.Popen(['tail', '-f', '/dev/null'])
        process.wait()

    except Exception as e:
        print(f"❌ Erro Ngrok: {e}")

if __name__ == "__main__":
    main()
