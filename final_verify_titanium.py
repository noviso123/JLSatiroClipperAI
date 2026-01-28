import os
import datetime
import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Escopos
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def get_service():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    return build('youtube', 'v3', credentials=creds)

def upload_clip(path, title, publish_at):
    print(f"🎬 Enviando {path} (VERTICAL) -> Agendado para {publish_at}")
    youtube = get_service()

    # IMPORTANTE: Para ser Shorts, o título ou descrição DEVE conter #shorts
    # E o vídeo deve ser vertical (o que já é o caso do vert_test_*.mp4)
    body = {
        'snippet': {
            'title': f"{title} #shorts",
            'description': 'Teste Final Titanium V3 - Formato Vertical Shorts AI',
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'private',
            'publishAt': publish_at,
            'selfDeclaredMadeForKids': False
        }
    }

    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(path, chunksize=-1, resumable=True)
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"⏳ {title}... {int(status.progress() * 100)}%")

    print(f"✅ Sucesso! ID: {response['id']}")
    return response['id']

if __name__ == "__main__":
    # Current Local: 15:40 (-03:00) -> UTC: 18:40
    # Agendamento precisa ser no futuro.
    # Vamos usar slots fixos para o teste
    now = datetime.datetime.now(datetime.UTC)

    # Slot 1: Daqui a 10 min
    t1 = (now + datetime.timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:00Z")
    # Slot 2: 23:00 UTC (Equivalente a 20:00 Local)
    t2 = now.strftime("%Y-%m-%dT23:00:00Z")

    print(f"🕒 Horário 1 (UTC): {t1}")
    print(f"🕒 Horário 2 (UTC): {t2}")

    try:
        # Clip 1 Vertical
        upload_clip("vert_test_1.mp4", "SHORTS TESTE 1 - Imediato", t1)
        # Clip 2 Vertical
        upload_clip("vert_test_2.mp4", "SHORTS TESTE 2 - Agendado 20h", t2)

        print("\n🏆 TESTE SHORTS TITANIUM CONCLUÍDO!")
    except Exception as e:
        print(f"❌ ERRO FINAL: {e}")
