from datetime import datetime
import os
import tempfile
from utilidades_config import es_modo_ejecucion

# Archivo temporal para logs cuando sea necesario
_log_file = None

def _obtener_archivo_log():
    """Obtiene el archivo de log temporal para escritura adicional"""
    global _log_file
    if _log_file is None and es_modo_ejecucion():
        try:
            # Crear archivo temporal en el directorio temporal del sistema
            temp_dir = tempfile.gettempdir()
            log_path = os.path.join(temp_dir, 'ms_procesos_server.log')
            _log_file = open(log_path, 'a', encoding='utf-8')
        except Exception:
            _log_file = None
    return _log_file

def _escribir_en_archivo(formatted_message):
    """Escribe el mensaje formateado en el archivo de log si está disponible"""
    archivo = _obtener_archivo_log()
    if archivo:
        try:
            archivo.write(formatted_message + '\n')
            archivo.flush()  # Forzar escritura inmediata
        except Exception:
            pass  # Ignorar errores de escritura en archivo

# Imprime los mensajes en consola con un formato estándar.
def _log_print(level:str, message:str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{level}] {timestamp} {message}"
    print(formatted, flush=True)  # flush=True para salida inmediata
    _escribir_en_archivo(formatted)
    return formatted

def _cerrar_archivo_log():
    """Cierra el archivo de log temporal"""
    global _log_file
    if _log_file:
        try:
            _log_file.close()
        except Exception:
            pass
        finally:
            _log_file = None