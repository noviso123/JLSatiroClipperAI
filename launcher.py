import subprocess
import time
import os
import sys

def run_command(command, background=False):
    if background:
        return subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        return subprocess.run(command, shell=True, check=True)

def main():
    print("🚀 [Launcher] Iniciando Aplicação V3.7...")

    # 1. Start Streamlit
    print("🔌 Subindo Servidor Streamlit (Background)...")
    run_command("streamlit run frontend/app.py &", background=True)
    time.sleep(3) # Wait for it to boot

    # 2. Start LocalTunnel
    print("🔗 Abrindo Túnel Público (Fixed URL Attempt)...")
    # Try fixed subdomain first
    cmd = "lt --port 8501 --subdomain viral-clipper-pro > url.txt 2>&1 &"
    run_command(cmd, background=True)
    time.sleep(5)

    # 3. Show Info
    print("\n==================================================")
    print("🔑 SUA SENHA (Tunnel Password):")
    os.system("wget -qO - ipv4.icanhazip.com")
    print("\n==================================================")

    print("\n👇 CLIQUE NO LINK ABAIXO E INSIRA A SENHA:")
    if os.path.exists("url.txt"):
        with open("url.txt", "r") as f:
            print(f.read().strip())
    else:
        print("⚠️ Erro ao ler URL.")
    print("\n==================================================")
    print("ℹ️ Mantenha esta célula rodando. Se o link não abrir, tente recarregar.")

if __name__ == "__main__":
    main()
