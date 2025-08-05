from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import os
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from procesos.repositories.cancion_repository import CancionRepository
from ms_procesos import config
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = config.get_path_credentials()

# Autentica y devuelve un cliente de Google Drive API
def authenticate_drive():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

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
    # Verifica si ya existe un archivo con ese nombre
    query = (
        f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
    )
    try:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = response.get("files", [])
        # Si existe, elimina el archivo previo
        for file in files:
            file_id = file["id"]
            service.files().delete(fileId=file_id).execute()
    except HttpError as e:
        msg = f"[ERROR] Error verificando existencia de archivo: {str(e)}"
        logger.error(msg)
        print(msg)
    # Ahora sube el nuevo archivo
    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=False)
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()
        msg = f"[INFO] Archivo subido: {file_name}"
        logger.info(msg)
        print(msg)
        return file.get("id")
    except HttpError as e:
        msg = f"[ERROR] Error subiendo archivo: {str(e)}"
        logger.error(msg)
        print(msg)
        return None


# Descarga un archivo específico por nombre desde una carpeta en Google Drive.
def download_file_from_folder(service, file_name, folder_id, destination_path):
    query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
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
                msg = f"[INFO] Descargando... {int(status.progress() * 100)}%"
                logger.info(msg)
                print(msg)
    msg = f"[INFO] Descarga completada: {final_path}"
    logger.info(msg)
    print(msg)
    return final_path

def download_all_files(song_key, dest_dir):
    try:
        service = authenticate_drive()
        # Paso 1: Obtener ID del folder padre (kia_songs)
        parent_folder_id = CancionRepository().get_parent_folder()
        if not parent_folder_id:
            msg = "[ERROR] No se pudo obtener la carpeta principal 'kia_songs'."
            logger.error(msg)
            print(msg)
        # Paso 2: Buscar la carpeta cuyo nombre sea igual a la key
        query = f"'{parent_folder_id}' in parents and name = '{song_key}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()  # pylint: disable=no-member
        folders = response.get('files', [])
        if not folders:
            msg = f"[ERROR] No se encontró la carpeta con key {song_key} en Google Drive."
            logger.error(msg)
            print(msg)
        folder_id = folders[0]['id']
        # Paso 3: Obtener todos los archivos dentro de la carpeta
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, modifiedTime)').execute() # pylint: disable=no-member
        files = response.get('files', [])
        if not files:
            msg = f"[WARNING] No se encontraron archivos en la carpeta {song_key} en Google Drive."
            logger.info(msg)
            print(msg)
        # Paso 4: Descargar todos los archivos
        with ThreadPoolExecutor(max_workers=10) as executor:
            for file in files:
                executor.submit(download_file, file, dest_dir)
        msg = f"[INFO] Archivos descargados para la key {song_key}"
        logger.info(msg)
        print(msg)
    except HttpError as error:
        msg = f"[ERROR] Error al acceder a Google Drive: {error}"
        logger.error(msg)
        print(msg)

def download_file(file, dest_dir):
    file_name = file['name']
    # Ignorar archivos Render.
    if file_name in ['render_kfn_p1.mp4', 'render_kfn_p1_ensayo.mp4']:
        return
    local_path = os.path.join(dest_dir, file_name)
    # Si no es 'kara_fun.kfn' y ya existe localmente, omitir la descarga
    if file_name != 'kara_fun.kfn' and os.path.exists(local_path):
        return
    try:
        service = authenticate_drive()
        file_id = file['id']
        request = service.files().get_media(fileId=file_id)  # pylint: disable=no-member
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            done = downloader.next_chunk()
        msg = f"[INFO] Archivo {file_name} descargado en: {local_path}"
        logger.info(msg)
        print(msg)
    except Exception as e:
        msg = f"[ERROR] Error al descargar {file_name}, {str(e)}"
        logger.error(msg)
        print(msg)

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
            msg = f"[INFO] Carpeta encontrada: {folders[0]['id']}"
            logger.info(msg)
            print(msg)
            return folders[0]['id']
        else:
            # Si no existe, la recrea con el mismo nombre de la Key
            repo = CancionRepository()
            msg = "[WARNING] Carpeta no encontrada, recreando carpeta..."
            logger.warning(msg)
            print(msg)
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
            msg = "[INFO] Carpeta recreada correctamente."
            logger.info(msg)
            print(msg)
            new_url_drive = folder['id']
            # Actualiza la url de la carpeta en la base de datos.
            repo.update_url_drive(cancion_id=cancion_id, new_url_drive=new_url_drive)
            return new_url_drive
    except HttpError as e:
        msg = f"[ERROR] Error al buscar o crear carpeta: {str(e)}"
        logger.error(msg)
        print(msg)
        return None