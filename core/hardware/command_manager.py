
class CommandManager:

    FINGERS = [
        "thumb",
        "index",
        "middle",
        "ring",
        "little"
    ]

    JOINTS = ["pip", "dip"]

    def __init__(self):

        self.protocol_configured = True

    def validate_targets(self, target_data):

        if not isinstance(target_data, dict):
            raise ValueError("Invalid target data.")

        targets = target_data.get("targets")

        if not isinstance(targets, dict):
            raise ValueError("Missing finger targets.")

        validated = {}

        for finger in self.FINGERS:

            if finger not in targets:
                raise ValueError(
                    f"Missing target for {finger}."
                )

            validated[finger] = {}

            for joint in self.JOINTS:

                value = targets[finger].get(joint)

                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                ):
                    raise ValueError(
                        f"Invalid {finger} {joint} target."
                    )

                if not 0 <= value <= 100:
                    raise ValueError(
                        f"{finger} {joint} must be between 0 and 100."
                    )

                validated[finger][joint] = round(
                    float(value), 2
                )

        return validated

    def prepare_command(self, target_data):

        validated = self.validate_targets(target_data)

        return {
            "hand_id": target_data.get("hand_id"),
            "handedness": target_data.get("handedness"),
            "targets": validated
        }

    def get_finger_curl_values(self, target_data):

        prepared = self.prepare_command(target_data)

        values = []

        for finger in self.FINGERS:

            pip = prepared["targets"][finger]["pip"]
            dip = prepared["targets"][finger]["dip"]

            # One pneumatic finger actuator is represented
            # by a combined curl value, not independent joints.
            curl = round((pip + dip) / 2)

            values.append(curl)

        return values

    def encode_command(self, target_data):

        if not self.protocol_configured:
            raise RuntimeError(
                "Arduino movement protocol has not been confirmed."
            )

        values = self.get_finger_curl_values(target_data)

        # Proposed protocol packet.
        # Arduino firmware must support this packet before use.
        packet = "M," + ",".join(
            str(value) for value in values
        ) + "\n"

        return packet

    def configure_protocol(self, confirmed=False):

        if not confirmed:
            raise ValueError(
                "Hardware protocol must be confirmed first."
            )

        self.protocol_configured = True

    def disable_protocol(self):

        self.protocol_configured = False
