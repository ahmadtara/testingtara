from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Inisialisasi flow dari credentials.json
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json', SCOPES)

# Tukar kode otentikasi dengan token
creds = flow.fetch_token(code='MASUKKAN_KODE_OTENTIKASI_DISINI')

# Simpan token ke file JSON
with open("token.json", "w") as token_file:
    token_file.write(creds.to_json())

print("✅ Token berhasil disimpan ke token.json")
