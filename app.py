import os
import json
import mimetypes
from flask import Flask, render_template, request, redirect, session, url_for
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

app = Flask(__name__)
app.secret_key = "bpjs-secret-key"

# ============================
# CONFIG
# ============================
SCOPES = ["https://www.googleapis.com/auth/drive"]
CLIENT_SECRETS_FILE = "oauth_client.json"
TOKEN_FILE = "token.json"

ROOT_FOLDER_ID = "10hYwK4NEW4Wp3AtGPEx9A6wNmRo18BZz"
REDIRECT_URI = "https://bpjs-tk-upload-rs-semen-gresik.onrender.com/oauth2callback"

# ============================
# OAUTH HELPERS
# ============================
def get_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def get_drive():
    if not os.path.exists(TOKEN_FILE):
        return None

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)

# ============================
# AUTH ROUTES
# ============================
@app.route("/login")
def login():
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    flow = get_flow()
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    return redirect("/")   # <- ini yang bikin anti error refresh

# ============================
# DRIVE HELPERS
# ============================
def get_or_create_folder(drive, folder_name):
    q = (
        f"name='{folder_name}' and "
        f"'{ROOT_FOLDER_ID}' in parents and "
        f"mimeType='application/vnd.google-apps.folder'"
    )

    result = drive.files().list(
        q=q,
        fields="files(id,name)"
    ).execute()

    if result["files"]:
        return result["files"][0]["id"]

    folder = drive.files().create(
        body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [ROOT_FOLDER_ID]
        },
        fields="id"
    ).execute()

    return folder["id"]

def upload_file(drive, local_path, filename, folder_id):
    mime = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    media = MediaFileUpload(local_path, mimetype=mime, resumable=True)

    drive.files().create(
        media_body=media,
        body={
            "name": filename,
            "parents": [folder_id]
        }
    ).execute()

# ============================
# MAIN ROUTE
# ============================
@app.route("/", methods=["GET", "POST"])
def index():
    drive = get_drive()
    if not drive:
        return redirect("/login")

    if request.method == "POST":
        nama = request.form["nama"]
        perusahaan = request.form["perusahaan"]
        folder_name = f"{nama} {perusahaan}"

        folder_id = get_or_create_folder(drive, folder_name)

        mapping = {
            "kk1": "KK 1",
            "ktp": "KTP Peserta",
            "kpj": "Kartu Peserta Jamsostek",
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
                upload_file(drive, path, filename, folder_id)
                os.remove(path)

        return "Upload sukses"

    return render_template("index.html")

# ============================
# LOCAL RUN
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
