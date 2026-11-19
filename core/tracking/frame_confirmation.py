
import math


class ThreeFrameConfirmation:
    """
    Confirms a tracked hand over three consecutive valid frames.

    The third frame is used as the initial target.
    Frames 1 and 2 never produce hardware commands.
    """

    FINGER_ORDER = (
        "thumb",
        "index",
        "middle",
        "ring",
        "little",
    )

    REQUIRED_FRAMES = 3

    def __init__(self):
        self.reset()

    def reset(self):
        self.valid_frames = 0
        self.hand_id = None
        self.confirmed = False

    def _read_targets(self, hand):
        curls = hand.get("finger_curls")

        if not isinstance(curls, dict):
            return None

        values = []

        for finger in self.FINGER_ORDER:
            if finger not in curls:
                return None

            try:
                value = float(curls[finger])
            except (TypeError, ValueError):
                return None

            if not math.isfinite(value) or not 0 <= value <= 100:
                return None

            values.append(round(value, 1))

        landmarks = hand.get("landmarks", [])

        if len(landmarks) != 21:
            return None

        for point in landmarks:
            for axis in ("x", "y", "z"):
                try:
                    coordinate = float(point[axis])
                except (KeyError, TypeError, ValueError):
                    return None

                if not math.isfinite(coordinate):
                    return None

        return values

    def update(self, hands):
        """
        Returns:
            None: waiting for confirmation or invalid tracking.
            dict: confirmed five-finger target.

        The first returned target is taken directly from frame 3.
        """

        if not hands:
            self.reset()
            return None

        # Use one consistent hand throughout confirmation.
        hand = hands[0]
        current_id = hand.get("hand_id")

        targets = self._read_targets(hand)

        if targets is None:
            self.reset()
            return None

        if self.hand_id is None:
            self.hand_id = current_id

        elif current_id != self.hand_id:
            self.reset()
            self.hand_id = current_id

        if not self.confirmed:
            self.valid_frames += 1

            if self.valid_frames < self.REQUIRED_FRAMES:
                return None

            # Exactly the third valid frame becomes the initial target.
            self.confirmed = True

        return {
            finger: targets[index]
            for index, finger in enumerate(self.FINGER_ORDER)
        }

    @property
    def status(self):
        if self.confirmed:
            return "Hand confirmed"

        return (
            f"Confirming hand: "
            f"{self.valid_frames}/{self.REQUIRED_FRAMES} frames"
        )
