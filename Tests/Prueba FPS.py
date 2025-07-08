#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fps_basler.py
------------------
Mide la tasa real de frames por segundo (FPS) que pueden entregar DOS
cámaras Basler a2A3840-13gm *sin* escribir nada en la SD.

Qué hace:
1. Configura ambas cámaras en modo libre (Continuous) con los parámetros fijos:
      Width  = 3840
      Height = 2160
      PixelFormat = "Mono12"
      ExposureTime = 500 µs (puedes ajustarlo)
2. Activa `AcquisitionFrameRateEnable` y deja que la cámara use su máximo
   (`ResultingFrameRate` suele ser ≈13 fps para este modelo).
3. Empieza a capturar y, cada segundo, imprime:
      [segundos]  cam1_fps  cam2_fps
4. Se detiene con Ctrl-C o con el pulsador en GPIO 26.

No guarda imágenes, solo las desecha, de modo que el cuello de botella SD
queda fuera de la prueba.
"""

from pypylon import pylon
import time, datetime, signal, RPi.GPIO as GPIO

# ------------- GPIO para STOP ----------------
parar = False
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)
def detener(*_):
    global parar
    parar = True
signal.signal(signal.SIGINT, detener)
signal.signal(signal.SIGTERM, detener)
GPIO.add_event_detect(26, GPIO.FALLING, callback=detener, bouncetime=300)

# ------------- inicializar camaras -----------
tl  = pylon.TlFactory.GetInstance()
dev = tl.EnumerateDevices()
if len(dev) < 2:
    raise SystemExit("Conecta dos camaras Basler primero")

cam1, cam2 = [pylon.InstantCamera(tl.CreateDevice(d)) for d in dev[:2]]

def conf(cam):
    cam.Open()
    cam.Width.SetValue(2160)
    cam.Height.SetValue(1440)
    cam.PixelFormat.SetValue("Mono12p")
    cam.ExposureTime.SetValue(500)              # 0.5 ms
    cam.AcquisitionFrameRateEnable.SetValue(True)
    # Poner algo muy alto; la propia cámara lo limitará a su máximo
    cam.AcquisitionFrameRate.SetValue(1000.0)
    print(cam.GetDeviceInfo().GetModelName(),
          "ResultingFrameRate =",
          cam.ResultingFrameRate.GetValue(), "fps")

conf(cam1)
conf(cam2)

cam1.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
cam2.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

print("\nMidiendo FPS (Ctrl-C o pulsador GPIO 26 para salir) ...\n")
inicio = time.time()
cnt1 = cnt2 = 0
ultimo_segundo = int(time.time())

try:
    while not parar:
        if cam1.RetrieveResult(0, pylon.TimeoutHandling_Return):
            cnt1 += 1
        if cam2.RetrieveResult(0, pylon.TimeoutHandling_Return):
            cnt2 += 1

        ahora = time.time()
        if int(ahora) != ultimo_segundo:
            seg = int(ahora - inicio)
            print(f"[{seg:>4}s]  cam1: {cnt1:>4}  cam2: {cnt2:>4}")
            cnt1 = cnt2 = 0
            ultimo_segundo = int(ahora)

finally:
    cam1.StopGrabbing(); cam2.StopGrabbing()
    cam1.Close(); cam2.Close()
    GPIO.cleanup()
    print("Terminado.")
