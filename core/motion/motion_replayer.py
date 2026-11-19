
"""
SkillMimic - Motion Replayer

Replays recorded hand movements through MotionController.

Features:
- Timestamp-based playback
- Adjustable playback speed
- Pause and resume
- Stop playback
- Optional looping
- FIFO movement submission
- Supports continuous finger values from 0 to 100

Hardware limitation:
This module sends estimated target values. The glove does not have
finger position sensors, so actual physical finger positions cannot
be confirmed by software.
"""

import threading
import time

from core.motion.motion_processor import MotionProcessor


class MotionReplayer:

    FINGER_ORDER = (
        "thumb",
        "index",
        "middle",
        "ring",
        "little",
    )

    def __init__(self, motion_controller=None):
        self.motion_controller = motion_controller

        self.processor = MotionProcessor()

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.RLock()

        self._motion_data = None
        self._playback_speed = 1.0
        self._loop = False

        self._state = "idle"
        self._current_frame = 0
        self._total_frames = 0
        self._last_error = None
        self._started_at = None

    def set_motion_controller(self, motion_controller):
        with self._lock:
            self.motion_controller = motion_controller

    def load_motion(self, motion_data):
        """
        Validate and load motion data before playback.
        """
        processed = self.processor.process_recording(motion_data)

        with self._lock:
            if self._state == "playing":
                raise RuntimeError(
                    "Stop the current playback before loading another skill."
                )

            self._motion_data = processed
            self._current_frame = 0
            self._total_frames = len(processed["frames"])
            self._last_error = None
            self._state = "loaded"

        return True

    def play(self, motion_data=None, speed=1.0, loop=False):
        """
        Start playback.

        Args:
            motion_data: Optional processed recording dictionary.
            speed: Playback speed. 1.0 = original speed.
                   0.5 = half speed. 2.0 = double speed.
            loop: Repeat playback when it reaches the end.
        """
        if motion_data is not None:
            self.load_motion(motion_data)

        with self._lock:
            if self._motion_data is None:
                raise ValueError("No motion is loaded.")

            if self.motion_controller is None:
                raise RuntimeError("MotionController is not configured.")

            if self._state == "playing":
                return False

            if not isinstance(speed, (int, float)) or isinstance(speed, bool):
                raise ValueError("Playback speed must be a number.")

            if speed <= 0 or speed > 5:
                raise ValueError("Playback speed must be greater than 0 and at most 5.")

            self._playback_speed = float(speed)
            self._loop = bool(loop)

            self._stop_event.clear()
            self._pause_event.clear()

            self._current_frame = 0
            self._last_error = None
            self._state = "playing"

            self._thread = threading.Thread(
                target=self._playback_worker,
                name="SkillMimic-MotionReplayer",
                daemon=True,
            )

            self._thread.start()

        return True

    def pause(self):
        with self._lock:
            if self._state != "playing":
                return False

            self._pause_event.set()
            self._state = "paused"

        return True

    def resume(self):
        with self._lock:
            if self._state != "paused":
                return False

            self._pause_event.clear()
            self._state = "playing"

        return True

    def stop(self, wait=True):
        """
        Stop playback.

        This stops further frame submission. A movement already accepted
        by the controller may still be in progress. Use the controller's
        emergency-stop function if an immediate hardware stop is required.
        """
        self._stop_event.set()
        self._pause_event.clear()

        thread = self._thread

        if wait and thread is not None and thread.is_alive():
            if thread is not threading.current_thread():
                thread.join(timeout=5.0)

        with self._lock:
            if self._state in ("playing", "paused"):
                self._state = "stopped"

        return True

    def _wait_if_paused(self):
        while self._pause_event.is_set():
            if self._stop_event.is_set():
                return False

            time.sleep(0.05)

        return not self._stop_event.is_set()

    def _wait_until(self, target_time):
        """
        Wait until the scheduled time while remaining responsive
        to pause and stop requests.
        """
        while not self._stop_event.is_set():
            if not self._wait_if_paused():
                return False

            remaining = target_time - time.monotonic()

            if remaining <= 0:
                return True

            time.sleep(min(remaining, 0.05))

        return False

    def _wait_for_controller(self):
        """
        Wait for the previous movement to finish before submitting
        the next frame. This preserves replay order and avoids
        building a queue of outdated movements.
        """
        controller = self.motion_controller

        wait_method = getattr(controller, "wait_until_idle", None)

        if not callable(wait_method):
            return True

        while not self._stop_event.is_set():
            if not self._wait_if_paused():
                return False

            try:
                result = wait_method(timeout=0.5)
            except TypeError:
                result = wait_method()

            if result is not False:
                return True

        return False

    def _get_frame_targets(self, frame):
        """
        Return the first tracked hand's five finger targets.

        This project currently controls one pneumatic glove.
        Empty-hand frames are skipped without inventing targets.
        """
        hands = frame.get("hands", [])

        if not hands:
            return None

        hand = hands[0]
        curls = hand.get("finger_curls", {})

        return {
            finger: int(round(float(curls[finger])))
            for finger in self.FINGER_ORDER
        }

    def _submit_frame(self, targets):
        """
        Send one frame to MotionController.

        submit_targets() is used instead of submit_latest_targets()
        because replay must preserve chronological frame order.
        """
        controller = self.motion_controller

        submit_method = getattr(controller, "submit_targets", None)

        if not callable(submit_method):
            raise RuntimeError(
                "MotionController does not provide submit_targets()."
            )

        # Replay owns the controller while playback is active. Passing the
        # explicit source is essential: the default "manual" source is rejected.
        result = submit_method(targets, source="skill_replay")

        if result is False:
            raise RuntimeError(
                "MotionController rejected a replay movement."
            )

        return result

    def _playback_worker(self):
        try:
            frames = self._motion_data["frames"]

            while not self._stop_event.is_set():

                if not self._wait_if_paused():
                    break

                playback_start = time.monotonic()
                first_timestamp = float(frames[0]["timestamp"])
                last_submitted_targets = None

                for index, frame in enumerate(frames):

                    if self._stop_event.is_set():
                        break

                    if not self._wait_if_paused():
                        break

                    timestamp = float(frame["timestamp"])
                    relative_time = timestamp - first_timestamp

                    scheduled_time = (
                        playback_start
                        + relative_time / self._playback_speed
                    )

                    if not self._wait_until(scheduled_time):
                        break

                    targets = self._get_frame_targets(frame)

                    with self._lock:
                        self._current_frame = index + 1

                    # Preserve the recorded timeline, including frames
                    # where the hand was temporarily not detected.
                    if targets is None:
                        continue

                    # Skip repeated or imperceptibly small frame changes.
                    # This prevents a 15-FPS recording from flooding a
                    # pneumatic actuator that needs time to complete each move.
                    if last_submitted_targets is not None:
                        max_delta = max(
                            abs(targets[finger] - last_submitted_targets[finger])
                            for finger in self.FINGER_ORDER
                        )
                        if max_delta < 3:
                            continue

                    if not self._wait_for_controller():
                        break

                    if self._stop_event.is_set():
                        break

                    self._submit_frame(targets)
                    last_submitted_targets = dict(targets)

                if self._stop_event.is_set():
                    break

                if not self._loop:
                    break

            # Wait for the last accepted movement to finish.
            if not self._stop_event.is_set():
                self._wait_for_controller()

            with self._lock:
                if self._stop_event.is_set():
                    self._state = "stopped"
                else:
                    self._state = "completed"
                    self._current_frame = self._total_frames

        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
                self._state = "error"

    def seek(self, frame_index):
        """
        Set the playback starting frame.

        Seeking is allowed only when playback is not active.
        """
        with self._lock:
            if self._state in ("playing", "paused"):
                raise RuntimeError(
                    "Stop playback before seeking."
                )

            if self._motion_data is None:
                raise RuntimeError("No motion is loaded.")

            if not isinstance(frame_index, int):
                raise ValueError("Frame index must be an integer.")

            if frame_index < 0 or frame_index >= self._total_frames:
                raise ValueError("Frame index is outside the recording.")

            self._current_frame = frame_index
            self._state = "loaded"

        return True

    def get_progress(self):
        with self._lock:
            if self._total_frames == 0:
                return 0.0

            return min(
                100.0,
                (self._current_frame / self._total_frames) * 100.0,
            )

    def is_playing(self):
        with self._lock:
            return self._state == "playing"

    def is_paused(self):
        with self._lock:
            return self._state == "paused"

    def is_finished(self):
        with self._lock:
            return self._state == "completed"

    def get_status(self):
        with self._lock:
            return {
                "state": self._state,
                "is_playing": self._state == "playing",
                "is_paused": self._state == "paused",
                "is_finished": self._state == "completed",
                "current_frame": self._current_frame,
                "total_frames": self._total_frames,
                "progress": self.get_progress(),
                "playback_speed": self._playback_speed,
                "loop": self._loop,
                "last_error": self._last_error,
            }

    def reset(self):
        self.stop(wait=True)

        with self._lock:
            self._motion_data = None
            self._current_frame = 0
            self._total_frames = 0
            self._last_error = None
            self._state = "idle"
            self._started_at = None

        self.processor.reset()
