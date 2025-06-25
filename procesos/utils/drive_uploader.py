import io
import os
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from procesos.repositories.cancion_repository import CancionRepository
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "./credentials/credentials.json"

# Autentica y devuelve un cliente de Google Drive API
def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

# Crea una carpeta en Google Drive dentro de una carpeta padre
def create_folder(service, folder_name, parent_folder_id):
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id]
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")

# Sube un archivo a una carpeta específica en Google Drive
def upload_file(service, file_path, file_name, folder_id):
    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=False)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")

# Descarga un archivo específico por nombre desde una carpeta en Google Drive.
def download_file_from_folder(service, file_name, folder_id, destination_path):
    query = f"'{folder_id}' in parents and name contains '{file_name}' and trashed = false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get("files", [])
    if not files:
        return None
    file_id = files[0]["id"]
    full_name = files[0]["name"]
    ext = os.path.splitext(full_name)[1]  # Extraer extensión
    request = service.files().get_media(fileId=file_id)
    final_path = destination_path + ext
    with io.FileIO(final_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"[INFO] Descargando... {int(status.progress() * 100)}%")
    print(f"[INFO] Descarga completada: {final_path}")
    return final_path

# Elimina archivos de una carpeta de Google Drive cuyo nombre contenga un texto específico.
def delete_drive_file(service, folder_id, filename_contains):
    query = f"'{folder_id}' in parents and name contains '{filename_contains}' and trashed = false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get("files", [])
    for file in files:
        file_id = file["id"]
        service.files().delete(fileId=file_id).execute()

# Busca la carpeta por la Key, para decidir si hay que recrear la carpeta.
def get_or_create_folder_by_name(service, folder_name, parent_folder_id, cancion_id):
    query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    try:
        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        folders = results.get('files', [])
        if folders:
            # Si ya existe, devuelve el ID
            print(f"[INFO] Carpeta encontrada: {folders[0]['id']}")
            return folders[0]['id']
        else:
            # Si no existe, la recrea con el mismo nombre de la Key
            repo = CancionRepository()
            logger.warning("[WARNING] Carpeta no encontrada, recreando carpeta...")
            print("[WARNING] Carpeta no encontrada, recreando carpeta...")
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            folder = service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            print("[INFO] Carpeta recreada correctamente.")
            new_url_drive = folder['id']
            # Actualiza la url de la carpeta en la base de datos.
            repo.update_url_drive(cancion_id=cancion_id, new_url_drive=new_url_drive)
            return new_url_drive
    except HttpError as e:
        logger.error("[ERROR] Error al buscar o crear carpeta: %s", str(e))
        print(f"[ERROR] Error al buscar o crear carpeta: {str(e)}")
        return None