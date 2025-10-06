"""
Interfaz gráfica del microservicio MS_Procesos
"""
import sys
import os
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from utilidades_config import (
    obtener_configuracion_bd,
    obtener_configuracion_version,
    es_modo_ejecucion
)

# Constante para ocultar consola en Windows
CREAR_SIN_VENTANA = 0x08000000 if os.name == 'nt' else 0


class InterfazMicroservicio:
    def __init__(self, raiz: tk.Tk):
        self.raiz = raiz
        self.raiz.title("Microservicio Ms_Procesos")
        self.raiz.geometry("500x300")
        self.raiz.resizable(True, True)
        
        self._aplicar_tema_oscuro()
        self._establecer_icono()
        
        # Estado del microservicio
        self.proceso = None
        self.cola_salida = queue.Queue()
        self.esta_encendido = False
        
        # Monitoreo de configuración
        self.config_anterior = None
        self.info_labels = {}
        
        self._construir_ui()
        self._programar_refresco_logs()
        self.raiz.after(1000, self._iniciar_automaticamente)
    
    def _construir_ui(self):
        """Construye la interfaz de usuario"""
        # Marco superior con botón de encendido/apagado
        marco_top = ttk.Frame(self.raiz, padding=(10, 10, 10, 5))
        marco_top.pack(fill=tk.X)
        
        self.var_estado = tk.BooleanVar(value=False)
        self.boton_switch = ttk.Checkbutton(
            marco_top,
            text="Apagado",
            variable=self.var_estado,
            command=self._alternar_microservicio,
            style='Switch.TCheckbutton'
        )
        self.boton_switch.pack(side=tk.LEFT)
        
        # Marco inferior con información (antes del área de logs)
        if es_modo_ejecucion():
            marco_inferior = ttk.Frame(self.raiz, padding=(10, 5, 10, 10))
            marco_inferior.pack(fill=tk.X, side=tk.BOTTOM)
            self._crear_labels_info(marco_inferior)
        
        # Área de logs con scrollbars
        marco_logs = ttk.Frame(self.raiz, padding=(10, 5, 10, 10))
        marco_logs.pack(fill=tk.BOTH, expand=True)
        
        self.texto = tk.Text(
            marco_logs,
            wrap=tk.NONE,
            state=tk.DISABLED,
            height=30,
            width=120,
            font=('Consolas', 10),
            bg='#092912',
            fg='#ffffff',
            insertbackground='#ffffff',
            selectbackground='#3b3b3b',
            selectforeground='#ffffff'
        )
        
        scroll_y = ttk.Scrollbar(marco_logs, orient=tk.VERTICAL, command=self.texto.yview)
        scroll_x = ttk.Scrollbar(marco_logs, orient=tk.HORIZONTAL, command=self.texto.xview)
        self.texto.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _crear_labels_info(self, marco_padre):
        """Crea los labels para mostrar información de conexión y versión"""
        marco_info = ttk.Frame(marco_padre)
        marco_info.pack(side=tk.RIGHT, padx=(20, 0))
        
        config_version = obtener_configuracion_version()
        version_texto = config_version.get("version", "1.0.0") if config_version else "1.0.0"
        
        self.info_labels['info'] = ttk.Label(
            marco_info,
            text=f"Versión: {version_texto} | Host: Cargando... | Puerto: Cargando...",
            font=('Segoe UI', 9),
            foreground='#ffffff',
            background='#092912'
        )
        self.info_labels['info'].pack(side=tk.LEFT)
        
        self._actualizar_info_conexion()
        self._programar_monitoreo_config()
    
    def _actualizar_info_conexion(self):
        """Actualiza la información de conexión y versión desde config.json"""
        config_bd = obtener_configuracion_bd()
        config_version = obtener_configuracion_version()
        
        if not config_bd or not self.info_labels:
            return
        
        # Solo actualizar si cambió la configuración
        if self.config_anterior == config_bd:
            return
        
        version_texto = config_version.get('version', '1.0.0') if config_version else '1.0.0'
        texto_completo = f"Versión: {version_texto} | Host: {config_bd['host']} | Puerto: {config_bd['port']}"
        
        if 'info' in self.info_labels:
            self.info_labels['info'].config(text=texto_completo)
        
        self.config_anterior = config_bd.copy()
    
    def _programar_monitoreo_config(self):
        """Programa la verificación periódica de cambios en config.json"""
        if self.raiz and self.raiz.winfo_exists():
            self._actualizar_info_conexion()
            self.raiz.after(2000, self._programar_monitoreo_config)
    
    def _iniciar_automaticamente(self):
        """Inicia el microservicio automáticamente al abrir la aplicación"""
        if not self.esta_encendido:
            self.var_estado.set(True)
            self._encender_microservicio()
    
    def _alternar_microservicio(self):
        """Alterna entre encender y apagar el microservicio"""
        if self.var_estado.get():
            self._encender_microservicio()
        else:
            self._apagar_microservicio()
    
    def _encender_microservicio(self):
        """Inicia el proceso del microservicio"""
        if self.esta_encendido:
            return
        
        try:
            comando = self._obtener_comando_servidor()
            self._escribir_log("[INFO] Microservicio Iniciado\n")
            
            entorno = os.environ.copy()
            entorno["PYTHONUNBUFFERED"] = "1"
            
            self.proceso = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                creationflags=CREAR_SIN_VENTANA,
                env=entorno
            )
            
            self.esta_encendido = True
            self.boton_switch.config(text="Encendido")
            
            hilo_lector = threading.Thread(target=self._leer_salida_servidor, daemon=True)
            hilo_lector.start()
            
        except Exception as e:
            self._escribir_log(f"[ERROR] No se pudo iniciar: {e}\n")
            self.var_estado.set(False)
            self.boton_switch.config(text="Apagado")
            self.esta_encendido = False
    
    def _apagar_microservicio(self):
        """Detiene el proceso del microservicio"""
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
    
    def _obtener_comando_servidor(self) -> list:
        """Retorna el comando para iniciar el servidor según el modo de ejecución"""
        if es_modo_ejecucion():
            return [sys.executable, "--modo=servidor", "--solo-servidor"]
        else:
            ruta_main = os.path.join(os.path.dirname(__file__), 'main.py')
            return [sys.executable, ruta_main, "--modo=servidor"]
    
    def _leer_salida_servidor(self):
        """Lee la salida del proceso del servidor en un hilo separado"""
        try:
            if not self.proceso or not self.proceso.stdout:
                return

            for linea in self.proceso.stdout:
                self.cola_salida.put(linea)
        except Exception as e:
            self.cola_salida.put(f"[ERROR] {e}\n")

    def _leer_archivo_log(self):
        """Lee nuevas líneas del archivo de log temporal"""
        if not es_modo_ejecucion():
            return

        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            log_path = os.path.join(temp_dir, 'ms_procesos_server.log')

            if not os.path.exists(log_path):
                return

            # Leer las últimas líneas agregadas desde la última posición
            if not hasattr(self, '_ultima_posicion_log'):
                self._ultima_posicion_log = 0

            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(self._ultima_posicion_log)
                nuevas_lineas = f.readlines()
                self._ultima_posicion_log = f.tell()

                for linea in nuevas_lineas:
                    if linea.strip():  # Solo procesar líneas no vacías
                        self.cola_salida.put(linea)

        except Exception:
            pass  # Ignorar errores de lectura del archivo

    def _programar_refresco_logs(self):
        """Programa el refresco periódico de los logs"""
        self._drenar_cola_logs()
        self._leer_archivo_log()  # También leer del archivo de log
        self.raiz.after(100, self._programar_refresco_logs)
    
    def _drenar_cola_logs(self):
        """Drena la cola de logs y los muestra en la interfaz"""
        try:
            while True:
                linea = self.cola_salida.get_nowait()
                self._escribir_log(linea)
        except queue.Empty:
            pass
    
    def _escribir_log(self, texto: str):
        """Escribe un mensaje en el área de logs"""
        self.texto.configure(state=tk.NORMAL)
        self.texto.insert(tk.END, texto)
        self.texto.see(tk.END)
        
        # Limitar a 1000 líneas
        try:
            total_lineas = int(self.texto.index('end-1c').split('.')[0])
            if total_lineas > 1000:
                self.texto.delete("1.0", f"{total_lineas - 1000}.0")
        except Exception:
            pass
        
        self.texto.configure(state=tk.DISABLED)
    
    def _aplicar_tema_oscuro(self):
        """Aplica el tema oscuro a la interfaz"""
        try:
            estilo = ttk.Style(self.raiz)
            try:
                estilo.theme_use('clam')
            except tk.TclError:
                pass
            
            color_fondo = '#092912'
            color_texto = '#ffffff'
            
            self.raiz.configure(bg=color_fondo)
            estilo.configure('TFrame', background=color_fondo)
            estilo.configure('TLabel', background=color_fondo, foreground=color_texto)
            estilo.configure('TScrollbar', background=color_fondo)
            estilo.configure(
                'Switch.TCheckbutton',
                font=('Segoe UI', 11, 'bold'),
                background=color_fondo,
                foreground=color_texto,
                padding=(10, 6)
            )
            estilo.map(
                'Switch.TCheckbutton',
                foreground=[('disabled', '#aaaaaa'), ('!disabled', color_texto)],
                background=[('active', color_fondo)]
            )
        except Exception:
            pass  # Ignorar errores al limpiar logs

    def _establecer_icono(self):
        """Establece el icono de la ventana"""
        try:
            if es_modo_ejecucion():
                base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
                ruta_icono = os.path.join(base, 'kia.ico')
            else:
                ruta_icono = os.path.join(os.path.dirname(__file__), 'kia.ico')
            
            if os.path.exists(ruta_icono):
                self.raiz.iconbitmap(ruta_icono)
        except Exception:
            pass
    
    def cerrar_interfaz(self):
        """Cierra la interfaz y detiene el microservicio"""
        try:
            self._limpiar_logs()
            self._apagar_microservicio()
        finally:
            self.raiz.destroy()

    def _limpiar_logs(self):
        """Limpia los logs del área de texto y el archivo temporal"""
        try:
            # Limpiar el área de texto de logs
            if hasattr(self, 'texto'):
                self.texto.configure(state=tk.NORMAL)
                self.texto.delete(1.0, tk.END)  # Limpiar todo el contenido
                self.texto.configure(state=tk.DISABLED)

            # Limpiar el archivo de log temporal
            if es_modo_ejecucion():
                try:
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    log_path = os.path.join(temp_dir, 'ms_procesos_server.log')

                    if os.path.exists(log_path):
                        # Crear archivo vacío para limpiar el contenido
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write("")  # Archivo vacío

                except Exception:
                    pass  # Ignorar errores al limpiar el archivo

        except Exception:
            pass  # Ignorar errores al limpiar logs


def iniciar_interfaz():
    """Punto de entrada para iniciar la interfaz gráfica"""
    raiz = tk.Tk()
    raiz.configure(bg='#092912')
    app = InterfazMicroservicio(raiz)
    raiz.protocol("WM_DELETE_WINDOW", app.cerrar_interfaz)
    raiz.mainloop()


if __name__ == '__main__':
    iniciar_interfaz()