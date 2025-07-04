import environ
import os
from ms_procesos import config
from pathlib import Path

def solicitar_ruta_y_actualizar(nombre_var):
    while True:
        config.reload_env()
        valor_actual = environ.Env()(nombre_var, default="").strip()
        if valor_actual and validar_o_crear_directorio(valor_actual):
            return valor_actual

        print(f"[WARNING] La {nombre_var} está vacía o es inválida.")
        while True:
            nueva_ruta = input(f"Por favor introduce una ruta válida y absoluta para {nombre_var}: ").strip()
            if not nueva_ruta:
                print("[WARNING] La ruta no puede estar vacía. Intenta de nuevo.")
                continue
            if validar_o_crear_directorio(nueva_ruta):
                print(f"[INFO] La {nombre_var} ha sido actualizada correctamente: {nueva_ruta}")
                actualizar_env(config.ENV_PATH, nombre_var, nueva_ruta)
                config.reload_env()
                return nueva_ruta
            else:
                print("[ERROR] La ruta es inválida, no existe el drive o no se puede crear el directorio. Intenta de nuevo.")

def validar_o_crear_directorio(ruta):
    try:
        path_obj = Path(ruta).expanduser().resolve()
        # Verificar que sea absoluta
        if not path_obj.is_absolute():
            print("[DEBUG] La ruta no es absoluta.")
            return False
        # Verificar que existe el drive (en Windows)
        if os.name == 'nt':
            drive = path_obj.drive
            if not drive or not os.path.exists(drive + "\\"):
                print(f"[DEBUG] El drive '{drive}' no existe.")
                return False
        else:
            # En Linux, asegurarse que la raíz existe (no hay mucho más que verificar)
            if not Path("/").exists():
                print("[DEBUG] La raíz no existe... esto no debería pasar.")
                return False
        # Intentar crear el directorio
        path_obj.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"[DEBUG] Error al crear el directorio: {e}")
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