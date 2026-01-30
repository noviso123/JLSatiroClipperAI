import asyncio
import edge_tts
import os
import hashlib

# List must match processing.py exactly
PHRASES = [
    "VOCÊ NÃO VAI ACREDITAR!",
    "O SEGREDO REVELADO!",
    "ISSO MUDA TUDO!",
    "OLHA O QUE ACONTECEU!",
    "PRESTE MUITA ATENÇÃO!",
    "NINGUÉM TE CONTA ISSO!",
    "A VERDADE APARECEU!",
    "VOCÊ PRECISA SABER!",
    "ISSO É IMPOSSÍVEL!",
    "MENTIRAM PARA VOCÊ!",
    "O DETALHE SECRETO!",
    "VOCÊ VAI SE CHOCAR!",
    "PARE TUDO AGORA!",
    "A MELHOR PARTE!",
    "ISSO É INSANO!"
]

VOICE = "pt-BR-AntonioNeural"
OUTPUT_DIR = os.path.join("models", "hooks")

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 Iniciando Download de {len(PHRASES)} Hooks (Voz: {VOICE})...")

    for text in PHRASES:
        # Match audio_engine.py hash logic
        clean_text = "".join([c for c in text.upper() if c.isalnum() or c.isspace()]).strip()
        hash_txt = hashlib.md5(clean_text.encode()).hexdigest()[:10]
        filename = os.path.join(OUTPUT_DIR, f"{hash_txt}.mp3")

        if os.path.exists(filename):
            print(f"✅ [CACHE] {text} -> {filename}")
            continue

        print(f"⬇️ [BAIXANDO] {text}...")
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(filename)
            print(f"   -> Salvo em {filename}")
        except Exception as e:
            print(f"❌ Erro ao baixar '{text}': {e}")

    print("\n✅ Concluído! Hooks disponíveis offline.")

if __name__ == "__main__":
    asyncio.run(main())
