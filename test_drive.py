from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

creds = Credentials.from_service_account_file(
    'bpjs-drive-bot.json',
    scopes=SCOPES
)

service = build('drive', 'v3', credentials=creds)

print("Connecting to Google Drive...")

results = service.files().list(
    q="name='BPJS_UPLOADS'",
    fields="files(id,name)"
).execute()

print(results)
