import os
import subprocess
import sys

def main():
    print("🚀 [JLSatiro Clipper AI] Iniciando Sistema (V23.0 Titanium Final)...")

    # Auto-Install for Colab/User convenience (if requirements missing)
    # Auto-Install for Colab/User convenience (if requirements missing)
    try:
        import mediapipe
        import gradio
        from packaging import version
        # Check specific critical version for Gradio
        if version.parse(gradio.__version__) < version.parse("4.44.1"):
            raise ImportError("Gradio outdated")
    except ImportError as e:
        print(f"📦 Instalando/Atualizando dependências... ({str(e)})")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade", "--trusted-host", "pypi.org", "--trusted-host", "pypi.python.org", "--trusted-host", "files.pythonhosted.org"])

    print("🔌 Iniciando Interface Gráfica (Gradio)...")
    print("⚠️  Aguarde o link público (Ex: https://xxxx.gradio.live)")

    # Execute UI path
    ui_path = os.path.join("frontend", "ui.py")
    subprocess.run([sys.executable, ui_path])

if __name__ == "__main__":
    main()
