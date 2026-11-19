
from collections import deque
from typing import Optional


class GestureProcessor:
    """
    Processes gesture predictions and maintains stable
    gesture recognition across consecutive frames.
    """

    def __init__(
        self,
        history_size=7,
        minimum_votes=4,
        confidence_threshold=0.70
    ):
        self.history = deque(maxlen=history_size)
        self.minimum_votes = minimum_votes
        self.confidence_threshold = confidence_threshold

        self.current_gesture = None
        self.previous_gesture = None

    # --------------------------------------------------
    # PROCESS PREDICTION
    # --------------------------------------------------

    def process(self, prediction: dict) -> dict:

        if not prediction:
            return self._unknown_result()

        gesture = prediction.get("gesture", "Unknown")
        confidence = float(prediction.get("confidence", 0.0))

        if (
            gesture in ["Unknown", "Unstable", None]
            or confidence < self.confidence_threshold
        ):
            return self._unknown_result()

        self.history.append(gesture)

        if not self.history:
            return self._unknown_result()

        stable_gesture = max(
            set(self.history),
            key=self.history.count
        )

        vote_count = self.history.count(stable_gesture)

        if vote_count < self.minimum_votes:
            return {
                "gesture": "Unstable",
                "confidence": confidence,
                "stable": False,
                "changed": False
            }

        self.previous_gesture = self.current_gesture
        changed = stable_gesture != self.current_gesture

        self.current_gesture = stable_gesture

        return {
            "gesture": stable_gesture,
            "confidence": confidence,
            "stable": True,
            "changed": changed
        }

    # --------------------------------------------------
    # UNKNOWN RESULT
    # --------------------------------------------------

    def _unknown_result(self) -> dict:

        self.history.clear()

        return {
            "gesture": "Unknown",
            "confidence": 0.0,
            "stable": False,
            "changed": False
        }

    # --------------------------------------------------
    # GET CURRENT GESTURE
    # --------------------------------------------------

    def get_current_gesture(self) -> Optional[str]:
        return self.current_gesture

    # --------------------------------------------------
    # RESET PROCESSOR
    # --------------------------------------------------

    def reset(self):

        self.history.clear()

        self.current_gesture = None
        self.previous_gesture = None
