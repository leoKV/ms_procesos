import os
import sys
import django
from django.core.management import call_command

def mostrar_banner():
    print("\n" + "="*50, flush=True)
    print("   Microservicio MS_Procesos   ", flush=True)
    print("="*50 + "\n", flush=True)

def main():
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ms_procesos.settings')

    try:
        django.setup()
        mostrar_banner()
        print("Iniciando listener de procesos...", flush=True)

        # Ejecutar el listener permanentemente
        call_command('process_listener')

    except KeyboardInterrupt:
        print("\n[INFO] Listener detenido por el usuario.", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error en la aplicación: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()