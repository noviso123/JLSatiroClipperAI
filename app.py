import os
import sys
import warnings

# Desabilitar verificações de SSL e avisos (Necessário para redes restritivas/corporativas)
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Patching requests for global bypass
orig_request = requests.Session.request
def patched_request(self, method, url, **kwargs):
    kwargs.setdefault('verify', False)
    return orig_request(self, method, url, **kwargs)
requests.Session.request = patched_request

# Unificação Omega: app.py agora é o lançador oficial do Titanium Ultimate
if __name__ == "__main__":
    from frontend import ui
    print("🚀 Iniciando JLSatiro Clipper AI - V24.0 (TITANIUM ULTIMATE)...")
    ui.demo.launch(share=False)
