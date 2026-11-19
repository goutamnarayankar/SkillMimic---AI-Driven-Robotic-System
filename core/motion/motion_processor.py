
"""
SkillMimic - Motion Processor

Validates and prepares recorded hand motion for storage and replay.

Input format:
{
    "frames": [
        {
            "timestamp": 0.0,
            "hands": [
                {
                    "hand_id": 0,
                    "handedness": "Right",
                    "finger_curls": {
                        "thumb": 0,
                        "index": 20,
                        "middle": 40,
                        "ring": 60,
                        "little": 80
                    }
                }
            ]
        }
    ],
    "duration": 2.0,
    "total_frames": 30,
    "target_fps": 15
}
"""

from copy import deepcopy
from numbers import Real


class MotionProcessor:
    FINGER_ORDER = (
        "thumb",
        "index",
        "middle",
        "ring",
        "little",
    )

    def __init__(self):
        self.last_error = None
        self.last_result = None

    @staticmethod
    def _is_number(value):
        return isinstance(value, Real) and not isinstance(value, bool)

    def _normalize_curl(self, value, finger_name):
        if not self._is_number(value):
            raise ValueError(
                f"Invalid curl value for '{finger_name}': {value}"
            )

        value = float(value)

        if value < 0 or value > 100:
            raise ValueError(
                f"'{finger_name}' curl must be between 0 and 100."
            )

        return int(round(value))

    def validate_recording(self, recording):
        if not isinstance(recording, dict):
            raise ValueError("Recording must be a dictionary.")

        frames = recording.get("frames")

        if not isinstance(frames, list) or not frames:
            raise ValueError("Recording contains no frames.")

        previous_timestamp = -1.0

        for frame_index, frame in enumerate(frames):
            if not isinstance(frame, dict):
                raise ValueError(
                    f"Frame {frame_index} must be a dictionary."
                )

            timestamp = frame.get("timestamp")

            if not self._is_number(timestamp):
                raise ValueError(
                    f"Frame {frame_index} has an invalid timestamp."
                )

            timestamp = float(timestamp)

            if timestamp < 0:
                raise ValueError(
                    f"Frame {frame_index} has a negative timestamp."
                )

            if timestamp < previous_timestamp:
                raise ValueError(
                    "Frame timestamps must be in chronological order."
                )

            previous_timestamp = timestamp

            hands = frame.get("hands")

            if not isinstance(hands, list):
                raise ValueError(
                    f"Frame {frame_index} must contain a hands list."
                )

            for hand_index, hand in enumerate(hands):
                if not isinstance(hand, dict):
                    raise ValueError(
                        f"Invalid hand in frame {frame_index}."
                    )

                curls = hand.get("finger_curls")

                if not isinstance(curls, dict):
                    raise ValueError(
                        f"Hand {hand_index} in frame {frame_index} "
                        "has no finger_curls dictionary."
                    )

                for finger in self.FINGER_ORDER:
                    if finger not in curls:
                        raise ValueError(
                            f"Missing '{finger}' value in frame "
                            f"{frame_index}."
                        )

                    self._normalize_curl(curls[finger], finger)

        return True

    def process_recording(self, recording):
        """
        Validate and normalize a complete recording.

        Empty-hand frames are preserved so tracking gaps remain
        represented in the original timeline.
        """
        self.last_error = None

        try:
            self.validate_recording(recording)

            processed = deepcopy(recording)
            processed_frames = []

            for frame in processed["frames"]:
                processed_hands = []

                for hand in frame["hands"]:
                    processed_hand = deepcopy(hand)

                    processed_hand["finger_curls"] = {
                        finger: self._normalize_curl(
                            hand["finger_curls"][finger],
                            finger,
                        )
                        for finger in self.FINGER_ORDER
                    }

                    processed_hands.append(processed_hand)

                processed_frames.append({
                    "timestamp": float(frame["timestamp"]),
                    "hands": processed_hands,
                })

            processed["frames"] = processed_frames
            processed["total_frames"] = len(processed_frames)
            processed["finger_order"] = list(self.FINGER_ORDER)
            processed["format_version"] = 2

            if len(processed_frames) > 1:
                calculated_duration = (
                    processed_frames[-1]["timestamp"]
                    - processed_frames[0]["timestamp"]
                )
            else:
                calculated_duration = 0.0

            original_duration = recording.get("duration")

            if self._is_number(original_duration) and original_duration >= 0:
                processed["duration"] = max(
                    float(original_duration),
                    calculated_duration,
                )
            else:
                processed["duration"] = calculated_duration

            self.last_result = processed
            return processed

        except Exception as exc:
            self.last_error = str(exc)
            raise

    def process_frames(self, frames):
        """Process a frames list directly."""
        return self.process_recording({
            "frames": frames,
        })

    def reset(self):
        self.last_error = None
        self.last_result = None

    def get_status(self):
        return {
            "ready": self.last_result is not None,
            "last_error": self.last_error,
            "frame_count": (
                len(self.last_result["frames"])
                if self.last_result else 0
            ),
        }
