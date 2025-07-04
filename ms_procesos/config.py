from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=True)

PATH_MAIN = env("PATH_MAIN", default="")
PATH_CREDENTIALS = env("PATH_CREDENTIALS", default="")
PATH_LOGS = env("PATH_LOGS", default="")