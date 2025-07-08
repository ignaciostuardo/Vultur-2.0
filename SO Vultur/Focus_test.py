#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import messagebox
from functools import partial
import cv2, json, os
from pypylon import pylon

# Parametros por defecto
EXPOSURE, GAIN = 500, 0.0
if os.path.exists("config.json"):
    try:
        cfg = json.load(open("config.json"))["Camaras"]
        EXPOSURE = int(cfg.get("ExposureTime", EXPOSURE))
        GAIN     = float(cfg.get("Gain", GAIN))
    except Exception as e:
        print("config.json invalido; usando valores por defecto:", e)

# Estilo visual
BG_MAIN, FG_MAIN         = "black", "white"
FONT_LABEL               = ("Helvetica", 25)
FONT_BUTTON              = ("Helvetica", 20, "bold")
BTN_BG, BTN_FG           = "gray25", "white"
BTN_ACTIVE_BG, BTN_W     = "gray40", 10

# Funcion para mostrar vista previa
def preview(idx, root):
    tl   = pylon.TlFactory.GetInstance()
    devs = tl.EnumerateDevices()
    if idx >= len(devs):
        messagebox.showerror("Error", f"Can't find the camera {idx+1}.")
        return

    root.withdraw()

    cam = pylon.InstantCamera(tl.CreateDevice(devs[idx]))
    cam.Open()
    cam.Width.Value, cam.Height.Value = 1440, 960
    cam.PixelFormat.Value  = "Mono8"
    cam.ExposureTime.Value = EXPOSURE
    cam.Gain.Value         = GAIN
    cam.TriggerMode.Value  = "Off"
    cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    win = f"CAM {idx+1} - Enfoque (toque para salir)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    quit_flag = False

    def on_mouse(event, x, y, flags, param):
        nonlocal quit_flag
        if event == cv2.EVENT_LBUTTONDOWN:
            quit_flag = True

    cv2.setMouseCallback(win, on_mouse)

    try:
        while not quit_flag:
            res = cam.RetrieveResult(500, pylon.TimeoutHandling_Return)
            if res and res.GrabSucceeded():
                gray = res.Array
                h, w = gray.shape

                roi = gray[h//3 : 2*h//3, w//3 : 2*w//3]
                gx  = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
                gy  = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
                focus = (gx**2 + gy**2).mean()
                enfocado = focus > 1000
                col_bgr = (0, 255, 0) if enfocado else (0, 0, 255)

                frame_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                cv2.rectangle(frame_bgr, (5, 5), (w-6, h-6), col_bgr, thickness=40)
                cv2.putText(frame_bgr, f"Foco: {focus:.0f}",
                            (40, 70), cv2.FONT_HERSHEY_SIMPLEX,
                            1.2, col_bgr, 3, cv2.LINE_AA)
                cv2.imshow(win, frame_bgr)
                res.Release()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        if cam.IsGrabbing(): cam.StopGrabbing()
        cam.Close()
        cv2.destroyWindow(win)
        root.deiconify()

# GUI principal
def main():
    root = tk.Tk()
    root.title("Camera Focus")
    root.configure(bg=BG_MAIN)
    root.attributes("-fullscreen", True)

    barra = tk.Frame(root, bg=BG_MAIN); barra.pack(anchor="ne", padx=20, pady=10)
    tk.Button(barra, text="x",
              command=lambda: root.destroy(),
              font=FONT_LABEL, bg="red", fg="white").pack()

    tk.Label(root, text="Choose a camera",
             font=FONT_LABEL, fg=FG_MAIN, bg=BG_MAIN).pack(pady=10)

    cont = tk.Frame(root, bg=BG_MAIN); cont.pack(pady=40)
    for i, txt in enumerate(("CAM 1", "CAM 2")):
        tk.Button(cont, text=txt, width=BTN_W, height=3,
                  font=FONT_BUTTON, bg=BTN_BG, fg=BTN_FG,
                  activebackground=BTN_ACTIVE_BG,
                  command=partial(preview, i, root)).grid(row=0, column=i,
                                                          padx=30, pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
