import os
import base64
import json
import mimetypes
from flask import Flask, render_template, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

# ============================
# GOOGLE CREDS FROM ENV
# ============================
b64 = os.environ.get("GOOGLE_CREDS_B64")
if not b64:
    raise Exception("GOOGLE_CREDS_B64 not set")

creds_json = base64.b64decode(b64).decode("utf-8")

creds = service_account.Credentials.from_service_account_info(
    json.loads(creds_json),
    scopes=["https://www.googleapis.com/auth/drive"]
)

drive = build("drive", "v3", credentials=creds)

# ============================
# ROOT FOLDER (Shared Drive)
# ============================
ROOT_FOLDER_ID = "10hYwK4NEW4Wp3AtGPEx9A6wNmRo18BZz"

def get_root_folder():
    return ROOT_FOLDER_ID


def get_or_create_folder(folder_name):
    root = get_root_folder()

    q = (
        f"name='{folder_name}' and "
        f"'{root}' in parents and "
        f"mimeType='application/vnd.google-apps.folder'"
    )

    result = drive.files().list(
        q=q,
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    if result["files"]:
        return result["files"][0]["id"]

    folder = drive.files().create(
        body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [root]
        },
        supportsAllDrives=True,
        fields="id"
    ).execute()

    return folder["id"]


def upload_file(local_path, filename, folder_id):
    mime = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

    media = MediaFileUpload(local_path, mimetype=mime, resumable=True)

    drive.files().create(
        media_body=media,
        body={
            "name": filename,
            "parents": [folder_id]
        },
        supportsAllDrives=True
    ).execute()


# ============================
# ROUTES
# ============================
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

        return "Upload sukses"

    return render_template("index.html")


# ============================
# LOCAL RUN (Render ignores this)
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
