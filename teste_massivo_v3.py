import os
import datetime
import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

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

def upload_short_custom(path, title, publish_at):
    print(f"🎬 Enviando {path} -> Agendado para {publish_at}...")
    youtube = get_service()

    body = {
        'snippet': {
            'title': f"{title} #shorts",
            'description': 'Teste Massivo Titanium V3 - Estreia Programada #shorts',
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
    now = datetime.datetime.now(datetime.UTC)

    # Slots
    t_agora = (now + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:00Z")
    t_1h = (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00Z")
    t_20h = now.strftime("%Y-%m-%dT23:00:00Z")

    print(f"🕒 Slot 1 (Agora): {t_agora}")
    print(f"🕒 Slot 2 (+1h): {t_1h}")
    print(f"🕒 Slot 3 (20h): {t_20h}")

    try:
        if os.path.exists("vert_1.mp4"):
            upload_short_custom("vert_1.mp4", "SHORTS RESTAURADO 1", t_agora)
        if os.path.exists("vert_2.mp4"):
            upload_short_custom("vert_2.mp4", "SHORTS RESTAURADO 2", t_1h)
        if os.path.exists("vert_3.mp4"):
            upload_short_custom("vert_3.mp4", "SHORTS RESTAURADO 3", t_20h)

        print("\n🏆 TESTE DE RESTAURAÇÃO CONCLUÍDO!")
    except Exception as e:
        print(f"❌ ERRO: {e}")
