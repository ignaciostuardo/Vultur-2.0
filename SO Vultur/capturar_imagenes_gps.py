#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pypylon import pylon
import tifffile as tiff
import json, time, datetime, csv, pathlib, sys, signal, threading
import RPi.GPIO as GPIO
from pymavlink import mavutil

# ───────── GPIO ─────────
LED_RUN, LED_WARN = 16, 20
stop = False

print_fix_warning = True

def _stop(*_):
    global stop
    stop = True

signal.signal(signal.SIGINT , _stop)
signal.signal(signal.SIGTERM, _stop)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_RUN , GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LED_WARN, GPIO.OUT, initial=GPIO.LOW)

# ───────── leer config ─────────
prm = json.load(open("config.json")) ["Camaras"]
FPS, EXP, GAIN = float(prm.get("FPS",2)), int(prm.get("ExposureTime",500)), float(prm.get("Gain",0))
PERIODO, DELAY = 1/FPS, 0.01

# ───────── GPS check ─────────
gps_ok = False
last_gps = {"hora": None, "lat": None, "lon": None, "alt": None}
last_att = {"yaw":None,"pitch":None,"roll":None,"gs":None,"climb":None}

def gps_reader():
    global gps_ok, print_fix_warning
    while True:
        try:
            msg = mav.recv_match(type=['GLOBAL_POSITION_INT','GPS_RAW_INT','ATTITUDE','VFR_HUD'], blocking=True, timeout=1)
        except Exception:
            continue
        if not msg:
            continue

        if msg.get_type() == "GLOBAL_POSITION_INT" and msg.lat not in (0, 0x7FFFFFFF):
            gps_ok = True
            last_gps.update(
                hora=datetime.datetime.utcnow().isoformat(timespec="milliseconds"),
                lat=msg.lat/1e7, lon=msg.lon/1e7, alt=msg.alt/1000.0)

        elif msg.get_type() == "GPS_RAW_INT":
            if msg.fix_type >= 3 and msg.lat not in (0, 0x7FFFFFFF):
                gps_ok = True
                last_gps.update(
                    hora=datetime.datetime.utcnow().isoformat(timespec="milliseconds"),
                    lat=msg.lat/1e7, lon=msg.lon/1e7, alt=msg.alt/1000.0)
            elif print_fix_warning:
                print("No GPS fix.")
                print_fix_warning = False

        elif msg.get_type() == "ATTITUDE":
            last_att.update(
                yaw  = round(msg.yaw   * 57.2958, 2),
                pitch= round(msg.pitch * 57.2958, 2),
                roll = round(msg.roll  * 57.2958, 2))

        elif msg.get_type() == "VFR_HUD":
            last_att.update(gs=msg.groundspeed, climb=msg.climb)

# ───────── GPS init ─────────
try:
    mav = mavutil.mavlink_connection('/dev/serial0', baud=57600)
    mav.wait_heartbeat(timeout=3)
    threading.Thread(target=gps_reader, daemon=True).start()
except Exception:
    gps_ok = False

if not gps_ok:
    for _ in range(2):
        GPIO.output(LED_WARN, 1); time.sleep(0.25)
        GPIO.output(LED_WARN, 0); time.sleep(0.25)
    print("Continuing without GPS ")

# ───────── carpetas ─────────
ini = datetime.datetime.now()
root = pathlib.Path.home()/f"Campaña {ini:%d-%m-%Y} - {ini:%Hh%Mm%Ss}"
(cam1_dir:=root/"CAM1").mkdir(parents=True, exist_ok=True)
(cam2_dir:=root/"CAM2").mkdir(exist_ok=True)
csv_path = root/"log_Campaña.csv"

parametros = {"Fecha_inicio": ini.isoformat(sep=" ", timespec="seconds"),
              "FPS": FPS, "Delay_master_slave_s": DELAY,
              "ExposureTime_us": EXP, "Gain": GAIN,
              "PixelFormat": "Mono12", "GPS_detectado": gps_ok}
json.dump(parametros, open(root/"Parametros.json","w"), indent=2)

# ───────── cámaras ─────────
tl=pylon.TlFactory.GetInstance()
devs=tl.EnumerateDevices()
if len(devs)<2:
    GPIO.cleanup(); sys.exit("Connect 2 cameras")

cam1,cam2=[pylon.InstantCamera(tl.CreateDevice(d)) for d in devs[:2]]
def cfg(c):
    c.Open(); c.Width.Value=3840; c.Height.Value=2160; c.PixelFormat.Value="Mono12"
    c.ExposureTime.Value=EXP; c.Gain.Value=GAIN
    c.TriggerSelector.Value="FrameStart"; c.TriggerMode.Value="On"; c.TriggerSource.Value="Software"

for c in (cam1,cam2): cfg(c); c.StartGrabbing(pylon.GrabStrategy_OneByOne)

GPIO.output(LED_RUN, 1)
print("Capturing")

with csv_path.open("w",newline="") as fcsv:
    wr=csv.writer(fcsv)
    wr.writerow(["Hora_RTC","Hora_GPS","Img_cam1","Img_cam2",
                 "Lat","Lon","Alt",
                 "Yaw_deg","Pitch_deg","Roll_deg", "gs","climb" ])
    try:
        while not stop:
            tic=time.time()

            cam1.ExecuteSoftwareTrigger()
            r1=cam1.RetrieveResult(5000,pylon.TimeoutHandling_ThrowException)
            time.sleep(DELAY)
            cam2.ExecuteSoftwareTrigger()
            r2=cam2.RetrieveResult(5000,pylon.TimeoutHandling_ThrowException)

            if r1.GrabSucceeded() and r2.GrabSucceeded():
                rtc=datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
                gps_iso = last_gps["hora"] or "NONE"
                lat = last_gps["lat"] if last_gps["lat"] is not None else "NONE"
                lon = last_gps["lon"] if last_gps["lon"] is not None else "NONE"
                alt = last_gps["alt"] if last_gps["alt"] is not None else "NONE"

                yaw  = last_att["yaw"]  if last_att["yaw"]  is not None else "NONE"
                pitch= last_att["pitch"]if last_att["pitch"]is not None else "NONE"
                roll = last_att["roll"] if last_att["roll"] is not None else "NONE"
                gs   = last_att["gs"]   if last_att["gs"]   is not None else "NONE"
                climb= last_att["climb"]if last_att["climb"]is not None else "NONE"

                ts=datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                f1,f2=cam1_dir/f"cam1_{ts}.tiff",cam2_dir/f"cam2_{ts}.tiff"
                tiff.imwrite(f1,r1.GetArray(),photometric="minisblack")
                tiff.imwrite(f2,r2.GetArray(),photometric="minisblack")
                wr.writerow([rtc, gps_iso, f1.name, f2.name, lat, lon, alt,
                             yaw, pitch, roll, gs, climb]); fcsv.flush()

            r1.Release(); r2.Release()
            time.sleep(max(0, PERIODO-(time.time()-tic)))
    finally:
        for c in (cam1,cam2):
            if c.IsGrabbing(): c.StopGrabbing(); c.Close()
        GPIO.output(LED_RUN, 0); GPIO.cleanup()
        print("End Capture")
