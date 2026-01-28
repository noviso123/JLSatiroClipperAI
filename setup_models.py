import os
import sys
import ssl
from faster_whisper import download_model

# NUCLEAR SSL FIX (Required for Setup)
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
import requests
from functools import partial

# Monkeypatch requests to ignore SSL verification globally
old_request = requests.Session.request
def new_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return old_request(self, method, url, *args, **kwargs)
requests.Session.request = new_request
requests.request = partial(requests.request, verify=False)
requests.get = partial(requests.get, verify=False)

import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL_NAME = "medium"
MODEL_PATH = os.path.join(MODEL_DIR, f"whisper-{MODEL_NAME}")

def download_local_model():
    print(f"🧠 Iniciando download do Modelo {MODEL_NAME} para uso OFFLINE...")
    print(f"📂 Destino: {MODEL_PATH}")

    os.makedirs(MODEL_PATH, exist_ok=True)

    try:
        # Downloads model files to the specific local directory
        path = download_model(MODEL_NAME, output_dir=MODEL_PATH)
        print(f"✅ Download Sucesso! Modelo salvo em: {path}")
        print("🚀 O sistema agora pode rodar sem internet.")
    except Exception as e:
        print(f"❌ Erro no Download: {e}")

if __name__ == "__main__":
    download_local_model()
