import os
import importlib.metadata
import json
import subprocess
import sys
import urllib.request
from procesos.services.base_proceso import BaseProceso
from procesos.repositories.cancion_repository import CancionRepository
from procesos.repositories.proceso_repository import ProcesoRepository
import yt_dlp
from procesos.utils.drive_uploader import authenticate_drive, get_or_create_folder_by_name, upload_file, delete_drive_file, download_file_from_folder
import shutil
from procesos.utils.print import _log_print
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

class DescargarCancion(BaseProceso):
    def __init__(self, proceso, contexto_global):
        super().__init__(proceso)
        self.contexto = contexto_global
        self.repo = None
        self.proceso_repo = None
        self.drive_service = None
        self.maquina_id = None
        self.songs_dir = None
        self.parent_dir = None
        self.proceso_id = None
        self.cancion_id = None
        self.nombre_cancion = None
        self.drive_key = None
        self.url_youtube = None
        self.folder_drive = None
        self.inicio = None
        self.fin = None
        self.cancion_dir = None
        self.drive_ext = None
    
    #-------- Método Principal---------
    def procesar(self):
        repo = CancionRepository()
        datos = repo.obtener_datos_remover_voz(self.proceso['id'])
        if not datos:
            msg = _log_print("ERROR","No se obtuvieron datos para descargar la canción.")
            logger.error(msg)
            return
        try:
            self._get_variables(datos)
            self._actualizar_estado_proceso(2,'')
            output_path = self._descargar_cancion()
            output_path = self._recortar_audio(output_path)
            self._subir_main(output_path)
            self._insertar_proceso_remover_voz()
            self._actualizar_estado_proceso(3,'')
            self._actualizar_porcentaje(10)
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo procesar: {str(e)}")
            logger.error(msg)
            self._manejar_error()

    #-------- Métodos auxiliares---------
    # Prepara las variables necesarias.
    def _get_variables(self, datos):
        self.repo = CancionRepository()
        self.proceso_repo = ProcesoRepository()
        self.drive_service = authenticate_drive()
        self.maquina_id = self.contexto['maquina_info'].maquina_id
        self.songs_dir = self.contexto['songs_dir']
        self.parent_dir = self.contexto['parent_folder_id']
        self.proceso_id = datos['proceso_id']
        self.cancion_id = datos['cancion_id']
        self.nombre_cancion = datos['nombre']
        self.drive_key = datos['drive_key']
        self.url_youtube = datos['url_youtube']
        self.folder_drive = datos['folder_drive']
        self.inicio = datos['inicio']
        self.fin = datos['fin']
        self.cancion_dir = os.path.join(self.songs_dir, str(self.drive_key))
        os.makedirs(self.cancion_dir, exist_ok=True)
    
    # Actualiza los estados del proceso.
    def _actualizar_estado_proceso(self, estado, msg_error):
        self.proceso_repo.update_estado_proceso(proceso_id=self.proceso_id, cancion_id=self.cancion_id, estado_id=estado, maquina_id=self.maquina_id, msg_error=msg_error)
        msg = _log_print("INFO",f"Estado de proceso actualizado a estado: {estado}")
        logger.info(msg)
    
    # Actualiza el porcentaje de avance.
    def _actualizar_porcentaje(self, porcentaje):
        self.proceso_repo.update_porcentaje_avance(cancion_id= self.cancion_id, porcentaje=porcentaje)
        msg = _log_print("INFO",f"Porcentaje de Avance Actualizado a: {porcentaje}%")
        logger.info(msg)

    # Descarga la canción
    def _descargar_cancion(self):
        if self.url_youtube:
            # Si hay Url de Youtube descarga la canción de Youtube.
            return self._descarga_youtube()
        else:
            # Si No hay Url de Youtube descarga la canción de Google Drive.
            return self._descarga_drive()
        
    # Descarga la canción de Youtube con o sin recorte de audio.
    def _descarga_youtube(self):
        self._update_yt_dlp()
        url_completa = self.url_youtube if self.url_youtube.startswith("http") else f"https://www.youtube.com/watch?v={self.url_youtube}"
        msg = _log_print("INFO",f"Descargando: {self.nombre_cancion} de Youtube...")
        logger.info(msg)
        temp_path = os.path.join(self.cancion_dir, "main_youtube")
        final_path = os.path.join(self.cancion_dir, "main")
        output_template = temp_path if (self.inicio != "00:00:00" or self.fin != "00:00:00") else final_path
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,
        }
        output_template += ".mp3"
        final_path += ".mp3"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_completa])
        if self.inicio != "00:00:00" or self.fin != "00:00:00":
            subprocess.run(["ffmpeg", "-y", "-i", output_template, final_path], check=True)
            return final_path
        else:
            return final_path
    
    def _update_yt_dlp(self):
        try:
            # Versión instalada actualmente
            current_version = importlib.metadata.version("yt-dlp")
            # Última versión en PyPI
            with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json") as r:
                latest_version = json.load(r)["info"]["version"]
            if current_version == latest_version:
                return
            msg = _log_print("INFO",f"Actualizando yt-dlp de {current_version} a {latest_version}...")
            logger.info(msg)
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([sys.executable, "-m", "pip", "freeze", "requirements.txt"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            msg = _log_print("INFO","yt-dlp actualizado correctamente.")
            logger.info(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo verificar o actualizar yt-dlp: {e}")
            logger.error(msg)
    
    # Descarga la canción de Google Drive con o sin recorte de audio.
    def _descarga_drive(self):
        msg = _log_print("INFO",f"Descargando: {self.nombre_cancion} de Google Drive...")
        logger.info(msg)
        downloaded_file = download_file_from_folder(self.drive_service, "main.mp3", self.folder_drive, os.path.join(self.cancion_dir, "main"))
        if not downloaded_file:
            msg = _log_print("ERROR","No se pudo descargar el archivo main de Google Drive.")
            logger.error(msg)
        ext = os.path.splitext(downloaded_file)[1].lower()
        if ext != ".mp3":
            mp3_path = os.path.join(self.cancion_dir, "main.mp3")
            subprocess.run(["ffmpeg", "-y", "-i", downloaded_file, mp3_path], check=True)
            delete_drive_file(self.drive_service, self.folder_drive, "main.")
            self.drive_ext = ext
            return mp3_path
        else:
            self.drive_ext = ext
            return downloaded_file
    
    # Realiza el recorte del audio y remplaza el audio.
    def _recortar_audio(self, output_path):
        if self.inicio == "00:00:00" and self.fin == "00:00:00":
            return output_path
        if not self.url_youtube and self.drive_ext == '.mp3':
            delete_drive_file(self.drive_service, self.folder_drive, "main.")
        msg = _log_print("INFO",f"Recortando audio desde {self.inicio} hasta {self.fin}")
        logger.info(msg)
        trimmed_path = os.path.join(self.cancion_dir, "main_trimmed.mp3")
        cmd = ["ffmpeg", "-y", "-i", output_path]
        if self.inicio != "00:00:00":
            cmd += ["-ss", self.inicio]
        if self.fin != "00:00:00":
            cmd += ["-to", self.fin]
        cmd += ["-c", "copy", trimmed_path]
        subprocess.run(cmd, check=True)
        os.remove(output_path)
        os.rename(trimmed_path, os.path.join(self.cancion_dir, "main.mp3"))
        updated_path = os.path.join(self.cancion_dir, "main.mp3")
        msg = _log_print("INFO","Recorte completado y main.mp3 actualizado.")
        logger.info(msg)
        return updated_path
    
    # Subir audio main a Google Drive.
    def _subir_main(self, output_path):
        # Refresca la conexión a Google Drive.
        self.drive_service = authenticate_drive()
        # Verifica si hay que recrear la carpeta o si aún existe.
        self.folder_drive = get_or_create_folder_by_name(self.drive_service, self.drive_key, self.parent_dir, self.cancion_id)
        msg = _log_print("INFO","Subiendo Main.mp3 a Google Drive....")
        logger.info(msg)
        try:
            upload_file(self.drive_service, output_path, "main.mp3", self.folder_drive)
            msg = _log_print("INFO","Archivo Subido Correctamente.")
            logger.info(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"Error al subir Main.mp3 a Google Drive: {str(e)}")
            logger.error(msg)

    # Insertar proceso para Remover Voz.
    def _insertar_proceso_remover_voz(self):
        try:
            self.proceso_repo.insertar_nuevo_proceso(tipo_proceso=1, maquina_id=self.maquina_id, cancion_id= self.cancion_id, info_extra='')
            msg = _log_print("INFO","Proceso: Remover Voz - Insertado correctamente.")
            logger.info(msg)
        except Exception as e:
            msg =_log_print("ERROR",f"Fallo inesperado al Insertar el nuevo proceso: {e}")
            logger.error(msg)
    
    # Manejo de errores.
    def _manejar_error(self):
        msg = _log_print("INFO","Manejando Errores....")
        logger.info(msg)
        self._limpiar_archivos_locales()
        self._actualizar_estado_proceso(1,'')

    # Elimina las carpetas que se generaron localmente.
    def _limpiar_archivos_locales(self):
        try:
            shutil.rmtree(self.cancion_dir)
            msg = _log_print("INFO","Archivos Locales Eliminados.")
            logger.info(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudieron eliminar los archivos locales: {str(e)}")
            logger.error(msg)