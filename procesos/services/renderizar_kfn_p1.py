import os
from pathlib import Path
import re
import platform
import subprocess
import zipfile
from procesos.services.base_proceso import BaseProceso
from procesos.repositories.cancion_repository import CancionRepository
from procesos.repositories.proceso_repository import ProcesoRepository
from procesos.utils.KaraokeFUNForm import KaraokeFunForm
from procesos.utils.drive_uploader import authenticate_drive, upload_file, download_file_from_folder, download_all_files
from ms_procesos import config
from procesos.utils.KFNDumper import KFNDumper
from procesos.utils.print import _log_print
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

class RenderizaKFNP1(BaseProceso):
    def __init__(self, proceso, contexto_global):
        super().__init__(proceso)
        self.contexto = contexto_global
        self.entries_kfn = []
        self.song_ini_text = ""
        self.inicia_digitacion = 0
        self.repo = None
        self.proceso_repo = None
        self.maquina_id = None
        self.proceso_id = None
        self.cancion_id = None
        self.drive_key = None
        self.url_drive = None
        self.path_songs_kfn = None
        self.song_dir = None
        self.archivos_kfn = None
    #-------- Método Principal---------
    def procesar(self):
        repo = CancionRepository()
        datos = repo.obtener_datos_renderizar_kfn(self.proceso['id'])
        if not datos:
            msg = _log_print("ERROR","No se pudieron obtener datos para renderizar karafun.")
            logger.error(msg)
            return
        try:
            self._running_on_windows()
            self._get_variables(datos)
            self._actualizar_estado_proceso(2,'')
            self._download_files()
            archivo_kfn = self._search_kfn()
            if not archivo_kfn:
                msg = _log_print("WARNING","El archivo KFN es requerido.")
                raise EnvironmentError(msg)
            else:
                song_ini = self._get_song_ini(archivo_kfn)
                digitacion = self._validar_digitacion(song_ini)
                if digitacion:
                    self._verificar_recursos()
                    self._kfn_karaoke()
                    self._actualizar_estado_proceso(3,'')
                    self._actualizar_porcentaje(80)
                else:
                    self._actualizar_estado_proceso(4,'No se ha iniciado la digitación en el proyecto KFN.')
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo renderizar: {str(e)}")
            logger.error(msg)
    #-------- Métodos auxiliares---------
    # Verificar el sistema operativo
    def _running_on_windows(self):
        so = platform.system()
        if so != "Windows":
            msg = _log_print("WARNING","Este proceso solo puede ejecutarse en Windows.")
            logger.warning(msg)
            raise EnvironmentError(msg)
        msg = _log_print("INFO","Sistema operativo compatible (Windows).")
        logger.info(msg)
    
    # Prepara las variables necesarias.
    def _get_variables(self, datos):
        self.repo = CancionRepository()
        self.proceso_repo = ProcesoRepository()
        self.maquina_id = self.contexto['maquina_info'].maquina_id
        self.proceso_id = datos['proceso_id']
        self.cancion_id = datos['cancion_id']
        self.drive_key = datos['drive_key']
        self.url_drive = datos['url_drive']
        self.path_songs_kfn = config.get_path_songs_kfn()
        self.song_dir = os.path.join(self.path_songs_kfn, self.drive_key)
        self.archivos_kfn = {}

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

    # Descargar todos los archivos de la carpeta de Google Drive.
    def _download_files(self):
        try:
            msg = _log_print("INFO",f"Descargando archivos para la carpeta: {self.drive_key}")
            logger.info(msg)
            os.makedirs(self.song_dir, exist_ok=True)
            download_all_files(self.drive_key, self.song_dir)
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudieron descargar los archivos de Google Drive: {str(e)}")
            logger.error(msg)

    # Buscar el archivo KFN.
    def _search_kfn(self):
        try:
            archivo_kfn = os.path.join(self.song_dir, "kara_fun.kfn")
            # Buscar KFN en carpeta local.
            if os.path.exists(archivo_kfn):
                msg = _log_print("INFO",f"Archivo KFN Encontrado: {archivo_kfn}")
                logger.info(msg)
                return archivo_kfn
            # Si no existe, intenta volver a descargarlo de Google Drive.
            else:
                os.makedirs(self.song_dir, exist_ok=True)
                drive_service = authenticate_drive()
                msg = _log_print("INFO",f"Descargando Archivo KFN de Google Drive: {self.drive_key}...")
                logger.info(msg)
                download_kfn = download_file_from_folder(drive_service, "kara_fun.kfn", self.url_drive, os.path.join(self.song_dir, "kara_fun"))
                if not download_kfn:
                    msg = _log_print("ERROR","No se pudo descargar el archivo KFN de Google Drive.")
                    logger.error(msg)
                return download_kfn
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo descargar el archivo Karafun: {str(e)}")
            logger.error(msg)
    
    def _get_song_ini(self, archivo_kfn):
        try:
            kfn = KFNDumper(archivo_kfn)
            self.entries_kfn = kfn.list()
            song_entry = next((e for e in self.entries_kfn if e.filename.lower() == "song.ini"), None)
            if song_entry:
                song_bytes = kfn.extract(song_entry)
                self.song_ini_text = song_bytes.decode("utf-8", errors="ignore")
                return self.song_ini_text
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo extraer el archivo Song.ini: {str(e)}")
            logger.error(msg)
    
    def _validar_digitacion(self, song_ini):
        try:
            porcentaje_minimo = self.proceso_repo.get_porcentaje_kfn()
            # 1. Contar palabras en los Text
            total_palabras = 0
            for linea in song_ini.splitlines():
                if linea.startswith("Text"):
                    _, texto = linea.split("=", 1)
                    palabras = [p for p in texto.strip().split() if p]
                    total_palabras += len(palabras)
            # 2. Contar digitaciones en los Sync
            total_sync = 0
            for linea in song_ini.splitlines():
                if linea.startswith("Sync"):
                    _, valores = linea.split("=", 1)
                    # Contar los números separados por coma
                    syncs = [s for s in valores.strip().split(",") if s]
                    total_sync += len(syncs)
            match = re.search(r'Sync0=([\d,]+)', song_ini)
            if match:
                valores = match.group(1).split(',')
                self.inicia_digitacion = int(valores[0]) / 100.0
            # 3. Calcular el porcentaje
            if total_palabras == 0:
                msg = _log_print("WARNING","No se encontro la letra de la canción.")
                logger.warning(msg)
                return False
            if total_sync == 0:
                msg = _log_print("WARNING","Aún no se ha realizado la digitación.")
                logger.warning(msg)
                return False
            porcentaje_real = (total_sync / total_palabras) * 100
            msg = _log_print("INFO",f"Digitaciones: {total_sync}, Palabras: {total_palabras}, Porcentaje: {porcentaje_real:.2f}%")
            logger.info(msg)
            # 4. Validar porcentaje mínimo requerido
            if porcentaje_real >= porcentaje_minimo:
                msg = _log_print("INFO","La digitación cumple con el mínimo requerido.")
                logger.info(msg)
                self._actualizar_porcentaje(60)
                return True
            else:
                self._actualizar_estado_proceso(4,'La digitación no cumple con el mínimo requerido.')
                msg = _log_print("WARNING","La digitación no cumple con el mínimo requerido.")
                logger.warning(msg)
                return False
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo validar el porcentaje de la digitación: {str(e)}")
            logger.error(msg)
            return False
    
    def _kfn_karaoke(self):
        try:
            self._mapear_archivos_kfn()
            # Elegir archivo de audio
            nuevo_audio = None
            if "sin_voz" in self.archivos_kfn:
                nuevo_audio = self.archivos_kfn["sin_voz"]
            elif "no_vocals" in self.archivos_kfn:
                nuevo_audio = self.archivos_kfn["no_vocals"]
            if nuevo_audio:
                lineas = self.song_ini_text.splitlines()
                nuevas_lineas = []
                for linea in lineas:
                    if linea.startswith("Source="):
                        partes = linea.split(",")
                        if len(partes) >= 3:
                            partes[-1] = nuevo_audio
                            linea = ",".join(partes)
                    nuevas_lineas.append(linea)
                self.song_ini_text = "\n".join(nuevas_lineas)
                path_nuevo_audio = os.path.join(self.song_dir, nuevo_audio)
                k_name = "kara_fun.kfn"
                kfun = KaraokeFunForm(path_nuevo_audio, self.archivos_kfn, self.song_ini_text, k_name, 1)
                result = kfun.genera_archivo_kfun()
                if result[0] == "0":
                    msg = f"[INFO] {result[1]}"
                    logger.info(msg)
                    print(msg)
                    path_kfn = result[2]
                    folder_kfn = os.path.dirname(path_kfn)
                    path_render_avi = os.path.join(folder_kfn, "kara_fun.avi")
                    path_mp4 = os.path.join(folder_kfn, "render_kfn_p1.mp4")
                    self._renderizar_karaoke(path_kfn, path_render_avi)
                    self._comprimir_avi(path_render_avi, path_mp4)
                    self._upload_mp4(path_mp4,'render_kfn_p1.mp4', self.url_drive)
                    self._insertar_proceso_p2()
                else:
                    msg = _log_print("ERROR","No se pudo reconstruir el archivo Karafun.")
                    logger.error(msg)
            else:
                msg = _log_print("WARNING",f"No se encontro el audio: {nuevo_audio}")
                logger.info(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudo renderizar el Karaoke: {str(e)}")
            logger.error(msg)

    def _mapear_archivos_kfn(self):
        for e in self.entries_kfn:
            nombre = e.filename
            clave = (
                nombre.lower()
                .replace(".mp3", "")
                .replace(".jpg", "")
                .replace(".png","")
                .replace(" ", "_")
            )
            self.archivos_kfn[clave] = nombre

    def _renderizar_karaoke(self, path_kfn, path_avi):
        try:
            # Ruta de AutoHotKey
            ahk_exe = config.get_path_auto_hot_key()
            # Ruta de Script AHK
            script_ahk = config.get_path_render_kfn()
            if not os.path.exists(ahk_exe):
                msg = _log_print("ERROR"," AutoHotKey no esta instalado o la ruta es incorrecta.")
                logger.error(msg)
                return
            if not os.path.exists(script_ahk):
                msg = _log_print("ERROR","Archivo render_kfn.ahk no existe o la ruta es incorrecta.")
                logger.error(msg)
                return
            # Comando completo
            comando = [ahk_exe, script_ahk, path_kfn, path_avi]
            msg = _log_print("INFO",f"Ejecutando AHK: {comando}")
            logger.info(msg)
            subprocess.run(comando, check=True)
            msg = _log_print("INFO",f"Renderización Finalizada {path_avi}")
            logger.info(msg)
        except subprocess.CalledProcessError as e:
            msg = _log_print("ERROR",f"Error durante la renderización: {e}")
            logger.error(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"Fallo inesperado en renderización: {e}")
            logger.error(msg)

    def _comprimir_avi(self, path_avi, path_mp4):
        try:
            msg = _log_print("INFO",f"Comprimiendo archivo {path_avi}")
            logger.info(msg)
            subprocess.run(["ffmpeg", "-y", "-i", path_avi, "-c:v", "libx264", "-crf", "28", "-preset", "veryslow", "-c:a", "aac", "-b:a", "128k", path_mp4], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            msg = _log_print("INFO",f"Compresión a MP4 Finalizada {path_mp4}")
            logger.info(msg)
            if os.path.exists(path_mp4):
                os.remove(path_avi)
                msg = _log_print("INFO","Archivo AVI eliminado.")
                logger.info(msg)
            else:
                msg = _log_print("WARNING","No se creo el archivo MP4 para eliminar el AVI.")
                logger.warning(msg)
        except subprocess.CalledProcessError as e:
            msg = _log_print("ERROR",f"Error durante la compresión a MP4: {e}")
            logger.error(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"Fallo inesperado en la compresión a MP4: {e}")
            logger.error(msg)

    def _upload_mp4(self, path_mp4, file_name, url_drive):
        try:
            drive_service = authenticate_drive()
            msg = _log_print("INFO","Subiendo archivo a Google Drive...")
            logger.info(msg)
            id_drive = upload_file(drive_service, path_mp4, file_name, url_drive)
            msg = _log_print("INFO","Archivo Subido a Google Drive correctamente.")
            logger.info(msg)
            return id_drive
        except Exception as e:
            msg = _log_print("ERROR",f"Fallo inesperado al subir archivo a Google Drive: {e}")
            logger.error(msg)

    def _insertar_proceso_p2(self):
        try:
            self.proceso_repo.insertar_nuevo_proceso(tipo_proceso=7, maquina_id=self.maquina_id, cancion_id= self.cancion_id, info_extra = str(self.inicia_digitacion))
            msg = _log_print("INFO","Proceso: Renderizar KFN Parte 2 - Insertado correctamente.")
            logger.info(msg)
        except Exception as e:
            msg =_log_print("ERROR",f"Fallo inesperado al Insertar el nuevo proceso: {e}")
            logger.error(msg)
    
    def _verificar_recursos(self):
        try:
            path_fondos = config.get_path_img_fondo()
            path_publicidad = config.get_path_publicidad()
            # Si ambas rutas ya existen, no se nada.
            if os.path.exists(path_fondos) and os.path.exists(path_publicidad):
                return True
            # Ruta del ZIP.
            path_zip = os.path.join(os.getcwd(), "resources", "resources.zip")
            path_d = Path(config.get_path_img_fondo())
            path_destino = path_d.parent
            if not os.path.exists(path_zip):
                msg = _log_print("ERROR",f"No se encontró el archivo: {path_zip}")
                logger.error(msg)
                return False
            # Extraer ZIP
            msg = _log_print("INFO",f"Extrayendo {path_zip} a {path_destino}...")
            logger.info(msg)
            with zipfile.ZipFile(path_zip, 'r') as zip_ref:
                zip_ref.extractall(path_destino)
            # Eliminar ZIP después de extraer
            os.remove(path_zip)
            msg = _log_print("INFO","Extracción completada y archivo ZIP eliminado.")
            logger.info(msg)
            return True
        except Exception as e:
            msg = _log_print("ERROR",f"Fallo al verificar/extraer recursos: {e}")
            logger.error(msg)
            return False