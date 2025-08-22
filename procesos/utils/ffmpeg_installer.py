import os
import platform
import subprocess
import stat
import requests
import zipfile
import tarfile
from pathlib import Path
from ms_procesos.config import env

class FFmpegInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.ffmpeg_dir = Path(__file__).parent / "ffmpeg"
        self.bin_path = None
    
    def _get_download_url(self):
        urls = {
            'windows': {
                'x86_64': env("FFMPEG_WINDOWS_X86_64", default=""),
                'amd64': env("FFMPEG_WINDOWS_AMD_64", default="")
            },
            'linux': {
                'x86_64': env("FFMPEG_LINUX_X86_64", default=""),
                'amd64': env("FFMPEG_LINUX_AMD_64", default="")
            },
            'darwin': {
                'x86_64': env("FFMPEG_DARWIN_X86_64", default=""),
                'arm64': env("FFMPEG_DARWIN_ARM64", default="")
            }
        }
        return urls.get(self.system, {}).get(self.arch)
    
    def _download_and_extract(self, url):
        self.ffmpeg_dir.mkdir(exist_ok=True)
        download_path = self.ffmpeg_dir / "ffmpeg_download"
        # Descargar
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        # Extraer
        if url.endswith('.zip'):
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(self.ffmpeg_dir)
        elif url.endswith('.tar.xz'):
            with tarfile.open(download_path, 'r:xz') as tar_ref:
                tar_ref.extractall(self.ffmpeg_dir)
        # Eliminar archivo descargado
        download_path.unlink()
    
    def _find_ffmpeg_binary(self):
        for root, dirs, files in os.walk(self.ffmpeg_dir):
            for file in files:
                if file.lower() in ('ffmpeg', 'ffmpeg.exe'):
                    found_path = Path(root) / file
                    # Hacer ejecutable en Unix
                    if self.system in ['linux', 'darwin']:
                        st = os.stat(found_path)
                        os.chmod(found_path, st.st_mode | stat.S_IEXEC)
                    return found_path
        return None
    
    def is_installed(self):
        local_ffmpeg = self._find_ffmpeg_binary()
        if local_ffmpeg and local_ffmpeg.exists():
            self.bin_path = local_ffmpeg
            # Agregar al PATH por si no estaba
            bin_dir = str(self.bin_path.parent)
            os.environ['PATH'] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
            return True
        return False
        
    def install(self):
        if self.is_installed():
            return True
        url = self._get_download_url()
        if not url:
            raise Exception(f"No se encontró versión de FFmpeg para {self.system}/{self.arch}")
        self._download_and_extract(url)
        self.bin_path = self._find_ffmpeg_binary()
        if not self.bin_path:
            raise Exception("No se pudo encontrar el binario FFmpeg después de la extracción")
        # Agregar al PATH
        bin_dir = str(self.bin_path.parent)
        os.environ['PATH'] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        return True
    
def ensure_ffmpeg_installed():
    installer = FFmpegInstaller()
    return installer.install()