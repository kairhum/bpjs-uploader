from flask import Flask, render_template, request, redirect
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
from datetime import datetime

app = Flask(__name__)

# Google Drive Auth
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(
    'bpjs-drive-bot.json',
    scopes=SCOPES
)
import httplib2
from googleapiclient.discovery import build

import httplib2
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp

authed_http = AuthorizedHttp(creds, http=httplib2.Http(timeout=60))
drive = build('drive', 'v3', http=authed_http)



ROOT_FOLDER_ID = None   # kita isi nanti

# cari folder BPJS_UPLOADS
def get_root_folder():
    global ROOT_FOLDER_ID
    if ROOT_FOLDER_ID:
        return ROOT_FOLDER_ID

    q = "name='BPJS_UPLOADS' and mimeType='application/vnd.google-apps.folder'"
    result = drive.files().list(q=q, fields="files(id,name)").execute()

    if result['files']:
        ROOT_FOLDER_ID = result['files'][0]['id']
        return ROOT_FOLDER_ID
    else:
        raise Exception("Folder BPJS_UPLOADS tidak ditemukan di Drive")

# cari / buat folder peserta
def get_or_create_folder(folder_name):
    root = get_root_folder()
    q = f"name='{folder_name}' and '{root}' in parents and mimeType='application/vnd.google-apps.folder'"
    result = drive.files().list(q=q, fields="files(id,name)").execute()

    if result['files']:
        return result['files'][0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [root]
        }
        folder = drive.files().create(body=file_metadata, fields='id').execute()
        return folder['id']


@app.route('/', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        nama = request.form['nama']
        perusahaan = request.form['perusahaan']
        folder_name = f"{nama} {perusahaan}"

        folder_id = get_or_create_folder(folder_name)

        mapping = {
            'kk1': 'KK 1',
            'ktp': 'KTP Peserta',
            'absensi': 'Absensi',
            'kronologi': 'Kronologi',
            'saksi': 'KTP 2 Saksi'
        }

        for field, label in mapping.items():
            file = request.files.get(field)
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1]
                filename = f"{label} {folder_name}{ext}"
                path = os.path.join("temp", filename)
                os.makedirs("temp", exist_ok=True)
                file.save(path)

                media = MediaFileUpload(path, resumable=True)
                drive.files().create(
                    media_body=media,
                    body={
                        'name': filename,
                        'parents': [folder_id]
                    }
                ).execute()

                os.remove(path)

        return "Upload sukses"

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
