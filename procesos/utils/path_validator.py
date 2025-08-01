import environ
from ms_procesos import config
import re
from pathlib import Path

def solicitar_ruta_y_actualizar(nombre_var):
    while True:
        config.reload_env()
        valor_actual = environ.Env()(nombre_var, default="").strip()
        if valor_actual and ruta_valida(valor_actual):
            return valor_actual
        else:
            if valor_actual:
                print(f"[ERROR] La ruta actual en {nombre_var} no es válida o no se pudo crear: {valor_actual}")
        
        nueva_ruta = input(f"[WARNING] La {nombre_var} está vacía o es inválida. Introduce una ruta válida: ").strip()
        if nueva_ruta and ruta_valida(nueva_ruta):
            print(f"[INFO] La {nombre_var} ha sido actualizada correctamente: {nueva_ruta}")
            actualizar_env(config.ENV_PATH, nombre_var, nueva_ruta)
            config.reload_env()
            return nueva_ruta
        else:
            print("[WARNING] La ruta no es válida o no se pudo crear. Intenta de nuevo.")

def ruta_valida(ruta: str) -> bool:
    patron_windows = r"^[a-zA-Z]:\\(?:[^\\/:*?\"<>|\r\n]+\\?)*$"
    if not re.match(patron_windows, ruta):
        return False
    try:
        path = Path(ruta)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo crear la ruta '{ruta}': {e}")
        return False

def actualizar_env(env_path, key, new_value):
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={new_value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={new_value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def validar_y_actualizar_paths():
    solicitar_ruta_y_actualizar("PATH_MAIN")
    solicitar_ruta_y_actualizar("PATH_CREDENTIALS")
    solicitar_ruta_y_actualizar("PATH_LOGS")
    solicitar_ruta_y_actualizar("PATH_SONGS_KFN")