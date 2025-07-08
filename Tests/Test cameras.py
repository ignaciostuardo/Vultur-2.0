#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preview_cam1.py  –  Live feed de la cámara 1 a 1280×720 / Mono8

Pulsa ‘q’ para salir.
Requiere:  pip install pypylon opencv-python
"""

import cv2
from pypylon import pylon

# ─── abrir primera cámara ───────────────────────────────────────
tl   = pylon.TlFactory.GetInstance()
devs = tl.EnumerateDevices()
if not devs:
    raise SystemExit("No se detectó ninguna cámara Basler")

cam = pylon.InstantCamera(tl.CreateDevice(devs[0]))
cam.Open()

# resolución y formato ligeros para pre-enfoque
cam.Width.Value  = 1280
cam.Height.Value = 720
cam.PixelFormat.Value = "Mono8"
cam.TriggerMode.Value = "Off"          # freerun

cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
cv2.namedWindow("Cam1 — preview (q para salir)",
                cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)

try:
    while True:
        res = cam.RetrieveResult(500, pylon.TimeoutHandling_Return)
        if res and res.GrabSucceeded():
            frame = res.Array                # ya es uint8
            cv2.imshow("Cam1 — preview (q para salir)", frame)
            res.Release()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    if cam.IsGrabbing():
        cam.StopGrabbing()
    cam.Close()
    cv2.destroyAllWindows()
