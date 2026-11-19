
import time


class SafetyController:

    def __init__(self, command_timeout=1.0):

        self.armed = False
        self.emergency_active = False

        self.command_timeout = command_timeout
        self.last_command_time = None

    def arm_system(self):

        if self.emergency_active:
            return False

        self.armed = True
        self.last_command_time = time.monotonic()

        return True

    def disarm_system(self):

        self.armed = False
        self.last_command_time = None

    def activate_emergency_stop(self):

        self.emergency_active = True
        self.armed = False
        self.last_command_time = None

    def reset_emergency_stop(self, operator_confirmed=False):

        if not operator_confirmed:
            return False

        self.emergency_active = False
        self.armed = False

        return True

    def validate_command(self, device_ready=False):

        if self.emergency_active:
            return False

        if not self.armed:
            return False

        if not device_ready:
            return False

        self.last_command_time = time.monotonic()

        return True

    def check_watchdog(self):

        if not self.armed:
            return False

        if self.last_command_time is None:
            self.disarm_system()
            return False

        elapsed = (
            time.monotonic() - self.last_command_time
        )

        if elapsed > self.command_timeout:
            self.disarm_system()
            return False

        return True

    def get_status(self):

        return {
            "armed": self.armed,
            "emergency_active": self.emergency_active,
            "watchdog_active": self.armed
        }
