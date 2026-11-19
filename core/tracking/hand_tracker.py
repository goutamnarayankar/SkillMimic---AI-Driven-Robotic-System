
import cv2
import mediapipe as mp


class HandTracker:

    def __init__(
        self,
        max_hands=1,
        detection_confidence=0.55,
        tracking_confidence=0.55
    ):
        self.max_hands = int(max_hands)
        self.detection_confidence = float(detection_confidence)
        self.tracking_confidence = float(tracking_confidence)

        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

        self.connections = self.mp_hands.HAND_CONNECTIONS

    def detect(self, frame):

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = self.hands.process(rgb_frame)

        detected_hands = []

        if results.multi_hand_landmarks:

            handedness = results.multi_handedness or []

            for hand_index, hand_landmarks in enumerate(
                results.multi_hand_landmarks
            ):

                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.connections
                )

                points = []

                for index, point in enumerate(
                    hand_landmarks.landmark
                ):
                    points.append({
                        "id": index,
                        "x": float(point.x),
                        "y": float(point.y),
                        "z": float(point.z)
                    })

                hand_label = "Unknown"

                if hand_index < len(handedness):
                    hand_label = (
                        handedness[hand_index]
                        .classification[0].label
                    )

                detected_hands.append({
                    "hand_id": hand_index,
                    "handedness": hand_label,
                    "landmarks": points
                })

        return frame, detected_hands

    def close(self):
        if self.hands:
            self.hands.close()
