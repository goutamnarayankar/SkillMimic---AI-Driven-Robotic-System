
import math


class JointAngleCalculator:

    FINGER_JOINTS = {
        "thumb": (1, 2, 3, 4),
        "index": (5, 6, 7, 8),
        "middle": (9, 10, 11, 12),
        "ring": (13, 14, 15, 16),
        "little": (17, 18, 19, 20)
    }

    def calculate_angle(self, point_a, point_b, point_c):

        vector1 = [
            point_a["x"] - point_b["x"],
            point_a["y"] - point_b["y"],
            point_a["z"] - point_b["z"]
        ]

        vector2 = [
            point_c["x"] - point_b["x"],
            point_c["y"] - point_b["y"],
            point_c["z"] - point_b["z"]
        ]

        dot_product = sum(
            a * b for a, b in zip(vector1, vector2)
        )

        magnitude1 = math.sqrt(
            sum(a * a for a in vector1)
        )

        magnitude2 = math.sqrt(
            sum(b * b for b in vector2)
        )

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        cosine = dot_product / (magnitude1 * magnitude2)
        cosine = max(-1.0, min(1.0, cosine))

        return math.degrees(math.acos(cosine))

    def calculate_finger_angles(self, landmarks):

        finger_angles = {}

        for finger, joints in self.FINGER_JOINTS.items():

            mcp, pip, dip, tip = joints

            pip_angle = self.calculate_angle(
                landmarks[mcp],
                landmarks[pip],
                landmarks[dip]
            )

            dip_angle = self.calculate_angle(
                landmarks[pip],
                landmarks[dip],
                landmarks[tip]
            )

            finger_angles[finger] = {
                "pip": round(pip_angle, 2),
                "dip": round(dip_angle, 2)
            }

        return finger_angles

    def calculate_hand_angles(self, hand_data):

        landmarks = hand_data["landmarks"]

        return {
            "hand_id": hand_data["hand_id"],
            "handedness": hand_data["handedness"],
            "fingers": self.calculate_finger_angles(landmarks)
        }
