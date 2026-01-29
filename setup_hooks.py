import asyncio
import edge_tts
import os
import hashlib
import ssl

# Titanium SSL Bypass: Mandatory for restricted networks
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except: pass

# Titanium Standard Hook Library
HOOKS = [
    "O SEGREDO!",
    "ISSO É INSANO!",
    "OLHA ISSO!",
    "VOCÊ SABIA?",
    "FINAL É LOUCO!",
    "VEJA ISSO!",
    "OLHA O QUE ELE FEZ!",
    "NÃO ACREDITO!",
    "ISSO MUDA TUDO!",
    "PRESTE ATENÇÃO!"
]

VOICE = "pt-BR-AntonioNeural"
OUTPUT_DIR = os.path.join("models", "hooks")

async def pre_generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # SSL Bypass for restricted environments
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except: pass

    print(f"🚀 Iniciando Pré-Geração de {len(HOOKS)} Hooks Offline...")

    for text in HOOKS:
        clean_text = "".join([c for c in text.upper() if c.isalnum() or c.isspace()]).strip()
        hash_txt = hashlib.md5(clean_text.encode()).hexdigest()[:10]
        output_path = os.path.join(OUTPUT_DIR, f"{hash_txt}.mp3")

        if os.path.exists(output_path):
            print(f"✅ Já existe: {text}")
            continue

        print(f"🎙️ Gerando: {text} -> {output_path}")
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(output_path)
            print(f"✅ Sucesso!")
        except Exception as e:
            print(f"❌ Falha em '{text}': {e}")

if __name__ == "__main__":
    asyncio.run(pre_generate())
