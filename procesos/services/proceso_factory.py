from procesos.services.remover_voz import RemoverVozProceso

class ProcesoFactory:
    _handlers = {
        1: RemoverVozProceso,
        # 2: RenderizaKFNProceso,
        # 3: CrearHistoriaProceso,
        # 4: CrearDemo,
        # 5: Transcribir,
    }

    @staticmethod
    def get_handler(proceso, contexto_global=None):
        tipo = proceso["tipo_proceso_id"]
        handler_class = ProcesoFactory._handlers.get(tipo)

        if not handler_class:
            print(f"[WARN] Proceso tipo {tipo} no implementado todavía. Proceso ID={proceso['id']} se omite.")
            return None

        return handler_class(proceso, contexto_global)