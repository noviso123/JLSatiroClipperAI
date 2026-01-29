from dataclasses import dataclass, field
from typing import List
import collections
import random

# Using dataclasses to mimic Pydantic behavior without requiring the external dependency immediately.
# If user installs pydantic, this can be easily swapped to "class VideoMetadata(BaseModel):"

@dataclass
class VideoMetadata:
    title: str
    description: str
    tags: List[str]
    category_id: str = "22" # People & Blogs
    privacy: str = "private"
    pinned_comment: str = ""

    def validate(self):
        # Enforce YouTube Constraints
        if len(self.title) > 100:
            self.title = self.title[:97] + "..."
        if len(self.tags) > 500: # Total characters constraint check (simplified here to item count for now)
            self.tags = self.tags[:40]

class MetadataEngine:
    def __init__(self):
        # Stopwords (PT-BR + Common Helpers)
        self.STOPWORDS = {
            "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma", "os", "no",
            "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu",
            "sua", "ou", "ser", "quando", "muito", "nos", "já", "está", "eu", "também", "só", "pelo", "pela",
            "até", "isso", "ela", "entre", "era", "depois", "sem", "mesmo", "aos", "ter", "seus", "quem", "nas",
            "me", "esse", "eles", "estão", "você", "tinha", "foram", "essa", "num", "nem", "suas", "meu", "às",
            "minha", "têm", "numa", "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho", "lhe",
            "deles", "essas", "esses", "pelas", "este", "fosse", "dele", "tu", "te", "vocês", "vos", "lhes",
            "meus", "minhas", "teu", "tua", "teus", "tuas", "nosso", "nossa", "nossos", "nossas", "dela",
            "delas", "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas", "isto", "aquilo",
            "estou", "está", "estamos", "estão", "estive", "esteve", "estivemos", "estiveram", "estava",
            "estávamos", "estavam", "estivera", "estivéramos", "esteja", "ejamos", "estejam", "estivesse",
            "estivéssemos", "estivessem", "estiver", "estivermos", "estiverem", "hei", "há", "havemos",
            "hão", "houve", "houvemos", "houveram", "houvera", "houvéramos", "haja", "hajamos", "hajam",
            "houvesse", "houvéssemos", "houvessem", "houver", "houvermos", "houverem", "houverei", "houverá",
            "houveremos", "houverão", "houveria", "houveríamos", "houveriam", "sou", "somos", "são", "era",
            "éramos", "eram", "fui", "foi", "fomos", "foram", "fora", "fôramos", "seja", "sejamos", "sejam",
            "fosse", "fôssemos", "fossem", "for", "formos", "forem", "serei", "será", "seremos", "serão",
            "seria", "seríamos", "seriam", "tenho", "tem", "temos", "tém", "tinha", "tínhamos", "tinham",
            "tive", "teve", "tivemos", "tiveram", "tivera", "tivéramos", "tenha", "tenhamos", "tenham",
            "tivesse", "tivéssemos", "tivessem", "tiver", "tivermos", "tiverem", "terei", "terá", "teremos",
            "terão", "teria", "teríamos", "teriam", "video", "vídeo", "falar", "falando", "então", "aí", "pra", "tá", "né"
        }

    def _extract_keywords(self, text, top_n=8):
        """NLP-Lite Frequency Analysis"""
        if not text: return []
        words = text.replace('.', '').replace(',', '').replace('!', '').replace('?', '').lower().split()
        filtered = [w for w in words if w not in self.STOPWORDS and len(w) > 3]
        count = collections.Counter(filtered)
        return [item[0] for item in count.most_common(top_n)]

    def generate(self, clip_words, user_hashtags_str="") -> VideoMetadata:
        # 1. Prepare Text
        transcript_text = ""
        try: transcript_text = " ".join([w['word'] for w in clip_words[:15]])
        except: transcript_text = "Video Viral Incrível"

        full_text = " ".join([w['word'] for w in clip_words])
        full_text_lower = full_text.lower()

        # 2. Extract Keywords (Organic)
        organic_keywords = self._extract_keywords(full_text)
        organic_tags = [f"#{w}" for w in organic_keywords]

        # 3. Strategy Merge Tags
        user_tags_list = [t.strip() for t in user_hashtags_str.split(' ') if t.strip().startswith('#')]

        context_map = {
            "dinheiro": ["#rendaextra", "#marketingdigital"],
            "Deus": ["#fe", "#motivacao"],
            "vender": ["#vendas", "#business"],
            "mulher": ["#empoderamento"],
            "futuro": ["#inovacao"]
        }

        context_tags = []
        for key, tags in context_map.items():
            if key in full_text_lower: context_tags.extend(tags)

        # Deduplication
        final_tags = []
        seen = set()

        # Priority Queue: User > Organic > Context > Base
        for t in user_tags_list:
            if t not in seen: final_tags.append(t); seen.add(t)
        for t in organic_tags:
            if t not in seen and len(final_tags) < 15: final_tags.append(t); seen.add(t)
        for t in context_tags:
            if t not in seen and len(final_tags) < 15: final_tags.append(t); seen.add(t)

        base_virals = ["#Shorts", "#Viral", "#Brasil"]
        for t in base_virals:
            if t not in seen and len(final_tags) < 15: final_tags.append(t); seen.add(t)

        tags_api = [t.replace('#', '') for t in final_tags]
        tags_display = " ".join(final_tags)

        # 4. Smart Title
        clean_hook = transcript_text.replace('"', '').replace('.', '').strip()
        if len(clean_hook) > 50: clean_hook = clean_hook[:47] + "..."
        if not clean_hook: clean_hook = "Segredo Revelado!"

        title_keyword = organic_keywords[0].upper() if organic_keywords else "VIRAL"
        title = f"{clean_hook} 🤯| #{title_keyword} #shorts"

        # 5. Smart Description
        description = (
            f"🔥 {clean_hook}\n\n"
            f"👇 Inscreva-se no canal para não perder o próximo vídeo!\n"
            f"{tags_display}\n\n"
            "Disclaimer: This video is for educational purposes. All rights belong to respective owners.\n"
            "#shorts #viral #growth"
        )

        # 6. Smart Comment
        topic = organic_keywords[0].capitalize() if organic_keywords else "o video"
        comment = (
            f"👇 Qual sua opinião sobre {topic}? Comente abaixo!\n\n"
            "✅ Inscreva-se no canal para mais conteúdos como este!"
        )

        metadata = VideoMetadata(
            title=title,
            description=description,
            tags=tags_api,
            pinned_comment=comment
        )
        metadata.validate() # Enforce constraints
        return metadata
