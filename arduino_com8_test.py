import serial
import time

PORT = "COM8"
BAUD = 9600

print("Connecting to", PORT)

try:
    ser = serial.Serial(PORT, BAUD, timeout=0.25, write_timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()

    def read_response(timeout=4):
        lines = []
        deadline = time.time() + timeout

        while time.time() < deadline:
            raw = ser.readline()
            if raw:
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    print("ARDUINO:", line)
                    lines.append(line)
        return lines

    print("\nTEST 1: Requesting Arduino status")
    ser.write(b"S\n")
    ser.flush()

    responses = read_response(3)
    status = next((x for x in responses if x.startswith("STATUS,")), None)

    if not status:
        print("\nFAIL: No STATUS response received.")
    else:
        values = status.split(",")[1:]
        if len(values) != 5:
            print("\nFAIL: Invalid finger status:", status)
        else:
            packet = "M," + ",".join(values) + "\n"

            print("\nTEST 2: Sending unchanged finger positions")
            print("COMMAND:", packet.strip())

            ser.write(packet.encode("ascii"))
            ser.flush()

            responses = read_response(4)

            if "ACK,M" in responses and "DONE,M" in responses:
                print("\nPASS: Arduino acknowledged and completed the no-change command.")
            elif "ERROR,ESTOP" in responses:
                print("\nFAIL: Arduino emergency-stop latch is active.")
            else:
                print("\nFAIL: Expected ACK,M and DONE,M were not both received.")

    ser.close()

except Exception as e:
    print("\nDIAGNOSTIC ERROR:", repr(e))

