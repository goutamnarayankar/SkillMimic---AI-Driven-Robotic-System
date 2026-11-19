
class EmergencyStop:

    def __init__(self, safety_controller):

        self.safety_controller = safety_controller
        self.activated = False

    def activate(self):

        self.activated = True

        self.safety_controller.activate_emergency_stop()

        return {
            "success": True,
            "message": "Software emergency stop activated."
        }

    def reset(self, operator_confirmed=False):

        if not self.activated:
            return False

        reset_success = (
            self.safety_controller.reset_emergency_stop(
                operator_confirmed=operator_confirmed
            )
        )

        if reset_success:
            self.activated = False

        return reset_success

    def is_active(self):

        return self.activated
