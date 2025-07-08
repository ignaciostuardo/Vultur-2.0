import tkinter as tk
from pymavlink import mavutil
import threading
import time

def iniciar_lectura():
    try:
        conexion = mavutil.mavlink_connection('/dev/serial0', baud=57600)
        conexion.wait_heartbeat(timeout=10)

        def actualizar_valores():
            while True:
                msg = conexion.recv_match(type='ATTITUDE', blocking=True, timeout=5)
                if msg:
                    roll = round(msg.roll * 57.2958, 1)   # rad a grados
                    pitch = round(msg.pitch * 57.2958, 1)
                    yaw = round(msg.yaw * 57.2958, 1)
                    label_yaw.config(text=f"Yaw: {yaw} grados")
                    label_pitch.config(text=f"Pitch: {pitch} grados")
                    label_roll.config(text=f"Roll: {roll} grados")
                time.sleep(0.2)

        threading.Thread(target=actualizar_valores, daemon=True).start()

    except Exception as e:
        label_yaw.config(text=f"Error: {e}")

app = tk.Tk()
app.title("Lectura en vivo de Yaw, Pitch y Roll")
app.configure(bg='black')
app.attributes('-fullscreen', True)

label_titulo = tk.Label(app, text="Lectura de Yaw, Pitch y Roll", font=("Helvetica", 22), fg="white", bg="black")
label_titulo.pack(pady=40)

label_yaw = tk.Label(app, text="Yaw: -", font=("Helvetica", 20), fg="cyan", bg="black")
label_yaw.pack(pady=10)

label_pitch = tk.Label(app, text="Pitch: -", font=("Helvetica", 20), fg="cyan", bg="black")
label_pitch.pack(pady=10)

label_roll = tk.Label(app, text="Roll: -", font=("Helvetica", 20), fg="cyan", bg="black")
label_roll.pack(pady=10)

btn_salir = tk.Button(app, text="Salir", command=app.destroy, font=("Helvetica", 14), bg="red", fg="white", width=15, height=2)
btn_salir.pack(pady=40)

iniciar_lectura()
app.mainloop()
