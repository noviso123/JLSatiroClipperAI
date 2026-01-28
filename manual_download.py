import os
import requests
import sys
import time

# NUCLEAR SSL FIX
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except: pass

MODEL_NAME = "tiny"
BASE_URL = f"https://huggingface.co/Systran/faster-whisper-{MODEL_NAME}/resolve/main"
DEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", f"whisper-{MODEL_NAME}")

FILES = [
    "config.json",
    "tokenizer.json",
    "vocabulary.txt",
    "model.bin"
]

def download_file(url, dest):
    print(f"⬇️ Baixando: {os.path.basename(dest)}...")
    try:
        # Stream download for progress
        with requests.get(url, stream=True, verify=False, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0

            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress bar logic
                        if total_size > 0:
                            percent = int(100 * downloaded / total_size)
                            # Print progress every 5%
                            if percent % 5 == 0 and percent != 100:
                                sys.stdout.write(f"\r⏳ Progresso: {percent}% ({downloaded//1024//1024}MB)")
                                sys.stdout.flush()
            print("\n✅ Concluído.")
            return True
    except Exception as e:
        print(f"\n❌ Erro ao baixar {url}: {e}")
        return False

def main():
    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"🚀 Iniciando Download Manual (Resiliente) - Modelo: {MODEL_NAME}")
    print(f"📂 Pasta: {DEST_DIR}")

    success = True
    for fname in FILES:
        url = f"{BASE_URL}/{fname}"
        dest = os.path.join(DEST_DIR, fname)

        # Verify sizes if exists? No, just overwrite to be safe or check if complete.
        if os.path.exists(dest):
             # Simple check: json are small, bin is big.
             if fname.endswith("bin") and os.path.getsize(dest) > 1000:
                 print(f"⚠️ {fname} já existe. Pulando.")
                 continue
             if not fname.endswith("bin") and os.path.getsize(dest) > 0:
                  print(f"⚠️ {fname} já existe. Pulando.")
                  continue

        if not download_file(url, dest):
            success = False
            break

    if success:
        print("\n🎉 TODOS OS ARQUIVOS BAIXADOS COM SUCESSO!")
        print("Agora o sistema está PRONTO para rodar offline.")
    else:
        print("\n❌ Falha no download. Tente novamente.")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
