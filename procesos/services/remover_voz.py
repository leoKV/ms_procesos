import os
import subprocess
from procesos.services.base_proceso import BaseProceso
from procesos.repositories.cancion_repository import CancionRepository
from procesos.repositories.proceso_repository import ProcesoRepository
import yt_dlp
from procesos.utils.drive_uploader import authenticate_drive, get_or_create_folder_by_name, upload_file, delete_drive_file, download_file_from_folder
import demucs.separate
import shutil
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

class RemoverVozProceso(BaseProceso):
    def __init__(self, proceso, contexto_global):
        super().__init__(proceso)
        self.contexto = contexto_global
    #-------- Método Principal---------
    def procesar(self):
        repo = CancionRepository()
        datos = repo.obtener_datos_remover_voz(self.proceso['id'])
        if not datos:
            logger.error("[ERROR] No se pudieron obtener datos para remover voz.")
            print("[ERROR] No se pudieron obtener datos para remover voz.")
            return
        try:
            self._get_variables(datos)
            self._actualizar_estado_proceso(2)
            output_path = self._descargar_cancion()
            output_path = self._recortar_audio(output_path)
            self._separar_voces(output_path)
            self._subir_archivos(output_path)
            self._limpiar_archivos_locales()
            self._actualizar_estado_proceso(3)
        except Exception as e:
            logger.error("[ERROR] No se pudo procesar: %s", str(e))
            print(f"[ERROR] No se pudo procesar: {str(e)}")
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
        self.modelo_demucs = self.proceso_repo.get_modelo_demucs()
        self.cancion_dir = os.path.join(self.songs_dir, str(self.drive_key))
        os.makedirs(self.cancion_dir, exist_ok=True)

    # Actualiza los estados del proceso.
    def _actualizar_estado_proceso(self, estado):
        self.proceso_repo.update_estado_proceso(proceso_id=self.proceso_id, cancion_id=self.cancion_id, estado_id=estado, maquina_id=self.maquina_id)
        logger.info("[INFO] Estado de proceso actualizado a estado: %s", estado)
        print(f"[INFO] Estado de proceso actualizado a estado: {estado}")
    
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
        url_completa = self.url_youtube if self.url_youtube.startswith("http") else f"https://www.youtube.com/watch?v={self.url_youtube}"
        logger.info("[INFO] Descargando: %s de Youtube...", self.nombre_cancion)
        print(f"[INFO] Descargado: {self.nombre_cancion} de Youtube...")
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
        
    # Descarga la canción de Google Drive con o sin recorte de audio.
    def _descarga_drive(self):
        logger.info("[INFO] Descargando: %s de Google Drive...", self.nombre_cancion)
        print(f"[INFO] Descargado: {self.nombre_cancion} de Google Drive...")
        downloaded_file = download_file_from_folder(self.drive_service, "main", self.folder_drive, os.path.join(self.cancion_dir, "main"))
        if not downloaded_file:
            logger.error("[ERROR] No se pudo descargar el archivo main de Google Drive.")
            print("[ERROR] No se pudo descargar el archivo main de Google Drive.")
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
        logger.info("[INFO] Recortando audio desde %s hasta %s", self.inicio, self.fin)
        print(f"[INFO] Recortando audio desde {self.inicio} hasta {self.fin}")
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
        logger.info("[INFO] Recorte completado y main.mp3 actualizado.")
        print("[INFO] Recorte completado y main.mp3 actualizado.")
        return updated_path

    # Separa las voces y la instrumental.
    def _separar_voces(self, output_path):
        cmd = ["--mp3", "--two-stems", "vocals", "-n", self.modelo_demucs, "--out", self.cancion_dir, output_path]
        # Ajustes específicos para mdx_extra
        if self.modelo_demucs == "mdx_extra":
            cmd.extend(["--segment", "10"])
        try:
            demucs.separate.main(cmd)
            logger.info("[INFO] Separación de Audio Completada.")
            print("[INFO] Separación de Audio Completada.")
        except Exception as e:
            logger.error("[ERROR] Error en separación de voces: %s", str(e))
            print(f"[ERROR] Error en separación de voces: {str(e)}")
            
    # Sube los archivos de audio main.mp3, vocals.mp3 y no_vocals.mp3 a Google Drive.
    def _subir_archivos(self, output_path):
        # Refresca la conexión a Google Drive.
        self.drive_service = authenticate_drive()
        # Verifica si hay que recrear la carpeta o si aún existe.
        self.folder_drive = get_or_create_folder_by_name(self.drive_service, self.drive_key, self.parent_dir, self.cancion_id)
        logger.info("[INFO] Subiendo audios a Google Drive....")
        print("[INFO] Subiendo audios a Google Drive....")
        try:
            upload_file(self.drive_service, output_path, "main.mp3", self.folder_drive)
            upload_file(self.drive_service, os.path.join(self.cancion_dir, self.modelo_demucs, "main", "vocals.mp3"), "vocals.mp3", self.folder_drive)
            upload_file(self.drive_service, os.path.join(self.cancion_dir, self.modelo_demucs, "main", "no_vocals.mp3"), "no_vocals.mp3", self.folder_drive)
            logger.info("[INFO] Archivos de Audio Subidos a Google Drive.")
            print("[INFO] Archivos de Audio Subidos a Google Drive.")
        except Exception as e:
            logger.error("[ERROR] Error al subir audios a Google Drive: %s", str(e))
            print(f"[ERROR] Error al subir audios a Google Drive: {str(e)}")

    # Elimina las carpetas que se generaron localmente.
    def _limpiar_archivos_locales(self):
        try:
            shutil.rmtree(self.cancion_dir)
            logger.info("[INFO] Archivos Locales Eliminados.")
            print("[INFO] Archivos Locales Eliminados.")
        except Exception as e:
            logger.error("[ERROR] No se pudieron eliminar los archivos locales: %s", str(e))
            print(f"[ERROR] No se pudieron eliminar los archivos locales: {str(e)}")

    # Manejo de errores.
    def _manejar_error(self):
        logger.info("[INFO] Manejando Errores....")
        print("[INFO] Manejando Errores....")
        self._limpiar_archivos_locales()
        self._actualizar_estado_proceso(1)