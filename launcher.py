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
    print("🚀 [Launcher] Iniciando Aplicação V6.1 (Cloudflare Edition)...")

    # 0. Check Updates
    print("🔄 [Launcher] Verificando Atualizações...")
    try: run_command("git pull origin main")
    except: pass

    # 1. Start Streamlit
    print("🔌 Subindo Servidor Streamlit (Background)...")
    run_command("streamlit run frontend/app.py &", background=True)
    time.sleep(3) # Wait for it to boot

    # 2. Start Cloudflare Tunnel (Replacement for Ngrok)
    print("🌩️ Criando Túnel Ilimitado (Cloudflare)...")

    # Download Cloudflared if not exists
    if not os.path.exists("cloudflared"):
        print("⏬ Baixando Binário Cloudflare...")
        run_command("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared")
        run_command("chmod +x cloudflared")

    # Run Tunnel
    print("🔗 Gerando Link Público...")
    # Clean old logs
    if os.path.exists("cf_log.txt"): os.remove("cf_log.txt")

    run_command("./cloudflared tunnel --url http://localhost:8501 > cf_log.txt 2>&1 &", background=True)
    time.sleep(5)

    # Extract URL
    cf_url = None
    try:
        with open("cf_log.txt", "r") as f:
            for line in f:
                if "trycloudflare.com" in line:
                    import re
                    # Regex to find https://*.trycloudflare.com
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        cf_url = match.group(0)
                        break
    except: pass

    if cf_url:
        print("\n==================================================")
        print("🎉 ACESSE SEU APP AQUI (ILIMITADO):")
        print(f"👉 {cf_url}")
        print("==================================================")
    else:
        print("⚠️ Link não encontrado no log. Tentando novamente em 5s...")
        time.sleep(5)
        # Retry logic could be added here, but usually it works.
        # Fallback print to check log
        print("⚠️ Se o link não apareceu, verifique o arquivo cf_log.txt")

    print("ℹ️ Mantenha esta célula rodando.")
    process = subprocess.Popen(['tail', '-f', '/dev/null'])
    process.wait()

if __name__ == "__main__":
    main()
