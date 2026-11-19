
class InverseKinematics:

    DEFAULT_LIMITS = {
        "thumb": {
            "pip": (0, 90),
            "dip": (0, 90)
        },
        "index": {
            "pip": (0, 110),
            "dip": (0, 90)
        },
        "middle": {
            "pip": (0, 110),
            "dip": (0, 90)
        },
        "ring": {
            "pip": (0, 110),
            "dip": (0, 90)
        },
        "little": {
            "pip": (0, 110),
            "dip": (0, 90)
        }
    }

    def __init__(self, joint_limits=None):

        self.joint_limits = (
            joint_limits
            if joint_limits is not None
            else self.DEFAULT_LIMITS
        )

    def clamp(self, value, minimum, maximum):

        return max(minimum, min(maximum, value))

    def normalize_angle(self, angle, minimum, maximum):

        angle = self.clamp(angle, minimum, maximum)

        if maximum == minimum:
            return 0.0

        return (
            (angle - minimum) / (maximum - minimum)
        ) * 100.0

    def calculate_targets(self, hand_angles):

        targets = {}

        for finger, joints in hand_angles["fingers"].items():

            finger_targets = {}

            for joint, angle in joints.items():

                minimum, maximum = self.joint_limits[finger][joint]

                finger_targets[joint] = round(
                    self.normalize_angle(
                        angle,
                        minimum,
                        maximum
                    ),
                    2
                )

            targets[finger] = finger_targets

        return {
            "hand_id": hand_angles["hand_id"],
            "handedness": hand_angles["handedness"],
            "targets": targets
        }

    def calculate(self, hand_angles_list):

        return [
            self.calculate_targets(hand_angles)
            for hand_angles in hand_angles_list
        ]
