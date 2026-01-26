import os
import subprocess

def main():
    print("💎 [Launcher] Iniciando JLSatiro Cobalt V16.0 (GPU)...")
    print("🔄 Verificando Atualizações...")
    try: subprocess.run("git pull origin main", shell=True)
    except: pass

    print("🔌 Iniciando Servidor...")
    print("⚠️ AGUARDE: O link público vai aparecer abaixo em alguns segundos (Ex: https://xxxx.gradio.live)")

    # Run the Gradio App
    # It will block here and print the URL to stdout
    os.system("python frontend/ui.py")

if __name__ == "__main__":
    main()
