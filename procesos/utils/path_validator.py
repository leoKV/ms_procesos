import environ
from ms_procesos import config
from pathlib import Path

def solicitar_ruta_y_actualizar(nombre_var):
    while True:
        config.reload_env()  # Asegura que tenemos la última versión del .env
        valor_actual = environ.Env()(nombre_var, default="").strip()
        if valor_actual:
            return valor_actual
        nueva_ruta = input(f"[WARNING] La {nombre_var} está vacía. Por favor introduce una ruta válida: ").strip()
        if nueva_ruta:
            print(f"[INFO] La {nombre_var} ha sido actualizada correctamente: {nueva_ruta}")
            actualizar_env(config.ENV_PATH, nombre_var, nueva_ruta)
            config.reload_env()
            return nueva_ruta
        else:
            print("[WARNING] La ruta no puede estar vacía. Intenta de nuevo.")

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