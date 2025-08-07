from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
creds = flow.run_local_server(port=8080)

print("Refresh Token:", creds.refresh_token)
