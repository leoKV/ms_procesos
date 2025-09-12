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
                "estado_proceso_id": row[2],
                "nombre_cancion":row[3],
                "artista":row[4]
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
        
    # Obtiene el modelo demucs que hay que utilizar.
    def get_modelo_demucs(self):
        with connections['default'].cursor()  as cursor:
            cursor.execute("select * from public.sps_modelo_demucs()")
            result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return 'mdx_extra'
        
    # Obtiene el porcentaje minimo de Digitación.
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
    # Actualiza el porcentaje de avance de la canción.
    def update_porcentaje_avance(self, cancion_id, porcentaje):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_porcentaje_avance(%s, %s)
                """,
                [ cancion_id, porcentaje]
            )
    
    # Inserta un nuevo proceso para Renderización: Parte 1 y Parte 2.
    def insertar_nuevo_proceso(self, tipo_proceso, maquina_id, cancion_id, info_extra):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spi_nuevo_proceso(%s, %s, %s, %s)
                """,
                [tipo_proceso, maquina_id, cancion_id, info_extra]
            )