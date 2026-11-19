
import math


class LandmarkProcessor:
    """
    Converts MediaPipe's 21 hand landmarks into five independent
    finger-curl targets in the range 0-100.

    Finger order:
        thumb, index, middle, ring, little

    0   = open
    100 = closed
    """

    FINGERS = ("thumb", "index", "middle", "ring", "little")

    # MediaPipe landmark indices
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4

    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8

    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12

    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16

    LITTLE_MCP = 17
    LITTLE_PIP = 18
    LITTLE_DIP = 19
    LITTLE_TIP = 20

    def __init__(
        self,
        smoothing=0.35,
        deadband=1.5,
        min_angle=45.0,
        max_angle=165.0
    ):
        self.smoothing = float(smoothing)
        self.deadband = float(deadband)
        self.min_angle = float(min_angle)
        self.max_angle = float(max_angle)

        if not 0 < self.smoothing <= 1:
            raise ValueError("smoothing must be greater than 0 and at most 1.")

        if self.min_angle >= self.max_angle:
            raise ValueError("min_angle must be smaller than max_angle.")

        self._smoothed = {}
        self._last_output = {}
        # Per-finger raw-curl endpoints captured from the user's own hand.
        # Until calibrated, the original geometric estimate is returned.
        self._calibration = {}

    # --------------------------------------------------
    # BASIC GEOMETRY
    # --------------------------------------------------

    @staticmethod
    def _point(landmark):
        """Normalize MediaPipe objects, HandTracker dictionaries, or coordinate rows."""

        if isinstance(landmark, dict):
            if "x" not in landmark or "y" not in landmark:
                raise ValueError("Landmark dictionary must contain x and y.")
            x = float(landmark["x"])
            y = float(landmark["y"])
            z = float(landmark.get("z", 0.0))

        elif hasattr(landmark, "x") and hasattr(landmark, "y"):
            x = float(landmark.x)
            y = float(landmark.y)
            z = float(getattr(landmark, "z", 0.0))

        else:
            try:
                coordinates = list(landmark)
            except (TypeError, ValueError):
                raise ValueError("Invalid landmark coordinate.")

            if len(coordinates) < 2:
                raise ValueError("Landmark coordinate needs at least x and y.")

            x = float(coordinates[0])
            y = float(coordinates[1])
            z = float(coordinates[2]) if len(coordinates) >= 3 else 0.0

        point = (x, y, z)
        if not all(math.isfinite(value) for value in point):
            raise ValueError("Landmark contains a non-finite coordinate.")
        return point

    @classmethod
    def _distance(cls, first, second):
        a = cls._point(first)
        b = cls._point(second)

        return math.sqrt(
            (a[0] - b[0]) ** 2
            + (a[1] - b[1]) ** 2
            + (a[2] - b[2]) ** 2
        )

    @classmethod
    def _angle(cls, first, middle, last):
        """
        Calculate the angle at the middle landmark.
        """

        a = cls._point(first)
        b = cls._point(middle)
        c = cls._point(last)

        vector_1 = (
            a[0] - b[0],
            a[1] - b[1],
            a[2] - b[2]
        )

        vector_2 = (
            c[0] - b[0],
            c[1] - b[1],
            c[2] - b[2]
        )

        dot = sum(
            vector_1[i] * vector_2[i]
            for i in range(3)
        )

        length_1 = math.sqrt(
            sum(value * value for value in vector_1)
        )

        length_2 = math.sqrt(
            sum(value * value for value in vector_2)
        )

        if length_1 == 0 or length_2 == 0:
            return 180.0

        cosine = dot / (length_1 * length_2)
        cosine = max(-1.0, min(1.0, cosine))

        return math.degrees(math.acos(cosine))

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    # --------------------------------------------------
    # LANDMARK INPUT NORMALIZATION
    # --------------------------------------------------

    @staticmethod
    def _extract_landmarks(hand):
        """
        Supports:
          - A list/tuple containing 21 landmarks
          - MediaPipe hand_landmarks objects
          - Dictionaries containing 'landmarks'
          - Dictionaries containing 'landmark_list'
        """

        if isinstance(hand, dict):
            landmarks = hand.get("landmarks")

            if landmarks is None:
                landmarks = hand.get("landmark_list")

            if landmarks is None:
                landmarks = hand.get("hand_landmarks")

        elif hasattr(hand, "landmark"):
            landmarks = hand.landmark

        else:
            landmarks = hand

        if hasattr(landmarks, "landmark"):
            landmarks = landmarks.landmark

        if landmarks is None:
            raise ValueError("No hand landmarks were supplied.")

        if not isinstance(landmarks, (list, tuple)):
            try:
                landmarks = list(landmarks)
            except (TypeError, ValueError):
                raise ValueError("Hand landmarks must contain 21 points.")

        if len(landmarks) != 21:
            raise ValueError(
                "Expected exactly 21 MediaPipe hand landmarks; "
                f"received {len(landmarks)}."
            )

        # Validate every point before processing.
        for landmark in landmarks:
            point = LandmarkProcessor._point(landmark)

            if not all(math.isfinite(value) for value in point):
                raise ValueError("Landmark contains a non-finite value.")

        return landmarks

    # --------------------------------------------------
    # CURL CALCULATION
    # --------------------------------------------------

    def _angle_to_curl(self, angle):
        """
        Convert finger joint angle into a curl percentage.
        A straighter finger has a larger angle and lower curl.
        """

        ratio = (
            self.max_angle - angle
        ) / (
            self.max_angle - self.min_angle
        )

        return self._clamp(ratio * 100.0, 0.0, 100.0)

    def _finger_curl(self, landmarks, mcp, pip, dip, tip):
        """
        Combine PIP and DIP joint bending.
        """

        pip_angle = self._angle(
            landmarks[mcp],
            landmarks[pip],
            landmarks[dip]
        )

        dip_angle = self._angle(
            landmarks[pip],
            landmarks[dip],
            landmarks[tip]
        )

        pip_curl = self._angle_to_curl(pip_angle)
        dip_curl = self._angle_to_curl(dip_angle)

        return (
            0.70 * pip_curl
            + 0.30 * dip_curl
        )

    def _thumb_curl(self, landmarks):
        """
        Thumb curl uses MCP/IP bending and thumb-tip distance
        relative to the palm size.
        """

        mcp_angle = self._angle(
            landmarks[self.THUMB_CMC],
            landmarks[self.THUMB_MCP],
            landmarks[self.THUMB_IP]
        )

        ip_angle = self._angle(
            landmarks[self.THUMB_MCP],
            landmarks[self.THUMB_IP],
            landmarks[self.THUMB_TIP]
        )

        angle_curl = (
            0.45 * self._angle_to_curl(mcp_angle)
            + 0.55 * self._angle_to_curl(ip_angle)
        )

        palm_size = self._distance(
            landmarks[self.INDEX_MCP],
            landmarks[self.LITTLE_MCP]
        )

        if palm_size < 1e-6:
            raise ValueError("Invalid palm size in landmarks.")

        thumb_tip_distance = self._distance(
            landmarks[self.THUMB_TIP],
            landmarks[self.INDEX_MCP]
        )

        # A thumb tip moving toward the index MCP generally
        # indicates thumb flexion/adduction.
        normalized_distance = thumb_tip_distance / palm_size

        position_curl = self._clamp(
            (1.35 - normalized_distance) / 0.95 * 100.0,
            0.0,
            100.0
        )

        return (
            0.65 * angle_curl
            + 0.35 * position_curl
        )

    # --------------------------------------------------
    # PER-FINGER CALIBRATION
    # --------------------------------------------------

    def _raw_curls(self, landmarks):
        return {
            "thumb": self._thumb_curl(landmarks),
            "index": self._finger_curl(landmarks, self.INDEX_MCP, self.INDEX_PIP, self.INDEX_DIP, self.INDEX_TIP),
            "middle": self._finger_curl(landmarks, self.MIDDLE_MCP, self.MIDDLE_PIP, self.MIDDLE_DIP, self.MIDDLE_TIP),
            "ring": self._finger_curl(landmarks, self.RING_MCP, self.RING_PIP, self.RING_DIP, self.RING_TIP),
            "little": self._finger_curl(landmarks, self.LITTLE_MCP, self.LITTLE_PIP, self.LITTLE_DIP, self.LITTLE_TIP),
        }

    def calibrate_open(self, hand):
        """Capture the current stable pose as the 0% reference for each finger."""
        raw = self._raw_curls(self._extract_landmarks(hand))
        for finger, value in raw.items():
            current = self._calibration.setdefault(finger, {})
            current["open"] = float(value)
        self.reset()
        return dict(raw)

    def calibrate_closed(self, hand):
        """Capture the current stable fist pose as the 100% reference."""
        raw = self._raw_curls(self._extract_landmarks(hand))
        for finger, value in raw.items():
            current = self._calibration.setdefault(finger, {})
            current["closed"] = float(value)
            if "open" in current and abs(current["closed"] - current["open"]) < 2.0:
                raise ValueError(
                    f"{finger} calibration range is too small; repeat open and closed poses."
                )
        self.reset()
        return dict(raw)

    def clear_calibration(self):
        self._calibration.clear()
        self.reset()

    def get_calibration_status(self):
        return {
            finger: {
                "open": self._calibration.get(finger, {}).get("open"),
                "closed": self._calibration.get(finger, {}).get("closed"),
                "ready": (
                    "open" in self._calibration.get(finger, {})
                    and "closed" in self._calibration.get(finger, {})
                    and abs(
                        self._calibration[finger]["closed"]
                        - self._calibration[finger]["open"]
                    ) >= 2.0
                ),
            }
            for finger in self.FINGERS
        }

    def _apply_calibration(self, finger, raw_value):
        calibration = self._calibration.get(finger, {})
        if "open" not in calibration or "closed" not in calibration:
            return self._clamp(raw_value, 0.0, 100.0)

        open_value = calibration["open"]
        closed_value = calibration["closed"]
        span = closed_value - open_value
        if abs(span) < 2.0:
            return self._clamp(raw_value, 0.0, 100.0)

        return self._clamp((raw_value - open_value) / span * 100.0, 0.0, 100.0)

    # --------------------------------------------------
    # SMOOTHING
    # --------------------------------------------------

    def _smooth(self, finger, value):
        previous = self._smoothed.get(finger)

        if previous is None:
            smoothed = value
        else:
            smoothed = (
                self.smoothing * value
                + (1.0 - self.smoothing) * previous
            )

        self._smoothed[finger] = smoothed

        previous_output = self._last_output.get(finger)

        if (
            previous_output is not None
            and abs(smoothed - previous_output) < self.deadband
        ):
            return int(round(previous_output))

        output = int(round(self._clamp(smoothed, 0.0, 100.0)))

        self._last_output[finger] = float(output)

        return output

    # --------------------------------------------------
    # PUBLIC PROCESSING API
    # --------------------------------------------------

    def process(self, hand):
        """
        Process one hand and return:

        {
            'finger_curls': {
                'thumb': 0,
                'index': 0,
                'middle': 0,
                'ring': 0,
                'little': 0
            }
        }
        """

        landmarks = self._extract_landmarks(hand)

        raw_curls = self._raw_curls(landmarks)
        calibrated_curls = {
            finger: self._apply_calibration(finger, value)
            for finger, value in raw_curls.items()
        }

        finger_curls = {
            finger: self._smooth(finger, calibrated_curls[finger])
            for finger in self.FINGERS
        }

        return {
            "finger_curls": finger_curls
        }

    def process_hand(self, hand):
        """
        Compatibility alias.
        """

        return self.process(hand)

    def reset(self):
        """
        Clear smoothing history when tracking is restarted
        or the tracked hand changes.
        """

        self._smoothed.clear()
        self._last_output.clear()

    def reset_smoothing(self):
        self.reset()
