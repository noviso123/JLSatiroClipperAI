import os
import pickle
import datetime
import json
import re
import glob
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# SCOPES for YouTube Upload and Comments
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]
STATE_FILE = 'upload_state.json'

def get_authenticated_service():
    """
    Returns an authorized YouTube API service using the permanent token.pickle.
    """
    credentials = None
    token_path = 'token.pickle'
    secret_path = 'credentials.json'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists(secret_path):
                raise FileNotFoundError(f"❌ Chave 'credentials.json' não encontrada!")
            flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
            credentials = flow.run_local_server(port=8080)

        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)

    return build('youtube', 'v3', credentials=credentials)

def get_next_publish_time():
    """
    Calculates the next available slot (09:00, 12:00, 15:00, 18:00, 21:00 UTC)
    ensuring it is at least 30 minutes in the future.
    """
    if not os.path.exists(STATE_FILE):
        state = {"total_uploaded": 0}
    else:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)

    total = state.get("total_uploaded", 0)
    slots = [9, 12, 15, 18, 21] # Hours

    # Start searching from "today"
    found = False
    day_offset = total // 5
    slot_idx = total % 5

    # Current UTC time
    now = datetime.datetime.now(datetime.UTC)

    while not found:
        target_date = now.date() + datetime.timedelta(days=day_offset)
        target_hour = slots[slot_idx]

        target_dt = datetime.datetime.combine(
            target_date,
            datetime.time(hour=target_hour)
        ).replace(tzinfo=datetime.UTC)

        # Must be at least 30 mins in the future
        if target_dt > (now + datetime.timedelta(minutes=30)):
            found = True
        else:
            # Try next slot
            total += 1
            day_offset = total // 5
            slot_idx = total % 5

    state["total_uploaded"] = total + 1
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

    return target_dt.strftime("%Y-%m-%dT%H:%M:00Z")

def generate_viral_hashtags(text=""):
    generic = ["#shorts", "#viral", "#inteligenciaartificial", "#cortes", "#podcast", "#sucesso", "#disciplina"]
    if text:
        words = re.findall(r'\w{6,}', text.lower())
        extra = ["#" + w for w in list(set(words))[:3]]
        return " ".join(generic + extra)
    return " ".join(generic)

def post_comment(youtube, video_id, comment_text):
    if not comment_text: return
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
        ).execute()
        print(f"💬 Comentário postado no vídeo {video_id}")
    except Exception as e:
        print(f"⚠️ Erro ao postar comentário: {e}")

def upload_short(video_path, title, transcription_text, user_hashtags="", pinned_comment=""):
    publish_at = get_next_publish_time()
    final_hashtags = user_hashtags if user_hashtags.strip() else generate_viral_hashtags(transcription_text)
    clean_title = (title[:70] + " " + final_hashtags.split()[0])[:100]
    final_description = f"{title}\n\n{final_hashtags}\n\nGerado por JLSatiro Clipper AI."

    print(f"🚀 Enviando: {clean_title} | Agendado: {publish_at}")
    youtube = get_authenticated_service()

    body = {
        'snippet': {
            'title': clean_title,
            'description': final_description,
            'tags': final_hashtags.replace("#", "").split(),
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'private',
            'publishAt': publish_at,
            'selfDeclaredMadeForKids': False
        }
    }

    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )

    response = None
    try:
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print(f"⏳ Upload {clean_title}... {int(status.progress() * 100)}%")
    except HttpError as e:
        if "uploadLimitExceeded" in str(e):
            print("\n" + "!"*60)
            print("⚠️ LIMITE DE COTA DA API ATINGIDO!")
            print("Não é possível enviar mais vídeos por hoje via API.")
            print("!"*60 + "\n")
            return None
        else:
            raise e

    if pinned_comment:
        post_comment(youtube, response['id'], pinned_comment)

    return response['id'], publish_at
