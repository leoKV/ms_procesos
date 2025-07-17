from django.db import connections
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

class CancionRepository:
    # Obtiene la información necesaria para remover la voz de la canción.
    def obtener_datos_remover_voz(self, proceso_id):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.sps_remover_voz(%s)
                """,
                [proceso_id]
            )
            result = cursor.fetchone()

        if result:
            return {
                "proceso_id": result[0],
                "cancion_id": result[1],
                "nombre": result[2],
                "drive_key": result[3],
                "url_youtube": result[4],
                "folder_drive": result[5],
                "inicio": result[6],
                "fin": result[7],
            }
        else:
            logger.warning("[WARNING] No se encontro la información para el proceso con ID: %s", proceso_id)
            print(f"[WARNING] No se encontro la información para el proceso con ID: {proceso_id}")
            return None
    
    # Obtiene el folder padre en el que se van a guardar las canciones.
    def get_parent_folder(self):
        with connections['default'].cursor() as cursor:
            cursor.execute("select * from public.sps_kia_folder()")
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            logger.warning("[WARNING] No se encontro el link para la carpeta kia_songs")
            print("[WARNING] No se encontro el link para la carpeta kia_songs")
            return ''
    
    # Actualiza la url de la carpeta de drive para la canción.
    def update_url_drive(self, cancion_id, new_url_drive):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_url_drive(%s, %s)
                """,
                [cancion_id, new_url_drive]
            )