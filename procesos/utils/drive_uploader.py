from concurrent.futures import ThreadPoolExecutor
import io
import os
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
from procesos.repositories.cancion_repository import CancionRepository
from ms_procesos import config
from procesos.utils.print import _log_print
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
        msg = _log_print("ERROR",f"Error verificando existencia de archivo: {str(e)}")
        logger.error(msg)
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
        msg = _log_print("INFO",f"Archivo subido: {file_name}")
        logger.info(msg)
        return file.get("id")
    except HttpError as e:
        msg = _log_print("ERROR",f"Error subiendo archivo: {str(e)}")
        logger.error(msg)
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
                msg = _log_print("INFO",f"Descargando... {int(status.progress() * 100)}%")
                logger.info(msg)
    msg = _log_print("INFO",f"Descarga completada: {final_path}")
    logger.info(msg)
    return final_path

def download_all_files(song_key, dest_dir):
    try:
        service = authenticate_drive()
        # Paso 1: Obtener ID del folder padre (kia_songs)
        parent_folder_id = CancionRepository().get_parent_folder()
        if not parent_folder_id:
            msg = _log_print("ERROR","No se pudo obtener la carpeta principal 'kia_songs'.")
            logger.error(msg)
        # Paso 2: Buscar la carpeta cuyo nombre sea igual a la key
        query = f"'{parent_folder_id}' in parents and name = '{song_key}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()  # pylint: disable=no-member
        folders = response.get('files', [])
        if not folders:
            msg = _log_print("ERROR",f"No se encontró la carpeta con key {song_key} en Google Drive.")
            logger.error(msg)
        folder_id = folders[0]['id']
        # Paso 3: Obtener todos los archivos dentro de la carpeta
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name, modifiedTime)').execute() # pylint: disable=no-member
        files = response.get('files', [])
        if not files:
            msg = _log_print("WARNING",f"No se encontraron archivos en la carpeta {song_key} en Google Drive.")
            logger.info(msg)
        # Paso 4: Descargar todos los archivos
        with ThreadPoolExecutor(max_workers=10) as executor:
            for file in files:
                executor.submit(download_file, file, dest_dir)
        msg = _log_print("INFO",f"Archivos descargados para la key {song_key}")
        logger.info(msg)
    except HttpError as error:
        msg = _log_print("ERROR",f"Error al acceder a Google Drive: {error}")
        logger.error(msg)

def download_file(file, dest_dir):
    file_name = file['name']
    # Ignorar archivos Render.
    if file_name in ['render_kfn_p1.mp4', 'render_kfn_p1_ensayo.mp4']:
        return
    local_path = os.path.join(dest_dir, file_name)
    force_download = ['kara_fun.kfn', 'caratula.png']
    # Actualizar siempre el KFN y la carátula.
    if file_name not in force_download and os.path.exists(local_path):
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
        msg = _log_print("INFO",f"Archivo {file_name} descargado en: {local_path}")
        logger.info(msg)
    except Exception as e:
        msg = _log_print("ERROR",f"Error al descargar {file_name}, {str(e)}")
        logger.error(msg)

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
            msg = _log_print("INFO",f"Carpeta encontrada: {folders[0]['id']}")
            logger.info(msg)
            return folders[0]['id']
        else:
            # Si no existe, la recrea con el mismo nombre de la Key
            repo = CancionRepository()
            msg = _log_print("WARNING","Carpeta no encontrada, recreando carpeta...")
            logger.warning(msg)
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
            msg = _log_print("INFO","Carpeta recreada correctamente.")
            logger.info(msg)
            new_url_drive = folder['id']
            # Actualiza la url de la carpeta en la base de datos.
            repo.update_url_drive(cancion_id=cancion_id, new_url_drive=new_url_drive)
            return new_url_drive
    except HttpError as e:
        msg = _log_print("ERROR",f"Error al buscar o crear carpeta: {str(e)}")
        logger.error(msg)
        return None