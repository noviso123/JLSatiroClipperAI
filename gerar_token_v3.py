import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from urllib.parse import urlparse, parse_qs

# Escopos necessários
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def main():
    secret_path = 'credentials.json'
    token_path = 'token.pickle'

    # URL fornecida pelo usuário no chat
    full_url = "http://localhost:8080/?state=kN2tkmVCGCIsG97H1EMAsvsOFrBFiY&code=4/0ASc3gC3AyDaL6bZa3x6fncPi4dgMiozDcIf3dnwZTu3NCl2avUH9Xo19300G62VkRlt08A&scope=https://www.googleapis.com/auth/youtube.force-ssl%20https://www.googleapis.com/auth/youtube.upload"

    # Extrair o código da URL
    query = urlparse(full_url).query
    params = parse_qs(query)

    if 'code' not in params:
        print("❌ ERRO: Não encontrei o parâmetro 'code' na URL.")
        return

    code = params['code'][0]
    print(f"📦 Processando código: {code[:15]}...")

    flow = InstalledAppFlow.from_client_secrets_file(
        secret_path,
        scopes=SCOPES,
        redirect_uri='http://localhost:8080'
    )

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

        print("\n" + "="*40)
        print("✅ SUCESSO TOTAL! 'token.pickle' gerado.")
        print("O robô agora tem acesso permanente ao canal.")
        print("="*40)
    except Exception as e:
        print(f"❌ ERRO FINAL AO GERAR TOKEN: {e}")

if __name__ == "__main__":
    main()
