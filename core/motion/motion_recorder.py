
import time
import threading
from copy import deepcopy


class MotionRecorder:
    """
    Records continuous hand movement frames.

    Each frame contains:
        timestamp
        hands
            handedness
            finger_curls

    Finger order:
        thumb, index, middle, ring, little

    Curl values:
        0   = open
        100 = closed
    """

    FINGERS = (
        "thumb",
        "index",
        "middle",
        "ring",
        "little"
    )

    def __init__(self, target_fps=15):
        self.target_fps = float(target_fps)

        if self.target_fps <= 0:
            raise ValueError("target_fps must be greater than zero.")

        self.frame_interval = 1.0 / self.target_fps

        self.frames = []

        self._recording = False
        self._start_time = None
        self._last_frame_time = None
        self._lock = threading.RLock()

        self._total_frames_received = 0
        self._total_frames_recorded = 0

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    @classmethod
    def _validate_curls(cls, curls):
        if not isinstance(curls, dict):
            raise ValueError("finger_curls must be a dictionary.")

        validated = {}

        for finger in cls.FINGERS:
            if finger not in curls:
                raise ValueError(
                    f"Missing finger value: {finger}"
                )

            try:
                value = float(curls[finger])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid curl value for {finger}."
                ) from error

            if not 0 <= value <= 100:
                raise ValueError(
                    f"{finger} curl must be between 0 and 100."
                )

            validated[finger] = int(round(value))

        return validated

    @classmethod
    def _normalize_hand(cls, hand, index=0):
        """
        Convert a processed hand into a stable recording format.
        """

        if not isinstance(hand, dict):
            raise ValueError("Each hand must be a dictionary.")

        curls = cls._validate_curls(
            hand.get("finger_curls")
        )

        normalized = {
            "hand_id": hand.get("hand_id", index),
            "handedness": str(
                hand.get("handedness", "Unknown")
            ),
            "finger_curls": curls
        }

        return normalized

    @classmethod
    def _normalize_hands(cls, hands):
        if hands is None:
            return []

        if not isinstance(hands, (list, tuple)):
            raise ValueError("hands must be a list.")

        normalized = []

        for index, hand in enumerate(hands):
            normalized.append(
                cls._normalize_hand(hand, index)
            )

        return normalized

    # --------------------------------------------------
    # RECORDING CONTROL
    # --------------------------------------------------

    def start_recording(self):
        """
        Start a fresh recording session.
        """

        with self._lock:
            if self._recording:
                raise RuntimeError(
                    "A recording is already active."
                )

            self.frames = []

            self._recording = True
            self._start_time = time.perf_counter()
            self._last_frame_time = None

            self._total_frames_received = 0
            self._total_frames_recorded = 0

            return True

    def stop_recording(self):
        """
        Stop recording and return the completed motion.
        """

        with self._lock:
            if not self._recording:
                if self.frames:
                    return self._build_recording()

                raise RuntimeError(
                    "No active recording to stop."
                )

            end_time = time.perf_counter()

            self._recording = False

            duration = max(
                0.0,
                end_time - self._start_time
            )

            return {
                "frames": deepcopy(self.frames),
                "duration": round(duration, 4),
                "total_frames": len(self.frames),
                "target_fps": self.target_fps,
                "format_version": 2,
                "finger_order": list(self.FINGERS)
            }

    def clear_recording(self):
        """
        Remove all recorded frames.
        """

        with self._lock:
            if self._recording:
                raise RuntimeError(
                    "Stop the recording before clearing it."
                )

            self.frames = []

            self._start_time = None
            self._last_frame_time = None

            self._total_frames_received = 0
            self._total_frames_recorded = 0

            return True

    # --------------------------------------------------
    # FRAME CAPTURE
    # --------------------------------------------------

    def record_frame(self, processed_hands, gesture=None):
        """
        Record one processed camera frame.

        processed_hands example:
            [
                {
                    "handedness": "Right",
                    "finger_curls": {
                        "thumb": 10,
                        "index": 20,
                        "middle": 30,
                        "ring": 40,
                        "little": 50
                    }
                }
            ]

        Frames without a detected hand are also recorded.
        This preserves the timing of tracking gaps.
        """

        with self._lock:
            if not self._recording:
                return False

            self._total_frames_received += 1

            now = time.perf_counter()

            elapsed = now - self._start_time

            if self._last_frame_time is not None:
                elapsed_since_last = (
                    now - self._last_frame_time
                )

                if elapsed_since_last < self.frame_interval:
                    return False

            hands = self._normalize_hands(processed_hands)

            frame = {
                "timestamp": round(elapsed, 4),
                "hands": hands
            }

            if gesture is not None:
                frame["gesture"] = deepcopy(gesture)

            self.frames.append(frame)

            self._last_frame_time = now
            self._total_frames_recorded += 1

            return True

    # --------------------------------------------------
    # RECORDING INFORMATION
    # --------------------------------------------------

    def _build_recording(self):
        if self._start_time is None:
            duration = 0.0
        else:
            duration = max(
                0.0,
                time.perf_counter() - self._start_time
            )

        return {
            "frames": deepcopy(self.frames),
            "duration": round(duration, 4),
            "total_frames": len(self.frames),
            "target_fps": self.target_fps,
            "format_version": 2,
            "finger_order": list(self.FINGERS)
        }

    def is_recording(self):
        with self._lock:
            return self._recording

    def get_frame_count(self):
        with self._lock:
            return len(self.frames)

    def get_duration(self):
        with self._lock:
            if self._start_time is None:
                return 0.0

            end = (
                time.perf_counter()
                if self._recording
                else self._last_frame_time
            )

            if end is None:
                return 0.0

            return max(0.0, end - self._start_time)

    def get_status(self):
        with self._lock:
            return {
                "recording": self._recording,
                "frame_count": len(self.frames),
                "target_fps": self.target_fps,
                "duration": self.get_duration(),
                "frames_received": self._total_frames_received,
                "frames_recorded": self._total_frames_recorded
            }

    # --------------------------------------------------
    # EXPORT
    # --------------------------------------------------

    def get_recording(self):
        """
        Return a safe copy of the current recording.
        """

        with self._lock:
            return self._build_recording()

    def export_frames(self):
        with self._lock:
            return deepcopy(self.frames)
