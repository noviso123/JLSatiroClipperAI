import os
import subprocess
import sys

def main():
    print("🚀 [JLSatiro Clipper AI] Iniciando Sistema (V22.0 Modular)...")

    # Auto-Install for Colab/User convenience (if requirements missing)
    try:
        import mediapipe
    except ImportError:
        print("📦 Instalando dependências ausentes...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("🔌 Iniciando Interface Gráfica (Gradio)...")
    print("⚠️  Aguarde o link público (Ex: https://xxxx.gradio.live)")

    # Execute UI path
    ui_path = os.path.join("frontend", "ui.py")
    subprocess.run([sys.executable, ui_path])

if __name__ == "__main__":
    main()
