
import serial
import time

PORT = "COM8"
BAUD = 9600

GESTURES = {
    "1": ("OPEN ALL", [0, 0, 0, 0, 0]),
    "2": ("CLOSE ALL", [100, 100, 100, 100, 100]),
}

def read_until(arduino, expected, timeout=15):

    start = time.monotonic()

    while time.monotonic() - start < timeout:

        line = arduino.readline().decode(
            "utf-8", errors="ignore"
        ).strip()

        if not line:
            continue

        print("Arduino:", line)

        if line == expected:
            return True

        if line.startswith("ERROR,"):
            raise RuntimeError(line)

        if line == "HOME_REQUIRED":
            raise RuntimeError(line)

    raise TimeoutError(
        "Arduino did not send " + expected
    )


def send_movement(arduino, values):

    packet = "M," + ",".join(
        str(value) for value in values
    )

    print("\nSending:", packet)

    arduino.write(
        (packet + "\n").encode("ascii")
    )
    arduino.flush()

    read_until(arduino, "ACK,M", timeout=8)

    print("Movement started.")

    read_until(arduino, "DONE", timeout=15)

    print("Movement completed.")

    print("Cooldown: 2.5 seconds")
    time.sleep(2.5)


def main():

    arduino = None

    try:

        print("Connecting to Arduino:", PORT)

        arduino = serial.Serial(
            PORT,
            BAUD,
            timeout=0.2,
            write_timeout=2
        )

        # Arduino resets when serial opens.
        time.sleep(2)

        arduino.reset_input_buffer()

        print("\nCheck that the glove is physically open.")
        print("Ensure the pneumatic system is safe.")

        confirmation = input(
            "Type HOME to confirm physical open position: "
        )

        if confirmation.strip().upper() != "HOME":
            print("Test cancelled.")
            return

        arduino.write(b"R\n")
        arduino.flush()

        read_until(arduino, "ACK,HOME")
        read_until(arduino, "READY")

        print("\nSKILLMIMIC GLOVE TEST")

        while True:

            print("\n1. Open All Fingers")
            print("2. Close All Fingers")
            print("3. Emergency Stop")
            print("4. Exit")

            choice = input("\nSelect option: ").strip()

            if choice == "4":
                print("Exiting.")
                break

            if choice == "3":

                print("EMERGENCY STOP REQUESTED")

                arduino.write(b"X\n")
                arduino.flush()

                time.sleep(0.3)

                while arduino.in_waiting:
                    line = arduino.readline().decode(
                        errors="ignore"
                    ).strip()

                    if line:
                        print("Arduino:", line)

                print("Inspect glove before recovery.")
                break

            if choice not in GESTURES:
                print("Invalid selection.")
                continue

            name, values = GESTURES[choice]

            print("\nSelected:", name)

            confirm = input(
                "Confirm movement? (y/n): "
            ).strip().lower()

            if confirm != "y":
                print("Cancelled.")
                continue

            send_movement(arduino, values)

    except Exception as error:

        print("\nTEST STOPPED:", error)
        print("Inspect the hardware before recovery.")

    finally:

        if arduino is not None and arduino.is_open:
            arduino.close()

            print("\nSerial connection closed.")


if __name__ == "__main__":
    main()
