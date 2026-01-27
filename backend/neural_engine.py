import os
import time
from typing import List, Optional

try:
    from pydantic import BaseModel, Field
    import instructor
    from llama_cpp import Llama
except ImportError:
    pass # Dependencies might not be installed on local dev

class VideoMetadataSchema(BaseModel):
    title: str = Field(description="Título viral para YouTube Shorts (Max 90 chars). Use emojis e gatilhos de curiosidade.")
    description: str = Field(description="Descrição otimizada para SEO (Max 300 chars). Inclua CTA e resumo.")
    tags: List[str] = Field(description="Lista de 5-10 tags virais relevantes ao conteúdo (ex: #Shorts, #Dinheiro).")
    pinned_comment: str = Field(description="Pergunta de engajamento para fixar nos comentários.")

class NeuralEngine:
    def __init__(self, model_path="model.gguf"):
        self.client = None
        if os.path.exists(model_path):
            print("🧠 Carregando Cérebro Neural (VRAM)...")
            try:
                # Load Llama with GPU offload
                llm = Llama(
                    model_path=model_path,
                    n_gpu_layers=-1, # All layers to GPU
                    n_ctx=2048, # Context window
                    verbose=False
                )
                # Patch with Instructor
                self.client = instructor.patch(
                    create=llm.create_chat_completion_openai_v1,
                    mode=instructor.Mode.JSON_SCHEMA
                )
                print("✅ Neural Engine Ativado!")
            except Exception as e:
                print(f"⚠️ Falha ao carregar Neural Engine: {e}")

    def generate(self, clean_text: str, user_hashtags: str = "") -> dict:
        if not self.client:
            return None

        prompt = f"""
        Analise a seguinte transcrição de um vídeo curto (Shorts) e gere metadados virais.

        # Transcrição:
        "{clean_text[:1500]}"

        # Hashtags Obrigatórias do Usuário (Inclua se houver):
        {user_hashtags}

        # Objetivo:
        Crie um Título explosivo, uma Descrição com CTA, Tags otimizadas e um Comentário para engajar.
        """

        try:
            start_t = time.time()
            resp = self.client.chat.completions.create(
                model="llama-3.2-3b",
                messages=[
                    {"role": "system", "content": "Você é um especialista em YouTube Shorts Viral."},
                    {"role": "user", "content": prompt}
                ],
                response_model=VideoMetadataSchema
            )
            print(f"⚡ Inferência Neural: {time.time() - start_t:.2f}s")

            # Convert to dict for compatibility
            return {
                "title": resp.title,
                "description": resp.description,
                "tags": resp.tags,
                "pinned_comment": resp.pinned_comment,
                "privacy": "private"
            }
        except Exception as e:
            print(f"❌ Erro na Inferência: {e}")
            return None
