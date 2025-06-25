import platform
import uuid
import getpass
from django.db import connections

class MaquinaInfoService:
    def __init__(self):
        self.maquina_id = None
        self.mac = self.get_mac_address()
        self.nombre_pc = self.get_computer_name()
        self.usuario = self.get_current_user()
        self.maquina_info = {}

    # Obtener la dirección MAC de la PC
    def get_mac_address(self):
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return "-".join([mac[e:e+2] for e in range(0, 12, 2)]).upper()
    # Obtener el nombre de la PC
    def get_computer_name(self):
        return platform.node()
    # Obtener el usuario de la PC
    def get_current_user(self):
        return getpass.getuser()

    def cargar_info_maquina(self):
        #self._print_debug()
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT * FROM public.sps_maquina_id(%s, %s, %s)
            """, [self.mac, self.nombre_pc, self.usuario])
            rows = cursor.fetchall()

        if not rows:
            raise RuntimeError("No se pudo obtener la información de la máquina desde la base de datos.")
        self.maquina_id = rows[0][0]

        for row in rows:
            tipo_proceso_id = row[1]
            procesa = row[2]
            numero_ejecuta = row[3]
            self.maquina_info[tipo_proceso_id] = {
                "procesa": procesa,
                "numero_ejecuta": numero_ejecuta
            }

    def puede_procesar(self, tipo_proceso_id):
        info = self.maquina_info.get(tipo_proceso_id)
        return info is not None and info["procesa"]

    def max_ejecuciones(self, tipo_proceso_id):
        info = self.maquina_info.get(tipo_proceso_id)
        if info:
            return info["numero_ejecuta"]
        return 0
    
    def _print_debug(self):
        print(f"[DEBUG] MAC detectada: {self.mac}")
        print(f"[DEBUG] Nombre PC: {self.nombre_pc}")
        print(f"[DEBUG] Usuario: {self.usuario}")