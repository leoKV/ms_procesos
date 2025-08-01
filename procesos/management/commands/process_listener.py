# Validación de PATHS
from procesos.utils.path_validator import validar_y_actualizar_paths
validar_y_actualizar_paths()
# Importaciones
from procesos.repositories.cancion_repository import CancionRepository
from procesos.utils import logs
from procesos.services.maquina_info_service import MaquinaInfoService
from procesos.services.proceso_factory import ProcesoFactory
from procesos.repositories.proceso_repository import ProcesoRepository
from procesos.utils.ffmpeg_installer import ensure_ffmpeg_installed
from ms_procesos import config
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
import os
import time
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Escucha y procesa nuevos procesos'
    def handle(self, *args, **options):
        logger.info("[INFO] Iniciando el listener de procesos...")
        print("[INFO] Iniciando el listener de procesos...")
        # Comprobar instalación de la herramienta FFmpeg
        try:
            logger.info("[INFO] Verificando instalación FFmpeg...")
            print("[INFO] Verificando instalación FFmpeg...")
            ensure_ffmpeg_installed()
            logger.info("[INFO] FFmpeg está instalado correctamente.")
            print("[INFO] FFmpeg está instalado correctamente.")
        except Exception as e:
            logger.error("[ERROR] No se pudo instalar/verificar FFmpeg %s", str(e))
            print(f"[ERROR] No se pudo instalar/verificar FFmpeg: {str(e)}")
            return   
         
        maquina_service = MaquinaInfoService()
        proceso_repository = ProcesoRepository()
        maquina_service.cargar_info_maquina()

        while True:
            # Obtener tiempo de ejecución dinámico
            tiempo_espera = proceso_repository.get_tiempo_ejecucion()
            if tiempo_espera <= 0:
                tiempo_espera = 5
            # Obtener procesos nuevos
            procesos = proceso_repository.get_nuevos_procesos()
            if procesos:
                logger.info("[INFO] %s Nuevo(s) procesos detectados.", len(procesos))
                print(f"[INFO] {len(procesos)} Nuevo(s) procesos detectados.")
                # Agrupar por tipo
                procesos_por_tipo = {}
                for proceso in procesos:
                    tipo = proceso['tipo_proceso_id']
                    if tipo not in procesos_por_tipo:
                        procesos_por_tipo[tipo] = []
                    procesos_por_tipo[tipo].append(proceso)

                # Procesar cada tipo
                for tipo, procesos_tipo in procesos_por_tipo.items():
                    if not maquina_service.puede_procesar(tipo):
                        for p in procesos_tipo:
                            logger.info("[INFO] La maquina no puede ejecutar procesos de tipo %s. El proceso con ID=%s será ignorado", tipo, p['id'])
                            print(f"[INFO] La maquina no puede ejecutar procesos de tipo {tipo}. El proceso con ID={p['id']} será ignorado.")
                        continue

                    max_ejecuciones = maquina_service.max_ejecuciones(tipo)
                    logger.info("[INFO] Procesando tipo=%s con max_ejecuciones=%s, procesos detectados=%s", tipo, max_ejecuciones, len(procesos_tipo))
                    print(f"[INFO] Procesando tipo={tipo} con max_ejecuciones={max_ejecuciones}, procesos detectados={len(procesos_tipo)}")
                    
                    # Crear contexto global por tipo de proceso
                    contexto_global = None
                    if tipo == 1:
                        contexto_global = self._crear_contexto_remover_voz()
                    if tipo == 6 or 7 or 8 or 9:
                        contexto_global = self._crear_contexto_renderizar_kfn()
                    # Procesar en lotes
                    for i in range(0, len(procesos_tipo), max_ejecuciones):
                        batch = procesos_tipo[i:i + max_ejecuciones]
                        batch_ids = [p['id'] for p in batch]
                        logger.info("[INFO] Procesando lote: %s", batch_ids)
                        print(f"[INFO] Procesando lote: {batch_ids}")
                        with ThreadPoolExecutor(max_workers=max_ejecuciones) as executor:
                            futures = [executor.submit(self.procesar_proceso, p, contexto_global) for p in batch]
                            for future in as_completed(futures):
                                future.result()
                        logger.info("[INFO] Lote Procesado Correctamente.")
                        print("[INFO] Lote Procesado Correctamente.")
            else:
                logger.info("[INFO] No hay nuevos procesos.")
                print("[INFO] No hay nuevos procesos.")
            logger.info("[INFO] Esperando %s segundos antes de la siguiente verificación...", tiempo_espera)
            print(f"[INFO] Esperando {tiempo_espera} segundos antes de la siguiente verificación...\n")
            time.sleep(tiempo_espera)

    def procesar_proceso(self, proceso, contexto_global=None):
        try:
            handler = ProcesoFactory.get_handler(proceso, contexto_global)
            if handler:
                handler.procesar()
        except Exception as e:
            logger.error("[ERROR] Error al procesar proceso ID=%s: %s", proceso.id, str(e))
            print(f"[ERROR] Error al procesar proceso ID={proceso.id}: {str(e)}")

    # Contexto - Proceso 1 - Remover Voz.
    def _crear_contexto_remover_voz(self):
        songs_dir = config.get_path_main()
        os.makedirs(songs_dir, exist_ok=True)
        parent_folder_id = CancionRepository().get_parent_folder()
        maquina_info = MaquinaInfoService()
        maquina_info.cargar_info_maquina()
        contexto = {
            "songs_dir": songs_dir,
            "parent_folder_id": parent_folder_id,
            "maquina_info": maquina_info,
        }
        return contexto
    
    # Contexto - Proceso 6,7,8 y 9 - Renderizar Karaoke/Ensayo Parte 1 y 2.
    def _crear_contexto_renderizar_kfn(self):
        maquina_info = MaquinaInfoService()
        maquina_info.cargar_info_maquina()
        contexto = {"maquina_info": maquina_info}
        return contexto
