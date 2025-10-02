"""
Utilidades para cargar y validar la configuración del microservicio
"""
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Importar BASE_DIR del config del proyecto
try:
    from ms_procesos.config import BASE_DIR
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent


def es_modo_ejecucion() -> bool:
    """Verifica si la aplicación está ejecutándose como .exe empaquetado"""
    return getattr(sys, 'frozen', False)


def obtener_rutas_config() -> list[Path]:
    """Retorna las rutas posibles donde buscar config.json"""
    rutas = [
        BASE_DIR / "config.json",
        Path.cwd() / "config.json",
        Path(__file__).parent / "config.json"
    ]
    
    if es_modo_ejecucion():
        rutas.insert(2, Path(sys.executable).parent / "config.json")
    
    return rutas


def cargar_config_json() -> Optional[Dict[str, Any]]:
    """
    Carga el archivo config.json desde las ubicaciones posibles.
    Retorna None si no está en modo ejecución o no se encuentra el archivo.
    """
    if not es_modo_ejecucion():
        return None
    
    for ruta in obtener_rutas_config():
        if ruta.exists():
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                if not isinstance(config, dict):
                    continue
                
                return config
            except (json.JSONDecodeError, IOError, KeyError, TypeError):
                continue
    
    return None


def obtener_configuracion_bd() -> Optional[Dict[str, str]]:
    """
    Obtiene la configuración de base de datos desde config.json.
    Retorna None si no está disponible o es inválida.
    """
    config = cargar_config_json()
    if not config:
        return None
    
    database_config = config.get("database")
    if not isinstance(database_config, dict):
        return None
    
    host = database_config.get("HOST")
    port = database_config.get("PORT")
    
    if not host or not port:
        return None
    
    return {
        "host": str(host),
        "port": str(port)
    }


def obtener_configuracion_version() -> Optional[Dict[str, str]]:
    """
    Obtiene la configuración de versión desde config.json.
    Retorna None si no está disponible o es inválida.
    """
    config = cargar_config_json()
    if not config:
        return None
    
    microservicio_config = config.get("microservicio")
    if not isinstance(microservicio_config, dict):
        return None
    
    version = microservicio_config.get("version")
    if not version:
        return None
    
    return {
        "version": str(version),
        "nombre": str(microservicio_config.get("nombre", "ms_procesos"))
    }


def obtener_config_bd_completa() -> Optional[Dict[str, Any]]:
    """
    Obtiene la configuración completa de base de datos para Django.
    Retorna None si no está disponible o es inválida.
    """
    config = cargar_config_json()
    if not config:
        return None
    
    db_config = config.get("database")
    if not isinstance(db_config, dict):
        return None
    
    campos_requeridos = ["ENGINE", "NAME", "USER", "PASSWORD", "HOST", "PORT"]
    if not all(campo in db_config for campo in campos_requeridos):
        return None
    
    return db_config