import serial
import serial.tools.list_ports
import threading
import time
from collections import deque


class ArduinoConnection:
    """
    SkillMimic Arduino serial communication.

    Individual finger movement:
        F,THUMB,OPEN,800
        F,INDEX,CLOSE,800

    Legacy target packet validation:
        M,0,0,0,0,100

    System commands:
        X = Emergency stop
        S = Status
    """

    FINGERS = (
        "THUMB",
        "INDEX",
        "MIDDLE",
        "RING",
        "LITTLE"
    )

    DIRECTIONS = ("OPEN", "CLOSE")

    MIN_DURATION_MS = 50
    MAX_DURATION_MS = 10000

    def __init__(
        self,
        port=None,
        baudrate=9600,
        timeout=0.2
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.connection = None

        self.lock = threading.RLock()
        self.condition = threading.Condition()

        self.responses = deque(maxlen=500)

        self.reader_thread = None
        self.reader_running = threading.Event()

        self.last_error = None

    # --------------------------------------------------
    # AVAILABLE SERIAL PORTS
    # --------------------------------------------------

    def get_available_ports(self):
        return [
            {
                "device": item.device,
                "description": item.description
            }
            for item in serial.tools.list_ports.comports()
        ]

    # --------------------------------------------------
    # CONNECT TO ARDUINO
    # --------------------------------------------------

    def connect(self, port=None):
        selected_port = port or self.port

        if not selected_port:
            raise ValueError(
                "Arduino COM port is not configured."
            )

        self.disconnect()

        connection = serial.Serial(
            port=selected_port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=1
        )

        with self.lock:
            self.connection = connection
            self.port = selected_port
            self.last_error = None

        # Arduino Uno may reset when serial opens.
        time.sleep(2)

        if not connection.is_open:
            raise ConnectionError(
                "Arduino serial connection failed."
            )

        connection.reset_input_buffer()

        with self.condition:
            self.responses.clear()
            self.condition.notify_all()

        self.reader_running.set()

        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="SkillMimicArduinoReader"
        )

        self.reader_thread.start()

        return self.is_connected()

    # --------------------------------------------------
    # BACKGROUND SERIAL READER
    # --------------------------------------------------

    def _reader_loop(self):
        while self.reader_running.is_set():

            with self.lock:
                connection = self.connection

            if (
                connection is None
                or not connection.is_open
            ):
                break

            try:
                raw = connection.readline()

                if not raw:
                    continue

                message = raw.decode(
                    "utf-8",
                    errors="replace"
                ).strip()

                if message:
                    with self.condition:
                        self.responses.append(message)
                        self.condition.notify_all()

            except (
                serial.SerialException,
                OSError
            ) as error:

                with self.condition:
                    self.last_error = str(error)
                    self.condition.notify_all()

                break

    # --------------------------------------------------
    # COMMAND VALIDATION
    # --------------------------------------------------

    def validate_command(self, command):

        if not isinstance(command, str):
            raise ValueError(
                "Command must be a string."
            )

        command = command.strip()

        if not command:
            raise ValueError(
                "Command cannot be empty."
            )

        # System commands.
        if command in ("X", "S", "RESET"):
            return command

        parts = command.split(",")

        # ----------------------------------------------
        # INDIVIDUAL FINGER EVENT
        # F,FINGER,DIRECTION,DURATION
        # ----------------------------------------------

        if len(parts) == 4 and parts[0] == "F":

            finger = parts[1].strip().upper()
            direction = parts[2].strip().upper()

            if finger not in self.FINGERS:
                raise ValueError(
                    f"Unknown finger: {finger}"
                )

            if direction not in self.DIRECTIONS:
                raise ValueError(
                    "Direction must be OPEN or CLOSE."
                )

            try:
                duration = int(parts[3])

            except ValueError as error:
                raise ValueError(
                    "Movement duration must be an integer."
                ) from error

            if not (
                self.MIN_DURATION_MS
                <= duration
                <= self.MAX_DURATION_MS
            ):
                raise ValueError(
                    "Movement duration must be between "
                    f"{self.MIN_DURATION_MS} and "
                    f"{self.MAX_DURATION_MS} ms."
                )

            return (
                f"F,{finger},{direction},{duration}"
            )

        # ----------------------------------------------
        # LEGACY FIVE-FINGER TARGET PACKET
        # M,THUMB,INDEX,MIDDLE,RING,LITTLE
        # ----------------------------------------------

        if len(parts) == 6 and parts[0] == "M":

            values = []

            for value in parts[1:]:

                try:
                    number = int(value)

                except ValueError as error:
                    raise ValueError(
                        "Finger targets must be integers."
                    ) from error

                if not 0 <= number <= 100:
                    raise ValueError(
                        "Finger targets must be between 0 and 100."
                    )

                values.append(str(number))

            return "M," + ",".join(values)

        raise ValueError(
            "Unsupported command. Expected "
            "F,FINGER,OPEN/CLOSE,DURATION, "
            "legacy M packet, X or S."
        )

    # --------------------------------------------------
    # SEND COMMAND
    # --------------------------------------------------

    def send_command(self, command):

        command = self.validate_command(command)

        with self.lock:

            if not self.is_connected():
                raise ConnectionError(
                    "Arduino is not connected."
                )

            try:
                self.connection.write(
                    (command + "\n").encode("ascii")
                )

                self.connection.flush()

                return True

            except (
                serial.SerialException,
                OSError
            ) as error:

                self.last_error = str(error)
                raise

    # --------------------------------------------------
    # CLEAR OLD RESPONSES
    # --------------------------------------------------

    def clear_responses(self):

        with self.condition:
            self.responses.clear()
            self.condition.notify_all()

    # --------------------------------------------------
    # WAIT FOR RESPONSE
    # --------------------------------------------------

    def wait_for_response(
        self,
        predicate,
        timeout=30
    ):

        deadline = time.monotonic() + timeout

        with self.condition:

            while True:

                for index, message in enumerate(
                    self.responses
                ):

                    if predicate(message):
                        del self.responses[index]
                        return message

                if self.last_error:
                    raise ConnectionError(
                        f"Arduino serial error: {self.last_error}"
                    )

                if not self.is_connected():
                    raise ConnectionError(
                        "Arduino disconnected."
                    )

                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    raise TimeoutError(
                        "Timed out waiting for Arduino response."
                    )

                self.condition.wait(
                    min(remaining, 0.2)
                )

    # --------------------------------------------------
    # WAIT FOR EXACT RESPONSE
    # --------------------------------------------------

    def wait_for_exact(
        self,
        expected,
        timeout=30
    ):

        return self.wait_for_response(
            lambda message: message == expected,
            timeout
        )

    # --------------------------------------------------
    # READ NEXT RESPONSE
    # --------------------------------------------------

    def read_data(self):

        with self.condition:

            if self.responses:
                return self.responses.popleft()

        return None

    # --------------------------------------------------
    # CONNECTION STATUS
    # --------------------------------------------------

    def is_connected(self):

        with self.lock:

            return (
                self.connection is not None
                and self.connection.is_open
            )

    # --------------------------------------------------
    # STATUS INFORMATION
    # --------------------------------------------------

    def get_status(self):

        with self.lock:

            return {
                "connected": self.is_connected(),
                "port": self.port,
                "baudrate": self.baudrate,
                "last_error": self.last_error,
                "reader_running": (
                    self.reader_running.is_set()
                ),
                "pending_responses": len(self.responses)
            }

    # --------------------------------------------------
    # DISCONNECT
    # --------------------------------------------------

    def disconnect(self):

        self.reader_running.clear()

        with self.lock:
            connection = self.connection
            self.connection = None

        if connection is not None:

            try:
                if connection.is_open:
                    connection.close()

            except (
                serial.SerialException,
                OSError
            ):
                pass

        if (
            self.reader_thread
            and self.reader_thread.is_alive()
        ):

            self.reader_thread.join(timeout=1)

        self.reader_thread = None

        with self.condition:
            self.responses.clear()
            self.condition.notify_all()