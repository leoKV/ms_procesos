import sys
import os
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path

# Constantes Windows para ocultar consola del subproceso
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

# Versión del microservicio
VERSION = "1.0.0"

def obtener_configuracion_bd():
    """
    Obtiene la configuración de BD desde config.json
    Retorna None si no está en modo ejecución o hay error
    """
    # Solo funciona en modo ejecución (empaquetado)
    if not getattr(sys, 'frozen', False):
        return None

    # Buscar config.json en la carpeta del ejecutable
    possible_paths = [
        Path.cwd() / "config.json",                    # Carpeta actual
        Path(sys.executable).parent / "config.json",   # Carpeta del .exe
    ]

    config_file = None
    for path in possible_paths:
        if path.exists():
            config_file = path
            break

    if not config_file:
        return None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Validar campos requeridos
        if not all(key in config for key in ["HOST", "PORT"]):
            return None

        return {
            "host": config["HOST"],
            "port": config["PORT"]
        }
    except Exception:
        return None

class InterfazMicroservicio:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        self.raiz.title("Microservicio Ms_Procesos")
        self.raiz.geometry("500x300")
        self.raiz.resizable(True, True)
        # Tema oscuro e icono
        self._aplicar_tema_oscuro()
        self._establecer_icono()

        self.proceso = None
        self.cola_salida = queue.Queue()
        self.hilo_lector = None
        self.esta_encendido = False

        # Variables para información de conexión y versión
        self.info_labels = {}
        self.config_anterior = None
        self.monitoreo_activo = False

        self._construir_ui()
        self._programar_refresco_logs()
        
        # Iniciar el microservicio automáticamente al abrir la aplicación
        self.raiz.after(1000, self._iniciar_automaticamente)

    def _construir_ui(self):
        marco_top = ttk.Frame(self.raiz, padding=(10, 10, 10, 5))
        marco_top.pack(fill=tk.X)

        self.var_estado = tk.BooleanVar(value=False)
        self.boton_switch = ttk.Checkbutton(
            marco_top,
            text="Apagado",
            variable=self.var_estado,
            command=self._toggle_microservicio,
            style='Switch.TCheckbutton'
        )
        self.boton_switch.pack(side=tk.LEFT)

        # Agregar información de conexión y versión en modo ejecución
        if getattr(sys, 'frozen', False):
            self._crear_labels_info(marco_top)

        # Area de logs con scrollbar
        marco_logs = ttk.Frame(self.raiz, padding=(10, 5, 10, 10))
        marco_logs.pack(fill=tk.BOTH, expand=True)

        self.texto = tk.Text(
            marco_logs,
            wrap=tk.NONE,
            state=tk.DISABLED,
            height=30,
            width=120,
            font=('Consolas', 10),
            bg='#2b2b2b',  # Fondo oscuro
            fg='#ffffff',  # Texto blanco
            insertbackground='#ffffff',  # Cursor visible
            selectbackground='#3a3a3a',
            selectforeground='#ffffff'
        )
        scroll_y = ttk.Scrollbar(marco_logs, orient=tk.VERTICAL, command=self.texto.yview)
        scroll_x = ttk.Scrollbar(marco_logs, orient=tk.HORIZONTAL, command=self.texto.xview)
        self.texto.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        # Empaquetar primero el scroll horizontal para reservar espacio en la parte inferior
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _crear_labels_info(self, parent_frame):
        """Crea los labels para mostrar información de conexión y versión"""
        # Frame para la información (parte derecha del marco superior)
        marco_info = ttk.Frame(parent_frame)
        marco_info.pack(side=tk.RIGHT, padx=(20, 0))

        # Label para versión
        lbl_version = ttk.Label(
            marco_info,
            text=f"Versión: {VERSION}",
            font=('Segoe UI', 9),
            foreground='#ffffff',
            background='#2b2b2b'
        )
        lbl_version.pack(anchor=tk.NE, pady=(0, 2))
        self.info_labels['version'] = lbl_version

        # Label para host
        lbl_host = ttk.Label(
            marco_info,
            text="Host: Cargando...",
            font=('Segoe UI', 9),
            foreground='#cccccc',
            background='#2b2b2b'
        )
        lbl_host.pack(anchor=tk.NE, pady=(0, 2))
        self.info_labels['host'] = lbl_host

        # Label para puerto
        lbl_port = ttk.Label(
            marco_info,
            text="Puerto: Cargando...",
            font=('Segoe UI', 9),
            foreground='#cccccc',
            background='#2b2b2b'
        )
        lbl_port.pack(anchor=tk.NE)
        self.info_labels['port'] = lbl_port

        # Actualizar información inicial
        self._actualizar_info_conexion()

    def _actualizar_info_conexion(self):
        """Actualiza la información de conexión desde config.json"""
        config_actual = obtener_configuracion_bd()

        # Si no hay configuración o no hay labels, salir
        if not config_actual or not self.info_labels:
            return

        # Verificar si la configuración ha cambiado
        if self.config_anterior == config_actual:
            return

        # Actualizar labels
        if 'host' in self.info_labels:
            self.info_labels['host'].config(text=f"Host: {config_actual['host']}")

        if 'port' in self.info_labels:
            self.info_labels['port'].config(text=f"Puerto: {config_actual['port']}")

        # Guardar configuración actual para comparar cambios
        self.config_anterior = config_actual.copy()

        # Programar próxima verificación en 2 segundos
        if not self.monitoreo_activo:
            self._iniciar_monitoreo_config()

    def _iniciar_monitoreo_config(self):
        """Inicia el monitoreo de cambios en config.json"""
        if self.monitoreo_activo:
            return

        self.monitoreo_activo = True
        self._programar_verificacion_config()

    def _programar_verificacion_config(self):
        """Programa la próxima verificación de config.json"""
        if self.raiz and self.raiz.winfo_exists():
            self._actualizar_info_conexion()
            self.raiz.after(2000, self._programar_verificacion_config)  # Verificar cada 2 segundos

    def _iniciar_automaticamente(self):
        """Inicia el microservicio automáticamente al abrir la aplicación"""
        if not self.esta_encendido:
            self.var_estado.set(True)
            self.encender_microservicio()
    
    def _toggle_microservicio(self):
        if self.var_estado.get():
            self.encender_microservicio()
        else:
            self.apagar_microservicio()

    def encender_microservicio(self):
        if self.esta_encendido:
            return
        try:
            cmd = self._obtener_comando_servidor()
            self._escribir_log("[INFO] Microservicio Iniciado\n")
            # Forzar salida sin buffer del subproceso para que los prints se vean en tiempo real
            entorno = os.environ.copy()
            entorno["PYTHONUNBUFFERED"] = "1"
            self.proceso = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW,
                env=entorno
            )
            self.esta_encendido = True
            self.boton_switch.config(text="Encendido")
            self.hilo_lector = threading.Thread(target=self._leer_salida_servidor, daemon=True)
            self.hilo_lector.start()
        except Exception as e:
            self._escribir_log(f"[ERROR] No se pudo iniciar el microservicio: {e}\n")
            self.var_estado.set(False)
            self.boton_switch.config(text="Apagado")
            self.esta_encendido = False

    def apagar_microservicio(self):
        if not self.esta_encendido:
            return
        try:
            self._escribir_log("[INFO] Microservicio Detenido\n")
            if self.proceso and self.proceso.poll() is None:
                self.proceso.terminate()
                try:
                    self.proceso.wait(timeout=5)
                except Exception:
                    self.proceso.kill()
            self.esta_encendido = False
            self.boton_switch.config(text="Apagado")
        except Exception as e:
            self._escribir_log(f"[ERROR] No se pudo detener: {e}\n")
        finally:
            self.proceso = None
            self.var_estado.set(False)

    def _obtener_comando_servidor(self):
        # En modo empaquetado (PyInstaller)
        if getattr(sys, 'frozen', False):
            # Usar el mismo ejecutable pero con argumentos específicos para modo servidor
            return [sys.executable, "--modo=servidor", "--solo-servidor"]
        else:
            # Desarrollo: usar el mismo intérprete para ejecutar main.py
            ruta_main = os.path.join(os.path.dirname(__file__), 'main.py')
            return [sys.executable, ruta_main, "--modo=servidor"]

    def _leer_salida_servidor(self):
        try:
            if not self.proceso or not self.proceso.stdout:
                return
            for linea in self.proceso.stdout:
                self.cola_salida.put(linea)
        except Exception as e:
            self.cola_salida.put(f"[ERROR lector] {e}\n")

    def _programar_refresco_logs(self):
        self._drenar_cola_logs()
        self.raiz.after(100, self._programar_refresco_logs)

    def _drenar_cola_logs(self):
        try:
            while True:
                linea = self.cola_salida.get_nowait()
                self._escribir_log(linea)
        except queue.Empty:
            pass

    def _escribir_log(self, texto: str):
        self.texto.configure(state=tk.NORMAL)
        self.texto.insert(tk.END, texto)
        self.texto.see(tk.END)
        # Limitar a máximo 1000 líneas en pantalla
        try:
            total_lineas = int(self.texto.index('end-1c').split('.')[0])
            if total_lineas > 1000:
                # Borrar las líneas más antiguas dejando solo las últimas 1000
                inicio_borrado = f"1.0"
                fin_borrado = f"{total_lineas - 1000}.0"
                self.texto.delete(inicio_borrado, fin_borrado)
        except Exception:
            pass
        self.texto.configure(state=tk.DISABLED)

    def _aplicar_tema_oscuro(self):
        try:
            estilo = ttk.Style(self.raiz)
            try:
                estilo.theme_use('clam')
            except tk.TclError:
                pass
            color_bg = '#2b2b2b'
            color_fg = '#ffffff'
            # Fondo raíz
            self.raiz.configure(bg=color_bg)
            # Estilos base
            estilo.configure('TFrame', background=color_bg)
            estilo.configure('TLabel', background=color_bg, foreground=color_fg)
            estilo.configure('TScrollbar', background=color_bg)
            # Switch
            estilo.configure('Switch.TCheckbutton',
                             font=('Segoe UI', 11, 'bold'),
                             background=color_bg,
                             foreground=color_fg,
                             padding=(10, 6))
            estilo.map('Switch.TCheckbutton',
                       foreground=[('disabled', '#aaaaaa'), ('!disabled', color_fg)],
                       background=[('active', '#3a3a3a')])
        except Exception:
            pass

    def _establecer_icono(self):
        """Establece el icono kia.ico con PyInstaller."""
        try:
            if getattr(sys, 'frozen', False):
                base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                ruta_icono = os.path.join(base, 'kia.ico')
            else:
                ruta_icono = os.path.join(os.path.dirname(__file__), 'kia.ico')
            if os.path.exists(ruta_icono):
                self.raiz.iconbitmap(ruta_icono)
        except Exception:
            # En plataformas no Windows, iconbitmap con .ico puede no aplicar
            pass

    def cerrar_interfaz(self):
        # Al cerrar la ventana, apaga el microservicio
        try:
            self.apagar_microservicio()
        finally:
            self.raiz.destroy()


def iniciar_interfaz():
    raiz = tk.Tk()
    raiz.configure(bg='#2b2b2b')  # Fondo negro
    app = InterfazMicroservicio(raiz)
    raiz.protocol("WM_DELETE_WINDOW", app.cerrar_interfaz)
    raiz.mainloop()


if __name__ == '__main__':
    iniciar_interfaz()

