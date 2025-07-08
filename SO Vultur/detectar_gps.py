from pymavlink import mavutil

def main():
    try:
        connection = mavutil.mavlink_connection('/dev/serial0', baud=57600)
        connection.wait_heartbeat(timeout=10)
        print("Heartbeat detected. Waiting for GPS fix...")

        fix_obtenido = False
        while not fix_obtenido:
            msg = connection.recv_match(type='GPS_RAW_INT', blocking=True, timeout=5)
            if not msg:
                print("Timeout waiting for GPS.")
                break

            if msg.fix_type >= 3 and msg.lat not in (0, 0x7FFFFFFF):
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt = msg.alt / 1000.0
                print("GPS OK")
                print(f"Current position: Latitude={lat:.7f}, longitude={lon:.7f}, altitude={alt:.1f} m")
                fix_obtenido = True
            else:
                print("GPS detected but no valid fix (Waiting for fix >= 3)...")
                break

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
