import os
import pickle
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes required for Drive and YouTube
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl' # Required for Comments
]

class GoogleServices:
    def __init__(self, client_secret_path='client_secret.json', token_path='token.pickle'):
        self.creds = None
        self.drive_service = None
        self.youtube_service = None
        self.client_secret_path = client_secret_path
        self.token_path = token_path
        self.authenticate()

    def authenticate(self):
        """Authenticates the user and saves the token."""
        print("🔐 Iniciando Autenticação Google API...")

        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            except Exception as e:
                print(f"⚠️ Token inválido/corrompido: {e}")

        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("🔄 Renovando Token Expirado...")
                try:
                    self.creds.refresh(Request())
                except:
                    self._new_login()
            else:
                self._new_login()

            # Save the credentials for the next run
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
                print("✅ Token salvo com sucesso!")
            except: pass

        # Build Services
        try:
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            self.youtube_service = build('youtube', 'v3', credentials=self.creds)
            print("✅ Conectado ao Google Drive e YouTube API!")
            self.verify_channel()
        except Exception as e:
            print(f"❌ Erro ao conectar serviços Google: {e}")

    def verify_channel(self):
        """Prints the connected YouTube channel name."""
        if not self.youtube_service: return
        try:
            request = self.youtube_service.channels().list(
                part="snippet",
                mine=True
            )
            response = request.execute()
            if response['items']:
                channel_name = response['items'][0]['snippet']['title']
                print(f"📺 CANAL CONECTADO: {channel_name}")
            else:
                print("⚠️ Nenhum canal encontrado nesta conta.")
        except Exception as e:
            print(f"⚠️ Erro ao verificar nome do canal: {e}")

    def _new_login(self):
        if not os.path.exists(self.client_secret_path):
            print("❌ ERRO: 'client_secret.json' não encontrado! O upload automático falhará.")
            return

        print("⚠️ Necessário Autenticação Inicial (Apenas uma vez)...")
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)

        # HEADLESS AUTH FOR COLAB (Phase 2 Requirement)
        # We enforce run_console so the user can copy-paste the URL/Code
        print("\n" + "="*60)
        print("🔗 CLIQUE NESTE LINK PARA AUTENTICAR:")
        print("="*60 + "\n")
        self.creds = flow.run_console()

    def upload_to_drive(self, file_path, folder_name="JLSatiro_AI_Studio"):
        """Uploads a file to a specific folder in Drive."""
        if not self.drive_service: return None

        try:
            filename = os.path.basename(file_path)

            # Check/Create Folder
            folder_id = self._get_folder_id(folder_name)
            if not folder_id:
                folder_id = self._create_folder(folder_name)

            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            media = MediaFileUpload(file_path, resumable=True)

            print(f"☁️ Enviando para o Drive: {filename}...")
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"✅ Upload Concluído! ID: {file.get('id')}")
            return file.get('id')
        except Exception as e:
            print(f"❌ Erro no Upload Drive: {e}")
            return None

    def upload_to_youtube(self, file_path, title, description, tags=[], category_id="22", privacy="private"):
        """Uploads a video to YouTube."""
        if not self.youtube_service: return None

        try:
            print(f"📺 Publicando no YouTube: {title}...")

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False,
                }
            }

            media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            request = self.youtube_service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"    ↳ Upload: {int(status.progress() * 100)}%")

            print(f"✅ Vídeo Publicado! ID: {response['id']}")
            return response['id']
        except Exception as e:
             print(f"❌ Erro no Upload YouTube: {e}")
             return None

    def post_comment(self, video_id, text):
        """Posts a top-level comment on a video."""
        if not self.youtube_service: return None
        try:
            print(f"💬 Postando comentário no vídeo {video_id}...")
            self.youtube_service.commentThreads().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": text
                            }
                        }
                    }
                }
            ).execute()
            print("✅ Comentário Publicado!")
            return True
        except Exception as e:
            print(f"❌ Erro ao postar comentário: {e}")
            return False

    def _get_folder_id(self, folder_name):
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items: return None
        return items[0]['id']

    def _create_folder(self, folder_name):
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = self.drive_service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')
