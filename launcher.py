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
    print("🚀 [Launcher] Iniciando Aplicação V6.5 (Ngrok FIXED URL)...")

    # 0. Cleanup Cloudflare (User Request)
    if os.path.exists("cloudflared"):
        try: os.remove("cloudflared")
        except: pass
    if os.path.exists("cf_log.txt"): os.remove("cf_log.txt")

    # 1. Auth Ngrok
    NGROK_TOKEN = "2tvNFAWzP9KMYZGpfCqx1EQmmwN_NPCQKjeqHD7pomCtJFVA"
    STATIC_DOMAIN = "glowing-cricket-firmly.ngrok-free.app"

    # 2. Update Check
    print("🔄 [Launcher] Verificando Atualizações...")
    try: run_command("git pull origin main")
    except: pass

    # 3. Authenticate
    print(f"🔑 Autenticando Ngrok (Domínio Fixo: {STATIC_DOMAIN})...")
    ngrok.set_auth_token(NGROK_TOKEN)

    # 4. Start Streamlit
    print("🔌 Subindo Servidor Streamlit (Background)...")
    run_command("streamlit run frontend/app.py &", background=True)
    time.sleep(3)

    # 5. Start Tunnel (Fixed Domain)
    print("🔗 Conectando Túnel Permanente...")
    ngrok.kill()

    try:
        url = ngrok.connect(8501, domain=STATIC_DOMAIN).public_url
        print("\n==================================================")
        print("🎉 SEU LINK FIXO ESTÁ ONLINE:")
        print(f"👉 {url}")
        print("==================================================")

    except Exception as e:
        print(f"❌ Erro Ngrok: {e}")
        print("💡 Se aparecer erro 725, sua conta excedeu o limite mensal.")

    print("ℹ️ Mantenha esta célula rodando.")
    process = subprocess.Popen(['tail', '-f', '/dev/null'])
    process.wait()

if __name__ == "__main__":
    main()
