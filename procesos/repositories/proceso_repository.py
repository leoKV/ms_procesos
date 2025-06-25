from django.db import connections

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
    # Actualiza el estado del proceso en sus distintas fases.
    def update_estado_proceso(self, proceso_id, cancion_id, estado_id, maquina_id):
        with connections['default'].cursor() as cursor:
            cursor.execute(
                """
                select * from public.spu_estado_proceso(%s, %s, %s, %s)
                """,
                [proceso_id, cancion_id, estado_id, maquina_id]
            )