from pypylon import pylon
import RPi.GPIO as GPIO
import time

# Pines para los colores del LED RGB (cátodo común)
PIN_ROJO = 20
PIN_AZUL = 21

# Configuración GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_ROJO, GPIO.OUT)
GPIO.setup(PIN_AZUL, GPIO.OUT)

def apagar_led_rgb():
    GPIO.output(PIN_ROJO, GPIO.LOW)
    GPIO.output(PIN_AZUL, GPIO.LOW)

def encender_color(rojo=False, azul=False):
    GPIO.output(PIN_ROJO, GPIO.HIGH if rojo else GPIO.LOW)
    GPIO.output(PIN_AZUL, GPIO.HIGH if azul else GPIO.LOW)

def parpadear_color(rojo=False, azul=False, veces=3, intervalo=0.3):
    for _ in range(veces):
        encender_color(rojo=rojo, azul=azul)
        time.sleep(intervalo)
        apagar_led_rgb()
        time.sleep(intervalo)

def detectar_camaras():
    try:
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()

        if len(devices) == 0:
            print("No cameras were detected")
            parpadear_color(rojo=True, veces=3)
        else:
            camera_list = "\n".join([f"{i+1}. {device.GetFriendlyName()}" for i, device in enumerate(devices)])
            print(f"Detected cameras:\n{camera_list}")
            parpadear_color(azul=True, veces=len(devices))
    except Exception as e:
        print(f"There was a problem detecting cameras: {e}")
    finally:
        apagar_led_rgb()
        GPIO.cleanup()

if __name__ == "__main__":
    detectar_camaras()

