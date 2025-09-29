import os
import sys
import django
from django.core.management import call_command
from django.conf import settings
from interfaz import iniciar_interfaz

def mostrar_banner():
    """Muestra un banner con la información del microservicio"""
    print("\n" + "="*50, flush=True)
    print("   Microservicio MS_Procesos   ", flush=True)
    print("="*50 + "\n", flush=True)

def mostrar_informacion_modo():
    """Muestra información sobre el modo de ejecución actual"""
    execution_mode = getattr(settings, 'EXECUTION_MODE', 'desarrollo')
    db_config_valid = getattr(settings, 'DB_CONFIG_VALID', True)

    print(f"[INFO] Modo de ejecución: {execution_mode.upper()}", flush=True)

    if execution_mode == 'desarrollo':
        print("[INFO] Configuración: Usando settings.py", flush=True)
    else:
        print("[INFO] Configuración: Usando config.json", flush=True)

    if db_config_valid:
        print("[INFO] Base de datos: Configuración válida", flush=True)
    else:
        print("[ERROR] Base de datos: Configuración inválida", flush=True)

    print(flush=True)

def main():
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ms_procesos.settings')

    try:
        django.setup()
        mostrar_banner()
        mostrar_informacion_modo()
        print("Iniciando listener de procesos", flush=True)

        # Ejecutar el listener permanentemente
        call_command('process_listener')

    except KeyboardInterrupt:
        print("\n[INFO] Listener detenido por el usuario.", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error en la aplicación: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    # Si está empaquetado con PyInstaller y se especifica --solo-servidor, ejecutar listener
    if getattr(sys, 'frozen', False) and '--solo-servidor' in sys.argv:
        main()
    # Si está empaquetado con PyInstaller sin argumentos especiales, iniciar la interfaz
    elif getattr(sys, 'frozen', False):
        iniciar_interfaz()
    else:
        # En modo desarrollo, ejecutar el listener directamente
        main()