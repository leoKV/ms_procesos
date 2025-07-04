from ms_procesos import config
from pathlib import Path

def solicitar_ruta_y_actualizar(nombre_var, valor_actual):
    env_path = config.BASE_DIR / ".env"
    valor_actual_str = str(valor_actual).strip() if valor_actual is not None else ""
    if valor_actual_str:
        return valor_actual_str
    while True:
        nueva_ruta = input(f"[WARNING] La {nombre_var} está vacía. Por favor introduce una ruta válida: ").strip()
        if nueva_ruta:
            print(f"[INFO] La {nombre_var} ha sido actualizada correctamente: {nueva_ruta}")
            actualizar_env(env_path, nombre_var, nueva_ruta)
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
    config.PATH_MAIN = solicitar_ruta_y_actualizar("PATH_MAIN", config.PATH_MAIN)
    config.PATH_CREDENTIALS = solicitar_ruta_y_actualizar("PATH_CREDENTIALS", config.PATH_CREDENTIALS)
    config.PATH_LOGS = solicitar_ruta_y_actualizar("PATH_LOGS", config.PATH_LOGS)