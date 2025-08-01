from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Cargador de entorno
env = environ.Env()
environ.Env.read_env(ENV_PATH, overwrite=True)

# PATHS PRINCIPALES
def get_path_main():
    return env("PATH_MAIN", default="").strip()

def get_path_credentials():
    return env("PATH_CREDENTIALS", default="").strip()

def get_path_logs():
    return env("PATH_LOGS", default="").strip()

# PATHS MS_KARAFUN
def get_path_songs_kfn():
    return env("PATH_SONGS_KFN", default="").strip()

def get_path_img_fondo():
    return env("PATH_IMG_FONDO", default="").strip()

# PATHS RENDER
def get_path_auto_hot_key():
    return env("PATH_AUTO_HOT_KEY", default="").strip()

def get_path_render_kfn():
    return env("PATH_RENDER_KFN", default="").strip()

# PATHS PUBLICIDAD
def get_path_publicidad():
    return env("PATH_PUBLICIDAD", default="").strip()

def reload_env():
    environ.Env.read_env(ENV_PATH, overwrite=True)