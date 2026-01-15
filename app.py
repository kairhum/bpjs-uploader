from flask import Flask, render_template, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_httplib2 import AuthorizedHttp
import os, base64, json, httplib2, mimetypes

app = Flask(__name__)

# =======================
# Load Google Credentials from ENV (Base64)
# =======================
b64 = os.environ.get("GOOGLE_CREDS_B64")
if not b64:
    raise Exception("GOOGLE_CREDS_B64 not found in environment")

creds_json = base64.b64decode(b64).decode("utf-8")

creds = service_account.Credentials.from_service_account_info(
    json.loads(creds_json),
    scopes=["https://www.googleapis.com/auth/drive"]
)

authed_http = AuthorizedHttp(creds, http=httplib2.Http(timeout=60))
drive = build("drive", "v3", http=authed_http)

# =======================
# Google Drive helpers
# =======================

ROOT_FOLDER_ID = "10hYwK4NEW4Wp3AtGPEx9A6wNmRo18BZz"	

def get_root_folder():
        return ROOT_FOLDER_ID


def get_or_create_folder(folder_name):
    q = f"name='{folder_name}' and '{ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder'"

    result = drive.files().list(
        q=q,
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    if result['files']:
        return result['files'][0]['id']
    else:
        folder = drive.files().create(
            body={
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [ROOT_FOLDER_ID]
            },
            supportsAllDrives=True,
            fields='id'
        ).execute()
        return folder['id']


def upload_file(local_path, filename, folder_id):
    mime = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    media = MediaFileUpload(local_path, mimetype=mime, resumable=True)
   drive.files().create(
    media_body=media,
    body={
        'name': filename,
        'parents': [folder_id]
    },
    supportsAllDrives=True
).execute()



# =======================
# Flask route
# =======================

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        nama = request.form["nama"]
        perusahaan = request.form["perusahaan"]
        folder_name = f"{nama} {perusahaan}"

        folder_id = get_or_create_folder(folder_name)

        mapping = {
            "kk1": "KK 1",
            "ktp": "KTP Peserta",
            "absensi": "Absensi",
            "kronologi": "Kronologi",
            "saksi": "KTP 2 Saksi"
        }

        os.makedirs("temp", exist_ok=True)

        for field, label in mapping.items():
            file = request.files.get(field)
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1]
                filename = f"{label} {folder_name}{ext}"
                path = os.path.join("temp", filename)

                file.save(path)
                upload_file(path, filename, folder_id)
                os.remove(path)

        return "Upload sukses 🎉"

    return render_template("index.html")


# ⚠️ Jangan pakai app.run() di Render
# Gunicorn yang jalanin app ini
