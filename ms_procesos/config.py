from pathlib import Path
import environ

# BASE_DIR = Path(__file__).resolve().parent.parent
# env = environ.Env()
# environ.Env.read_env(BASE_DIR / ".env", overwrite=True)

# PATH_MAIN = env("PATH_MAIN", default="")
# PATH_CREDENTIALS = env("PATH_CREDENTIALS", default="")
# PATH_LOGS = env("PATH_LOGS", default="")

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Cargador de entorno
env = environ.Env()
environ.Env.read_env(ENV_PATH, overwrite=True)

def get_path_main():
    return env("PATH_MAIN", default="").strip()

def get_path_credentials():
    return env("PATH_CREDENTIALS", default="").strip()

def get_path_logs():
    return env("PATH_LOGS", default="").strip()

def reload_env():
    environ.Env.read_env(ENV_PATH, overwrite=True)