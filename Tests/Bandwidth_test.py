#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bandwidth_camaras.py
─────────────────────────
Mide la velocidad real de transmisión de datos entre la(s) cámara(s)
Basler y la Raspberry Pi.

• Sin modificar la configuración actual de la cámara.
• Calcula FPS, MB/s y Mbps de carga útil.
• Admite:  -c 0   (cámara 0, por defecto)
           -c 1   (cámara 1)
           -c both   (las dos simultáneas)
           -n N  (número de frames, por defecto 100)

Corrección 2025-06-26
─────────────────────
`TriggerMode` se pone en *Off* **antes** de llamar a `StartGrabbing`;
si el nodo no es editable se ignora, evitando la excepción
“Node is not writable”.

Requisitos:
    pip install pypylon
"""

import time, argparse, sys
from pypylon import pylon


# ───────── función de medición para una cámara ─────────
def medir(cam, n_frames):
    """Devuelve fps, MB/s y Mbps de `cam` capturando `n_frames`."""
    cam.Open()

    # Trigger a freerun SOLO si el nodo es editable
    try:
        if cam.TriggerMode.IsWritable():
            cam.TriggerMode.SetValue("Off")
    except AttributeError:
        pass

    cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    bytes_total = 0
    t0 = time.perf_counter()
    for _ in range(n_frames):
        res = cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        bytes_total += res.GetPayloadSize()
        res.Release()
    dt = time.perf_counter() - t0
    cam.StopGrabbing()

    fps  = n_frames / dt
    mb_s = bytes_total / dt / (1024 * 1024)
    return fps, mb_s, mb_s * 8


# ───────── CLI y flujo principal ─────────
def main():
    ap = argparse.ArgumentParser(description="Test de ancho de banda Basler")
    ap.add_argument("-c", "--cam", default="0",
                    help="'0', '1' o 'both' (defecto 0)")
    ap.add_argument("-n", "--frames", type=int, default=100,
                    help="Frames a capturar (def 100)")
    args = ap.parse_args()

    tl  = pylon.TlFactory.GetInstance()
    dev = tl.EnumerateDevices()
    if not dev:
        sys.exit("No se detectaron cámaras Basler")

    def open_idx(i):
        if i >= len(dev):
            sys.exit(f"Índice {i} fuera de rango ({len(dev)} cámaras)")
        return pylon.InstantCamera(tl.CreateDevice(dev[i]))

    if args.cam == "both":
        cams = [open_idx(0), open_idx(1)]
    else:
        cams = [open_idx(int(args.cam))]

    # Informação básica
    for i, cam in enumerate(cams):
        cam.Open()
        w, h = cam.Width.GetValue(), cam.Height.GetValue()
        fmt  = cam.PixelFormat.GetValue()
        print(f"CAM {i}: {w}×{h}  {fmt}")
        cam.Close()

    if len(cams) == 2:
        # ─── Captura simultánea ───
        for c in cams:
            c.Open()
            try:
                if c.TriggerMode.IsWritable():
                    c.TriggerMode.SetValue("Off")
            except AttributeError:
                pass
            c.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        bytes_tot = [0, 0]
        t0 = time.perf_counter()
        for _ in range(args.frames):
            for idx, c in enumerate(cams):
                res = c.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                bytes_tot[idx] += res.GetPayloadSize()
                res.Release()
        dt = time.perf_counter() - t0

        for c in cams:
            c.StopGrabbing(); c.Close()

        for idx, bt in enumerate(bytes_tot):
            fps  = args.frames / dt
            mb_s = bt / dt / 1024 / 1024
            print(f"CAM {idx} {fps:.2f} fps | {mb_s:.2f} MB/s | {mb_s*8:.2f} Mbps")
    else:
        cam = cams[0]
        fps, mb_s, mbps = medir(cam, args.frames)
        cam.Close()
        print(f"Resultado  {fps:.2f} fps | {mb_s:.2f} MB/s | {mbps:.2f} Mbps")


if __name__ == "__main__":
    main()
