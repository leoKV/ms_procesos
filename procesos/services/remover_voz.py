import os
from procesos.services.base_proceso import BaseProceso
from procesos.repositories.cancion_repository import CancionRepository
from procesos.repositories.proceso_repository import ProcesoRepository
from procesos.utils.drive_uploader import authenticate_drive, get_or_create_folder_by_name, upload_file, download_file_from_folder
import demucs.separate
import shutil
from procesos.utils.print import _log_print
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

class RemoverVozProceso(BaseProceso):
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
        self.folder_drive = None
        self.modelo_demucs = None
        self.cancion_dir = None

    #-------- Método Principal---------
    def procesar(self):
        repo = CancionRepository()
        datos = repo.obtener_datos_remover_voz(self.proceso['id'])
        if not datos:
            msg = _log_print("ERROR","No se obtuvieron datos para remover voz.")
            logger.error(msg)
            return
        try:
            self._get_variables(datos)
            self._actualizar_estado_proceso(2,'')
            result = self._separar_voces()
            if result:
                self._subir_archivos()
                self._limpiar_archivos_locales()
                self._actualizar_estado_proceso(3,'')
                self._actualizar_porcentaje(20)
            else:
                self._limpiar_archivos_locales()
                self._actualizar_estado_proceso(4,'No se encontró el archivo main.mp3')
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
        self.folder_drive = datos['folder_drive']
        self.modelo_demucs = self.proceso_repo.get_modelo_demucs()
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

    # Separa las voces y la instrumental.
    def _separar_voces(self) -> bool:
        main_path = os.path.join(self.cancion_dir, 'main.mp3')
        if not os.path.isfile(main_path):
            main_path = download_file_from_folder(self.drive_service, "main.mp3", self.folder_drive, os.path.join(self.cancion_dir, "main"))
            if not main_path:
                msg = _log_print("ERROR",f"No se encontró el Audio main.mp3 en local y en Drive: {self.nombre_cancion}")
                logger.error(msg)
                return False
        os.path.join(self.songs_dir, str(self.drive_key))
        cmd = ["--mp3", "--two-stems", "vocals", "-n", self.modelo_demucs, "--out", self.cancion_dir, main_path]
        # Ajustes específicos para mdx_extra
        if self.modelo_demucs == "mdx_extra":
            cmd.extend(["--segment", "10"])
        try:
            msg = _log_print("INFO",f"Comenzando Separación de Audio para: {self.nombre_cancion}")
            logger.info(msg)
            demucs.separate.main(cmd)
            msg = _log_print("INFO","Separación de Audio Completada.")
            logger.info(msg)
            return True
        except Exception as e:
            msg = _log_print("ERROR",f"Error en Separación de Audio: {str(e)}")
            logger.error(msg)
            return False

    # Sube los archivos de audio vocals.mp3 y no_vocals.mp3 a Google Drive.
    def _subir_archivos(self):
        # Refresca la conexión a Google Drive.
        self.drive_service = authenticate_drive()
        # Verifica si hay que recrear la carpeta o si aún existe.
        self.folder_drive = get_or_create_folder_by_name(self.drive_service, self.drive_key, self.parent_dir, self.cancion_id)
        msg = _log_print("INFO","Subiendo audios a Google Drive....")
        logger.info(msg)
        try:
            upload_file(self.drive_service, os.path.join(self.cancion_dir, self.modelo_demucs, "main", "vocals.mp3"), "vocals.mp3", self.folder_drive)
            upload_file(self.drive_service, os.path.join(self.cancion_dir, self.modelo_demucs, "main", "no_vocals.mp3"), "no_vocals.mp3", self.folder_drive)
            msg = _log_print("INFO","Archivos de Audio Subidos a Google Drive.")
            logger.info(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"Error al subir Audios a Google Drive: {str(e)}")
            logger.error(msg)

    # Elimina las carpetas que se generaron localmente.
    def _limpiar_archivos_locales(self):
        try:
            shutil.rmtree(self.cancion_dir)
            msg = _log_print("INFO","Archivos Locales Eliminados.")
            logger.info(msg)
        except Exception as e:
            msg = _log_print("ERROR",f"No se pudieron eliminar los archivos locales: {str(e)}")
            logger.error(msg)

    # Manejo de errores.
    def _manejar_error(self):
        msg = _log_print("INFO","Manejando Errores....")
        logger.info(msg)
        self._limpiar_archivos_locales()
        self._actualizar_estado_proceso(1,'')