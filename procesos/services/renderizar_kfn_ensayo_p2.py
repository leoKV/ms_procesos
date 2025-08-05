from decimal import Decimal
import os
import subprocess
from procesos.services.base_proceso import BaseProceso
from procesos.repositories.cancion_repository import CancionRepository
from procesos.repositories.proceso_repository import ProcesoRepository
from procesos.utils.drive_uploader import authenticate_drive, upload_file, download_file_from_folder
from ms_procesos import config
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)


class RenderizaKFNEnsayoP2(BaseProceso):
    def __init__(self, proceso, contexto_global):
        super().__init__(proceso)
        self.contexto = contexto_global
        self.repo = None
        self.proceso_repo = None
        self.maquina_id = None
        self.proceso_id = None
        self.cancion_id = None
        self.nombre_cancion = None
        self.artista = None
        self.cliente = None
        self.publicidad = None
        self.drive_key = None
        self.url_drive = None
        self.drive_final = None
        self.drive_ensayo = None
        self.inicia_digitacion = 0
        self.path_songs_kfn = None
        self.song_dir = None
        self.path_karaoke = None
    #-------- Método Principal---------
    def procesar(self):
        repo = CancionRepository()
        datos = repo.obtener_datos_renderizar_kfn(self.proceso['id'])
        if not datos:
            msg = "[ERROR] No se pudieron obtener datos para renderizar Karaoke."
            logger.error(msg)
            print(msg)
            return
        try:
            self._get_variables(datos)
            self._actualizar_estado_proceso(2,'')
            render_kfn = self._download_render_kfn_p1()
            if not render_kfn:
                msg = "[WARNING] El archivo Render KFN es requerido."
                raise EnvironmentError(msg)
            else:
                path_caratula_mp4 = self._caratula_mp4()
                if self.publicidad:
                    self._add_publicidad(render_kfn)
                self._karaoke_final(path_caratula_mp4)
                self._actualizar_estado_proceso(3,'')
        except Exception as e:
            msg = f"[ERROR] No se pudo renderizar: {str(e)})"
            logger.error(msg)
            print(msg)

    #-------- Métodos auxiliares---------
    # Prepara las variables necesarias.
    def _get_variables(self, datos):
        self.repo = CancionRepository()
        self.proceso_repo = ProcesoRepository()
        self.maquina_id = self.contexto['maquina_info'].maquina_id
        self.proceso_id = datos['proceso_id']
        self.cancion_id = datos['cancion_id']
        self.nombre_cancion = datos['nombre']
        self.artista = datos['artista']
        self.cliente = datos['cliente']
        self.publicidad = datos['publicidad']
        self.drive_key = datos['drive_key']
        self.url_drive = datos['url_drive']
        self.drive_final = datos['drive_final']
        self.drive_ensayo = datos['drive_ensayo']
        self.inicia_digitacion = datos['info_extra']
        self.path_songs_kfn = config.get_path_songs_kfn()
        self.song_dir = os.path.join(self.path_songs_kfn, self.drive_key)
        self.path_karaoke = os.path.join(self.song_dir, 'ensayo')
        
    # Actualiza los estados del proceso.
    def _actualizar_estado_proceso(self, estado, msg_error):
        self.proceso_repo.update_estado_proceso(proceso_id=self.proceso_id, cancion_id=self.cancion_id, estado_id=estado, maquina_id=self.maquina_id, msg_error=msg_error)
        msg = f"[INFO] Estado de proceso actualizado a estado: {estado}"
        logger.info(msg)
        print(msg)
        
    # Descarga el archivo KFN de Google Drive.
    def _download_render_kfn_p1(self):
        try:
            render_kfn = os.path.join(self.path_karaoke, "render_kfn_p1_ensayo.mp4")
            # Verificar si el archivo ya existe.
            if os.path.exists(render_kfn):
                msg = f"[INFO] Archivo Render KFN Encontrado: {render_kfn}"
                logger.info(msg)
                print(msg)
                return render_kfn
            # Si no existe, se descarga de Google Drive.
            os.makedirs(self.path_karaoke, exist_ok=True)
            drive_service = authenticate_drive()
            msg = f"[INFO] Descargando Archivo Render KFN de Google Drive: {self.drive_key}..."
            logger.info(msg)
            print(msg)
            download_render_kfn = download_file_from_folder(drive_service, "render_kfn_p1_ensayo.mp4", self.url_drive, os.path.join(self.path_karaoke, "render_kfn_p1_ensayo"))
            if not download_render_kfn:
                msg = "[ERROR] No se pudo descargar el archivo Render KFN de Google Drive."
                logger.error(msg)
                print(msg)
            return download_render_kfn
        except Exception as e:
            msg = f"[ERROR] No se pudo descargar el archivo Render KFN: {str(e)})"
            logger.error(msg)
            print(msg)

    def _caratula_mp4(self):
        try:
            path_caratula_mp4 = os.path.join(self.song_dir, "caratula.mp4")
            if os.path.exists(path_caratula_mp4):
                msg = f"[INFO] Carátula MP4 Encontrada: {path_caratula_mp4}"
                logger.info(msg)
                print(msg)
                return path_caratula_mp4
            path_caratula = os.path.join(self.song_dir, "caratula.png")
            if not os.path.exists(path_caratula):
                msg = f"[INFO] Descargando caratula.png de Google Drive: {self.drive_key}"
                logger.info(msg)
                print(msg)
                drive_service = authenticate_drive()
                download_caratula = download_file_from_folder(drive_service, "caratula.png", self.url_drive, os.path.join(self.song_dir, "caratula"))
                if not download_caratula:
                    msg = f"[ERROR] No se pudo descargar la caratula de Google Drive: {self.drive_key}"
                    logger.error(msg)
                    print(msg)
                    return download_caratula
            path_pub = config.get_path_publicidad()
            path_sin_audio = os.path.join(path_pub, "sin_audio.mp3")
            msg = "[INFO] Conviertiendo Carátula a MP4..."
            logger.info(msg)
            print(msg)
            subprocess.run([
                "ffmpeg",
                "-y",
                "-loop", "1",
                "-i", path_caratula,
                "-i", path_sin_audio,
                "-t", "4",
                "-r", "29.97",
                "-crf", "23",
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "320k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                path_caratula_mp4
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
            msg = f"[INFO] Carátula convertida a MP4: {path_caratula_mp4}"
            logger.info(msg)
            print(msg)
            return path_caratula_mp4
        except subprocess.CalledProcessError as e:
            msg = f"[ERROR] Error durante la conversión de carátula a MP4: {e}"
            logger.error(msg)
            print(msg)
        except Exception as e:
            msg = f"[ERROR] Fallo inesperado al convertir carátula a MP4: {e}"
            logger.error(msg)
            print(msg)

    def _add_publicidad(self, render_kfn):
        try:
            path_pub = config.get_path_publicidad()
            path_end_pub = os.path.join(path_pub, "end_pub.mp4")
            path_pub_out = os.path.join(self.path_karaoke, "render_kfn_p1_ensayo_pub.mp4")
            msg = "[INFO] Agregando Publicidad..."
            logger.info(msg)
            print(msg)
            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", render_kfn,
                "-i", path_end_pub,
                "-filter_complex", "[0:v] [0:a] [1:v] [1:a] concat=n=2:v=1:a=1 [v] [a]",
                "-map", "[v]",
                "-map", "[a]",
                "-strict", "-2",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-movflags", "+faststart",
                path_pub_out
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
            # Reemplazar el archivo original
            os.replace(path_pub_out, render_kfn)
            msg = "[INFO] Publicidad Agregada correctamente."
            logger.info(msg)
            print(msg)
        except subprocess.CalledProcessError as e:
            msg = f"[ERROR] Error al agregar publicidad: {e}"
            logger.error(msg)
            print(msg)
        except Exception as e:
            msg = f"[ERROR] Fallo inesperado al agregar publicidad: {e}"
            logger.error(msg)
            print(msg)

    def _karaoke_final(self, path_caratula_mp4):
        try:
            # Drive Ensayo
            path_render_kfn_p1 = os.path.join(self.path_karaoke, "render_kfn_p1_ensayo.mp4")
            nombre_archivo = f"{self.drive_key} - Ensayo.mp4"
            path_karaoke_final = os.path.join(self.path_karaoke, nombre_archivo)
            msg = "[INFO] Creando Karaoke Ensayo..."
            logger.info(msg)
            print(msg)
            if self.inicia_digitacion is not None and Decimal(self.inicia_digitacion) <= Decimal('10'):
                subprocess.run([
                    "ffmpeg",
                    "-y",
                    "-i", path_caratula_mp4,
                    "-i", path_render_kfn_p1,
                    "-filter_complex", "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]",
                    "-map", "[outv]",
                    "-map", "[outa]",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    path_karaoke_final
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            else:
                subprocess.run([
                    "ffmpeg",
                    "-y",
                    "-i", path_render_kfn_p1,
                    "-i", path_caratula_mp4,
                    "-filter_complex", "[0:v][1:v] overlay=0:0:enable='between(t,0,5)'",
                    "-c:a", "copy",
                    path_karaoke_final
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            # Subir Karaoke a Google Drive.
            if os.path.exists(path_karaoke_final):
                msg = "[INFO] Karaoke Ensayo creado correctamente."
                logger.info(msg)
                print(msg)
                #Drive Ensayo
                file_id = self._upload_mp4(path_karaoke_final, nombre_archivo, self.drive_ensayo)
                self.repo.new_url_drive(self.cancion_id, file_id, 5)
                msg = "[INFO] URL de Drive actualizada correctamente."
                logger.info(msg)
                print(msg)
        except subprocess.CalledProcessError as e:
            msg = f"[ERROR] Error al crear Karaoke Ensayo: {e}"
            logger.error(msg)
            print(msg)
        except Exception as e:
            msg = f"[ERROR] Fallo inesperado al crear Karaoke Ensayo: {e}"
            logger.error(msg)
            print(msg)

    def _upload_mp4(self, path_mp4, file_name, url_drive):
        try:
            drive_service = authenticate_drive()
            msg = "[INFO] Subiendo archivo a Google Drive..."
            logger.info(msg)
            print(msg)
            id_drive = upload_file(drive_service, path_mp4, file_name, url_drive)
            msg = "[INFO] Archivo Subido a Google Drive correctamente."
            logger.info(msg)
            print(msg)
            return id_drive
        except Exception as e:
            msg = f"[ERROR] Fallo inesperado al subir archivo a Google Drive: {e}"
            logger.error(msg)
            print(msg)