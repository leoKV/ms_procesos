from procesos.services.remover_voz import RemoverVozProceso
from procesos.services.descargar_cancion import DescargarCancion
from procesos.services.renderizar_kfn_p1 import RenderizaKFNP1
from procesos.services.renderizar_kfn_p2 import RenderizaKFNP2
from procesos.services.renderizar_kfn_ensayo_p1 import RenderizaKFNEnsayoP1
from procesos.services.renderizar_kfn_ensayo_p2 import RenderizaKFNEnsayoP2
from procesos.utils.print import _log_print

class ProcesoFactory:
    _handlers = {
        1: RemoverVozProceso,
        6: RenderizaKFNP1,
        7: RenderizaKFNP2,
        8: RenderizaKFNEnsayoP1,
        9: RenderizaKFNEnsayoP2,
        10: DescargarCancion
    }
    @staticmethod
    def get_handler(proceso, contexto_global=None):
        tipo = proceso["tipo_proceso_id"]
        handler_class = ProcesoFactory._handlers.get(tipo)
        if not handler_class:
            _log_print("WARNING",f"El tipo de proceso: {tipo} aún no se implementa.")
            return None
        return handler_class(proceso, contexto_global)