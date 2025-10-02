"""
Punto de entrada del microservicio MS_Procesos
"""
import os
import sys
import django
from django.core.management import call_command
from django.conf import settings
from interfaz import iniciar_interfaz
from utilidades_config import es_modo_ejecucion


def mostrar_banner():
    """Muestra el banner de inicio del microservicio"""
    print("\n" + "="*50, flush=True)
    print("   Microservicio MS_Procesos   ", flush=True)
    print("="*50 + "\n", flush=True)


def mostrar_informacion_inicio():
    """Muestra información sobre la configuración al iniciar"""
    modo = getattr(settings, 'MODO_EJECUCION', 'desarrollo')
    
    print(f"[INFO] Modo: {modo.upper()}", flush=True)
    
    # Mostrar versión en modo ejecución
    if es_modo_ejecucion():
        print("[INFO] Configuracion desde: config.json", flush=True)
    else:
        print("[INFO] Configuracion desde: settings.py", flush=True)


def ejecutar_listener():
    """Configura Django y ejecuta el listener de procesos"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ms_procesos.settings')
    
    try:
        django.setup()
        mostrar_banner()
        mostrar_informacion_inicio()
        
        call_command('process_listener')
        
    except KeyboardInterrupt:
        print("\n[INFO] Listener detenido\n", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}\n", flush=True)
        sys.exit(1)


if __name__ == '__main__':
    # Modo ejecución (.exe) con argumento --solo-servidor: ejecutar listener
    if es_modo_ejecucion() and '--solo-servidor' in sys.argv:
        ejecutar_listener()
    
    # Modo ejecución (.exe) sin argumentos: mostrar interfaz
    elif es_modo_ejecucion():
        iniciar_interfaz()
    
    # Modo desarrollo: ejecutar listener directamente
    else:
        ejecutar_listener()