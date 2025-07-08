import tkinter as tk
from tkinter import messagebox, Toplevel
import subprocess
import threading
import sys
import signal
import RPi.GPIO as GPIO
import os
import time

AUTOHIDE_DELAY_MS = 10000

class InterfazApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interfaz de Ejecucion de Codigos")
        self.capture_process = None
        self.console_window = None
        self.console_text = None
        self.hide_timer = None
        self.apagado_timer = None
        self.timer_mensaje = None
        self.popup_apagado = None
        self.animacion_activa = False
        self.shutdown_hold_time = 5000
        self.marcos_verdes = []
        self.parpadeo_activo = False

        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        self.is_fullscreen = True

        self.frame_botones = tk.Frame(root, bg='black')
        self.frame_botones.pack(pady=20)

        botones = [
            ("Detect Devices", self.detectar_dispositivos, "purple"),
            ("Configure Cameras", self.abrir_configuracion, "blue"),
            ("Live View", self.capturar_y_ver, "blue"),
            ("Flight Calculator", self.abrir_calculadora_vuelo, "orange"),
            ("Start Capture", self.capturar_imagenes, "green"),
            ("Stop Capture", self.detener_captura, "red")
        ]

        for i, (texto, comando, color) in enumerate(botones):
            tk.Button(self.frame_botones, text=texto, command=comando, height=5, width=25,
                      bg=color, fg='white', font=("Helvetica", 10, "bold")).grid(row=i // 2, column=i % 2, padx=5, pady=5)

        sys.stdout = self

        GPIO.setmode(GPIO.BCM)
        self.pin_start = 19
        self.pin_stop  = 26
        GPIO.setup(self.pin_start, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.pin_stop,  GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(self.pin_start, GPIO.FALLING, callback=self.iniciar_captura_gpio, bouncetime=300)
        GPIO.add_event_detect(self.pin_stop,  GPIO.BOTH, callback=self.controlar_apagado_fisico, bouncetime=300)

        self.root.bind("<Escape>", self.toggle_fullscreen)

    def mostrar_marco_verde(self):
        if self.marcos_verdes:
            return
        self.marcos_verdes.append(tk.Frame(self.root, bg="green", height=10))
        self.marcos_verdes[-1].place(x=0, y=0, relwidth=1)
        self.marcos_verdes.append(tk.Frame(self.root, bg="green", width=10))
        self.marcos_verdes[-1].place(x=0, y=0, relheight=1)
        self.marcos_verdes.append(tk.Frame(self.root, bg="green", width=10))
        self.marcos_verdes[-1].place(relx=1.0, x=-10, y=0, relheight=1)
        self.marcos_verdes.append(tk.Frame(self.root, bg="green", height=10))
        self.marcos_verdes[-1].place(x=0, rely=1.0, y=-10, relwidth=1)
        self.parpadeo_activo = True
        self.parpadear_marco()

    def ocultar_marco_verde(self):
        self.parpadeo_activo = False
        for marco in self.marcos_verdes:
            marco.destroy()
        self.marcos_verdes.clear()

    def parpadear_marco(self):
        if not self.parpadeo_activo:
            return
        estado = self.marcos_verdes[0].cget("bg")
        nuevo_color = "black" if estado == "green" else "green"
        for marco in self.marcos_verdes:
            marco.configure(bg=nuevo_color)
        self.root.after(500, self.parpadear_marco)

    def controlar_apagado_fisico(self, channel):
        if GPIO.input(self.pin_stop) == GPIO.LOW:
            self.hold_start_time = time.time()
            self.timer_mensaje = self.root.after(2000, self.mostrar_mensaje_apagado)
            self.apagado_timer = self.root.after(self.shutdown_hold_time, self.apagar_sistema)
        else:
            if self.apagado_timer:
                self.root.after_cancel(self.apagado_timer)
                self.apagado_timer = None
            if self.timer_mensaje:
                self.root.after_cancel(self.timer_mensaje)
                self.timer_mensaje = None
            self.ocultar_popup_apagado()
            dur = time.time() - getattr(self, 'hold_start_time', 0)
            if dur < self.shutdown_hold_time / 1000:
                self.detener_captura()

    def mostrar_mensaje_apagado(self):
        if self.popup_apagado or self.animacion_activa:
            return
        self.popup_apagado = Toplevel(self.root)
        self.popup_apagado.attributes('-fullscreen', True)
        self.popup_apagado.configure(bg='black')
        label = tk.Label(self.popup_apagado, text="Shutting down...", fg='white', bg='black', font=('Helvetica', 32, 'bold'))
        label.pack(expand=True)
        self.animacion_activa = True

    def ocultar_popup_apagado(self):
        if self.popup_apagado:
            self.popup_apagado.destroy()
            self.popup_apagado = None
            self.animacion_activa = False

    def apagar_sistema(self):
        self.mostrar_mensaje_apagado()
        self.root.after(3000, lambda: os.system("sudo shutdown now"))

    def iniciar_captura_gpio(self, channel):
        if self.capture_process is not None:
            self.write("Script alredy excecuted.\n")
            return
        self.write("START pressed: iniciating capture...\n")
        threading.Thread(target=self.ejecutar_script_captura, args=('capturar_imagenes_gps.py',), daemon=True).start()

    def create_console_window(self):
        if self.console_window is not None:
            return
        self.console_window = Toplevel(self.root)
        self.console_window.title("Salida")
        self.console_window.configure(bg="black")
        self.console_window.attributes("-topmost", True)
        w, h = 500, 150
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        self.console_window.geometry(f"{w}x{h}+{x}+{y}")
        self.console_text = tk.Text(self.console_window, height=5, width=25, font=("Helvetica", 10), bg="black", fg="white")
        self.console_text.pack(expand=True, fill='both')
        self.console_window.protocol("WM_DELETE_WINDOW", self.ocultar_consola)

    def write(self, text):
        self.create_console_window()
        if self.hide_timer:
            self.console_window.after_cancel(self.hide_timer)
        self.console_text.insert(tk.END, text)
        self.console_text.see(tk.END)
        self.console_text.update()
        self.hide_timer = self.console_window.after(AUTOHIDE_DELAY_MS, self.ocultar_consola)

    def flush(self):
        pass

    def ocultar_consola(self):
        if self.console_window:
            self.console_window.destroy()
            self.console_window = None
            self.console_text = None
            self.hide_timer = None

    def ejecutar_script(self, script):
        try:
            process = subprocess.Popen(['python3', script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                self.write(line)
            process.stdout.close()
            process.wait()
        except Exception as e:
            self.write(f"Error ejecutando {script}: {e}\n")

    def ejecutar_script_captura(self, script):
        try:
            self.mostrar_marco_verde()
            self.capture_process = subprocess.Popen(['python3', script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in self.capture_process.stdout:
                self.write(line)
            self.capture_process.stdout.close()
            self.capture_process.wait()
        except Exception as e:
            self.write(f"Error ejecutando {script}: {e}\n")
        finally:
            self.capture_process = None
            self.ocultar_marco_verde()

    def detectar_dispositivos(self):
        threading.Thread(target=self.ejecutar_script, args=('detectar_camaras.py',), daemon=True).start()
        threading.Thread(target=self.ejecutar_script, args=('detectar_gps.py',), daemon=True).start()

    def abrir_configuracion(self):
        threading.Thread(target=self.ejecutar_script, args=('configurar_parametros.py',), daemon=True).start()

    def capturar_imagenes(self):
        if self.capture_process is not None:
            messagebox.showinfo("Informacion", "El script de captura ya esta en ejecucion.")
            return
        threading.Thread(target=self.ejecutar_script_captura, args=('capturar_imagenes_gps.py',), daemon=True).start()

    def capturar_y_ver(self):
        threading.Thread(target=self.ejecutar_script, args=('Focus_test.py',), daemon=True).start()

    def detener_captura(self):
        if self.capture_process is not None:
            if self.capture_process.poll() is None:
                self.capture_process.send_signal(signal.SIGINT)
                try:
                    self.capture_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.write("El proceso no se cerro a tiempo, se forzara el cierre.\n")
                    self.capture_process.kill()
            self.capture_process = None
            self.ocultar_marco_verde()
            self.write("Data saved.\n")
        else:
            messagebox.showinfo("Informacion", "No hay un proceso de captura en ejecucion.")

    def abrir_calculadora_vuelo(self):
        try:
            subprocess.Popen(['python3', 'calculadora_vuelo_con_retorno.py'])
        except Exception as e:
            self.write(f"No se pudo abrir la calculadora: {e}\n")

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', self.is_fullscreen)
        return "break"

root = tk.Tk()
app = InterfazApp(root)
root.mainloop()
GPIO.cleanup()
