#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_gps_rtk.py
--------------
Registra la posicion del GPS Here3+ (RTK) que llega via Pixhawk/MAVLink
y la vuelca a un CSV cada 1 segundos.  No controla camaras ni guarda
imagenes: solo GPS.

• Puerto serie Pixhawk  : /dev/serial0  @ 57600 baud
• Mensaje MAVLink usado : GLOBAL_POSITION_INT
• Salida                : carpeta logs_<fecha>/gps_log.csv
• Detencion limpia      : Ctrl-C   o pulsador en GPIO 26
"""

from pymavlink import mavutil
import time, datetime, csv, os, signal, RPi.GPIO as GPIO, threading

# ---------- GPIO STOP ----------
STOP_PIN = 26
detener  = threading.Event()

def _stop(*_):
    detener.set()

GPIO.setmode(GPIO.BCM)
GPIO.setup(STOP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(STOP_PIN, GPIO.FALLING, callback=_stop, bouncetime=300)
signal.signal(signal.SIGINT , _stop)
signal.signal(signal.SIGTERM, _stop)

# ---------- carpeta y CSV ----------
stamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
folder  = f"logs_{stamp}"
os.makedirs(folder, exist_ok=True)
csv_path = os.path.join(folder, "gps_log.csv")

# ---------- conectar MAVLink ----------
print("Conectando a Pixhawk / GPS…")
try:
    mav = mavutil.mavlink_connection('/dev/serial0', baud=57600)
    mav.wait_heartbeat(timeout=10)
    print("Heartbeat recibido; comenzando log cada 1 s.")
except Exception as e:
    raise SystemExit(f"ERROR: no se pudo conectar — {e}")

# ---------- bucle principal ----------
with open(csv_path, "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["timestamp_utc", "lat_deg", "lon_deg", "alt_m"])

    while not detener.is_set():
        inicio = time.time()

        msg = mav.recv_match(type="GLOBAL_POSITION_INT",
                             blocking=True, timeout=1.5)

        lat = lon = alt = None
        if msg:
            lat = msg.lat / 1e7        # grados
            lon = msg.lon / 1e7
            alt = msg.alt / 1000.0     # metros

        wr.writerow([datetime.datetime.utcnow()
                       .isoformat(timespec="milliseconds"),
                     lat, lon, alt])
        f.flush()

        # esperar hasta completar 2 s exactos
        restante = 1.0 - (time.time() - inicio)
        if restante > 0:
            time.sleep(restante)

print("\nLog detenido; archivo en:", csv_path)
GPIO.cleanup()
