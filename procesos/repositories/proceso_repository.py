from django.db import connections
import logging
from procesos.utils import logs
logger = logging.getLogger(__name__)

class ProcesoRepository:
    # Obtiene los nuevos procesos con estado: Agregado.
    def get_nuevos_procesos(self):
        with connections['default'].cursor() as cursor:
            cursor.execute("select * from public.sps_nuevos_procesos()")
            procesos = cursor.fetchall()
        return [
            {
                "id": row[0],
                "tipo_proceso_id": row[1],
                "estado_proceso_id": row[2]
            }
            for row in procesos
        ]
    # Obtiene el intervalo de tiempo en que se tiene que comprobar si hay nuevos procesos.
    def get_tiempo_ejecucion(self):
        with connections['default'].cursor() as cursor:
            cursor.execute("select * from public.sps_tiempo_ejecucion()")
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return 5
        
    def get_modelo_demucs(self):
        with connections['default'].cursor()  as cursor:
            cursor.execute("select * from public.sps_modelo_demucs()")
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return 'mdx_extra'
    
    def get_porcentaje_kfn(self):
        with connections['default'].cursor()  as cursor:
            cursor.execute("select * from public.sps_porcentaje_kfn()")
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return 80
    
    # Actualiza el estado del proceso en sus distintas fases.
    def update_estado_proceso(self, proceso_id, cancion_id, estado_id, maquina_id, msg_error):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_estado_proceso(%s, %s, %s, %s, %s)
                """,
                [proceso_id, cancion_id, estado_id, maquina_id, msg_error]
            )

    def insertar_nuevo_proceso(self, tipo_proceso, maquina_id, cancion_id, info_extra):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spi_nuevo_proceso(%s, %s, %s, %s)
                """,
                [tipo_proceso, maquina_id, cancion_id, info_extra]
            )