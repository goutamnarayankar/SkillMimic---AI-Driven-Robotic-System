
from core.hardware.arduino_connection import ArduinoConnection


class DeviceManager:

    def __init__(self, port=None, baudrate=9600):

        self.arduino = ArduinoConnection(
            port=port,
            baudrate=baudrate
        )

        self.device_name = "SkillMimic Pneumatic Glove"
        self.device_ready = False

    def connect_device(self, port=None):

        connected = self.arduino.connect(port)

        self.device_ready = connected

        return connected

    def disconnect_device(self):

        self.arduino.disconnect()
        self.device_ready = False

    def get_device_status(self):

        connection_status = self.arduino.get_status()

        return {
            "device_name": self.device_name,
            "connected": connection_status["connected"],
            "ready": self.device_ready,
            "port": connection_status["port"],
            "baudrate": connection_status["baudrate"]
        }

    def get_available_devices(self):

        return self.arduino.get_available_ports()

    def is_ready(self):

        return (
            self.device_ready
            and self.arduino.is_connected()
        )
