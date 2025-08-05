# Microservicio Procesos

El objetivo de este microservicio es recibir y ejecutar los nuevos procesos que se insertan en la base de datos. 

## 🚀 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado lo siguiente:

- Python 3.8 o superior``
- pip (Gestor de paquetes de Python)
- Virtualenv (recomendado)
- Karafun Studio - Español
- Credenciales de Google Drive
- AutoHotKey 1.1

## 🛠️ Configuración del Entorno

1. **Clona el repositorio**:

   ```bash
   git clone https://github.com/leoKV/ms_procesos.git
   cd ms_procesos

2. **Agregar Credenciales**:
   Es necesario aseguarse de que las credenciales de Google Drive se encuentran presentes en la raíz del proyecto:

   <img width="240" height="240" alt="image" src="https://github.com/user-attachments/assets/5ccb2367-7dec-4c1d-bbce-fae3a9d46596" />

4. **Instalar dependencias**:

   ```bash
   pip install -r requirements.txt
   
5. **Verificar conexión a base de datos en el archivo settings.py**:

   <img width="264" height="233" alt="image" src="https://github.com/user-attachments/assets/4efb1766-7ad4-4861-9bbe-c2564db69f1a" />

    <img width="639" height="294" alt="image" src="https://github.com/user-attachments/assets/aa0f4548-e8d8-4372-9c80-792010eb7c95" />
    
7. **Verificar las rutas en el archivo .env**:
   <img width="1367" height="596" alt="image" src="https://github.com/user-attachments/assets/41d457f2-f1e7-4a15-be05-2ed085cd3f84" />

- PATH_SONGS_KFN: Hace referencia a la carpeta donde se guardan las carpetas de cada canción con su key, las cuales contienen los archivos importantes
  de cada una de ellas, tales como: main.mp3, no_vocals.mp3, caratula.png etc. Esta carpeta corresponde al microservicio: ms_karafun.
- PATH_IMG_FONDO: Hace referencia a la carpeta en la que estarán las imagenes de Fondo para crear el karafun, tales como: Fondo Karaoke IA.jpg, Fondo Karaoke IA_sin_logo.jpg
  o cualquier otra.
- PATH_AUTO_HOT_KEY: Hace referencia a la ruta directa al ejecutable .exe de AutoHotKey.
- PATH_RENDER_KFN: Hace referencia a la ruta directa del archivo render_kfn.ahk, el cual es un script diseñado para ejecutar la renderización de un karaoke con ayuda
  de AutoHotKey. Este archivo ya se incluye en las utilidades del proyecto.
- PATH_PUBLICIDAD: Hace referencia a la carpeta en la cual se encuentran los archivos complementarios para crear un karaoke, tales como: end_pub.mp4 y sin_audio.mp3.

8. **Correr el proyecto**:
   ```bash
   python manage.py process_listener
