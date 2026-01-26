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
    print("🚀 [Launcher] Iniciando Aplicação V6.2 (Fixed URL Edition)...")

    # 0. Auth Ngrok
    # User's Token (Restored)
    NGROK_TOKEN = "2tvNFAWzP9KMYZGpfCqx1EQmmwN_NPCQKjeqHD7pomCtJFVA"
    STATIC_DOMAIN = "glowing-cricket-firmly.ngrok-free.app"

    # 1. Update Check
    print("🔄 [Launcher] Verificando Atualizações...")
    try: run_command("git pull origin main")
    except: pass

    # 2. Authenticate
    print(f"🔑 Autenticando Ngrok (Domínio Fixo: {STATIC_DOMAIN})...")
    ngrok.set_auth_token(NGROK_TOKEN)

    # 3. Start Streamlit
    print("🔌 Subindo Servidor Streamlit (Background)...")
    run_command("streamlit run frontend/app.py &", background=True)
    time.sleep(3)

    # 4. Start Tunnel (Fixed Domain)
    print("🔗 Conectando Túnel Permanente...")
    ngrok.kill()

    try:
        # Connect using the specific domain from the screenshot
        url = ngrok.connect(8501, domain=STATIC_DOMAIN).public_url

        print("\n==================================================")
        print("🎉 SEU LINK FIXO ESTÁ ONLINE:")
        print(f"👉 {url}")
        print("==================================================")

    except Exception as e:
        print(f"❌ Erro Ngrok: {e}")
        print("💡 Dica: Se der erro de 'Bind', pode ser que a conta Free não suporte 2 túneis.")

    print("ℹ️ Mantenha esta célula rodando.")
    process = subprocess.Popen(['tail', '-f', '/dev/null'])
    process.wait()

if __name__ == "__main__":
    main()
