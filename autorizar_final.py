import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from urllib.parse import urlparse, parse_qs

# Escopos necessários (Upload + Comentários)
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def main():
    secret_path = 'credentials.json'
    token_path = 'token.pickle'

    if not os.path.exists(secret_path):
        print(f"❌ ERRO: O arquivo '{secret_path}' não foi encontrado!")
        return

    print("🚀 MODO DE AUTORIZAÇÃO FINAL (TITANIUM)")
    print("-" * 60)

    flow = InstalledAppFlow.from_client_secrets_file(
        secret_path,
        scopes=SCOPES,
        redirect_uri='http://localhost:8080'
    )

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    print(f"\n1. Abra este link no seu navegador:\n\n{auth_url}\n")
    print("2. Faça o login e autorize.")
    print("3. A página vai dar erro (Site não encontrado).")

    print("\n" + "!"*60)
    print("COPIE A URL COMPLETA DA BARRA DE ENDEREÇO DA PÁGINA QUE DEU ERRO")
    print("E COLE ABAIXO.")
    print("!"*60)

    full_url = input("\n👉 Cole a URL gerada (ex: http://localhost:8080/?state=...&code=...): ").strip()

    try:
        query = urlparse(full_url).query
        params = parse_qs(query)
        code = params['code'][0]

        flow.fetch_token(code=code)
        creds = flow.credentials

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

        print("\n" + "="*40)
        print("✅ SUCESSO! 'token.pickle' criado.")
        print("Acesso permanente liberado.")
        print("="*40)

    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    main()
