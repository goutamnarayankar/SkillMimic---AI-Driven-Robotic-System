
import threading
import time
from collections import deque


class MotionController:
    """
    SkillMimic five-finger pneumatic controller.

    Packet:
        M,THUMB,INDEX,MIDDLE,RING,LITTLE

    Arduino responses:
        ACK,M
        MOVING,OPEN
        MOVING,CLOSE
        DONE,M

    Live Mirror:
        Keeps only the newest target while the glove is busy.

    Skill Replay:
        Preserves FIFO packet order.
    """

    FINGERS = ("thumb", "index", "middle", "ring", "little")
    SOURCES = ("manual", "live_mirror", "skill_replay")

    ACK_TIMEOUT = 6.0
    MOVEMENT_TIMEOUT_EXTRA = 8.0
    POLL_INTERVAL = 0.2

    def __init__(
        self,
        arduino=None,
        default_duration_ms=800,
        cooldown_seconds=0,
        movement_timeout=40
    ):
        self.arduino = arduino
        self.default_duration_ms = int(default_duration_ms)
        self.cooldown_seconds = float(cooldown_seconds)
        self.movement_timeout = float(movement_timeout)

        self._condition = threading.Condition(threading.RLock())
        self._queue = deque()

        self._running = False
        self._worker = None

        self._active = False
        self._phase = "idle"
        self._current_task = None

        self._completed_tasks = 0
        self._last_error = None
        self._last_result = None

        self._emergency_stopped = False
        # A controller fault is distinct from an operator-requested E-stop.
        # Faults block new commands but never silently send the firmware's
        # latched X command.
        self._faulted = False
        self._mode_owner = None
        self._release_when_idle = False

        self._latest_targets = None
        self._latest_target_source = None

        self._estimated_targets = {
            finger: 0 for finger in self.FINGERS
        }

    # =================================================
    # CONNECTION
    # =================================================

    def set_arduino(self, arduino):
        with self._condition:
            self.arduino = arduino
            self._condition.notify_all()

    def _require_connection(self):
        if self.arduino is None:
            raise ConnectionError("Arduino connection is not configured.")

        if not self.arduino.is_connected():
            raise ConnectionError("Arduino is not connected.")

    # =================================================
    # VALIDATION
    # =================================================

    @classmethod
    def validate_targets(cls, targets):
        if not isinstance(targets, dict):
            raise ValueError("Targets must be a dictionary.")

        result = {}

        for finger in cls.FINGERS:
            if finger not in targets:
                raise ValueError(f"Missing target for {finger}.")

            try:
                value = float(targets[finger])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid target for {finger}.") from exc

            if not 0 <= value <= 100:
                raise ValueError(f"{finger} must be between 0 and 100.")

            result[finger] = int(round(value))

        return result

    @classmethod
    def make_packet(cls, targets):
        values = cls.validate_targets(targets)
        return "M," + ",".join(
            str(values[finger]) for finger in cls.FINGERS
        )

    @classmethod
    def packet_to_targets(cls, packet):
        if not isinstance(packet, str):
            raise ValueError("Packet must be a string.")

        parts = packet.strip().split(",")

        if len(parts) != 6 or parts[0] != "M":
            raise ValueError(
                "Expected M,THUMB,INDEX,MIDDLE,RING,LITTLE."
            )

        return cls.validate_targets({
            finger: value
            for finger, value in zip(cls.FINGERS, parts[1:])
        })

    # =================================================
    # WORKER
    # =================================================

    def start(self):
        with self._condition:
            if self._running:
                return

            self._running = True
            self._worker = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="SkillMimicMotionWorker"
            )
            self._worker.start()

    # =================================================
    # MODE OWNERSHIP
    # =================================================

    def acquire_mode(self, mode):
        if mode not in self.SOURCES:
            raise ValueError("Unknown controller mode.")

        with self._condition:
            if self._emergency_stopped:
                raise RuntimeError("Emergency stop is active.")
            if self._faulted:
                raise RuntimeError(
                    "Controller fault is active. Inspect the glove and acknowledge the fault."
                )

            if self._mode_owner not in (None, mode):
                raise RuntimeError(
                    f"{self._mode_owner} currently owns the glove."
                )

            if self._active or self._queue or self._latest_targets is not None:
                if self._mode_owner != mode:
                    raise RuntimeError(
                        "Wait for the previous movement to finish."
                    )

            self._mode_owner = mode
            self._release_when_idle = False
            return True

    def release_mode(self, mode):
        with self._condition:
            if self._mode_owner != mode:
                return

            self._release_when_idle = True
            self._release_mode_if_idle()
            self._condition.notify_all()

    def _release_mode_if_idle(self):
        if (
            self._release_when_idle
            and not self._active
            and not self._queue
            and self._latest_targets is None
        ):
            self._mode_owner = None
            self._release_when_idle = False

    def _check_source(self, source):
        if source not in self.SOURCES:
            raise ValueError("Unknown movement source.")

        if self._emergency_stopped:
            raise RuntimeError("Emergency stop is active.")
        if self._faulted:
            raise RuntimeError(
                "Controller fault is active. Inspect the glove and acknowledge the fault."
            )

        if self._mode_owner not in (None, source):
            raise RuntimeError(
                f"{self._mode_owner} currently owns the glove."
            )

    # =================================================
    # SUBMIT TARGETS
    # =================================================

    def submit_latest_targets(
        self,
        targets,
        source="live_mirror",
        duration_ms=None
    ):
        """
        Live Mirror submission.

        Replaces any older pending Live Mirror target.
        It does not add every camera frame to the queue.
        """
        validated = self.validate_targets(targets)

        with self._condition:
            self._check_source(source)

            self._latest_targets = validated
            self._latest_target_source = source

            if not self._running:
                self.start()

            self._condition.notify_all()

        return True

    def submit_targets(
        self,
        targets,
        source="manual",
        duration_ms=None
    ):
        """
        Live Mirror is latest-wins; replay/manual commands are FIFO.
        This prevents recorded frames from being overwritten.
        """
        validated = self.validate_targets(targets)

        if source == "live_mirror":
            return self.submit_latest_targets(
                validated, source=source, duration_ms=duration_ms
            )

        if source not in self.SOURCES:
            raise ValueError("Unknown movement source.")

        with self._condition:
            self._check_source(source)
            self._queue.append({
                "source": source,
                "targets": validated,
                "duration_ms": duration_ms,
            })
            if not self._running:
                self.start()
            self._condition.notify_all()

        return True

    def submit_packet(self, packet, source="manual"):
        targets = self.packet_to_targets(packet)

        return self.submit_latest_targets(
            targets,
            source=source
        )

    # =================================================
    # FIFO SKILL REPLAY
    # =================================================

    def submit_packets(self, packets, source="skill_replay"):
        if source not in self.SOURCES:
            raise ValueError("Unknown movement source.")

        validated = [
            self.packet_to_targets(packet)
            for packet in packets
        ]

        if not validated:
            return 0

        with self._condition:
            self._check_source(source)

            for targets in validated:
                self._queue.append({
                    "source": source,
                    "targets": targets
                })

            if not self._running:
                self.start()

            self._condition.notify_all()

        return len(validated)

    def submit_events(
        self,
        events,
        source="skill_replay",
        preserve_timing=False
    ):
        """
        Compatibility helper for older replay pages.

        Converts old finger events into complete target packets.
        New replay code should prefer submit_packets().
        """
        if not events:
            return 0

        current = dict(self._estimated_targets)
        packets = []

        for event in events:
            finger = str(event["finger"]).lower()
            direction = str(event["direction"]).upper()

            if finger not in self.FINGERS:
                raise ValueError(f"Unknown finger: {finger}")

            if direction == "OPEN":
                current[finger] = 0
            elif direction == "CLOSE":
                current[finger] = 100
            else:
                raise ValueError("Direction must be OPEN or CLOSE.")

            packets.append(self.make_packet(current))

        return self.submit_packets(packets, source=source)

    # =================================================
    # ARDUINO RESPONSE HANDLING
    # =================================================

    def _wait_for_line(self, predicate, timeout, description):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            with self._condition:
                if self._emergency_stopped:
                    raise InterruptedError(
                        "Movement interrupted by emergency stop."
                    )

            remaining = deadline - time.monotonic()

            try:
                response = self.arduino.wait_for_response(
                    predicate,
                    timeout=min(self.POLL_INTERVAL, max(0.01, remaining))
                )
                if response:
                    return response

            except TimeoutError:
                continue

        raise TimeoutError(
            f"Timed out waiting for Arduino {description}."
        )

    def _execute_targets(self, targets):
        self._require_connection()

        packet = self.make_packet(targets)

        if hasattr(self.arduino, "clear_responses"):
            self.arduino.clear_responses()

        self.arduino.send_command(packet)

        ack = self._wait_for_line(
            lambda line: (
                line == "ACK,M"
                or line.startswith("ERROR,")
            ),
            self.ACK_TIMEOUT,
            "ACK,M"
        )

        if ack.startswith("ERROR,"):
            raise RuntimeError(f"Arduino rejected packet: {ack}")

        started = time.monotonic()
        movement_timeout = self.movement_timeout

        while True:
            elapsed = time.monotonic() - started
            remaining = movement_timeout - elapsed

            if remaining <= 0:
                raise TimeoutError("Arduino movement timed out.")

            response = self._wait_for_line(
                lambda line: (
                    line.startswith("MOVING,")
                    or line == "DONE,M"
                    or line.startswith("ERROR,")
                    or line == "STOPPED"
                ),
                remaining,
                "movement completion"
            )

            if response.startswith("ERROR,"):
                raise RuntimeError(f"Arduino error: {response}")

            if response == "STOPPED":
                raise InterruptedError("Arduino stopped the movement.")

            if response == "DONE,M":
                break

            if response not in ("MOVING,OPEN", "MOVING,CLOSE"):
                raise RuntimeError(
                    f"Unexpected Arduino response: {response}"
                )

        # These values are estimates only; no position sensors are used.
        with self._condition:
            self._estimated_targets.update(targets)

        return True

    # =================================================
    # WORKER LOOP
    # =================================================

    def _worker_loop(self):
        while True:
            with self._condition:
                while (
                    self._running
                    and not self._queue
                    and self._latest_targets is None
                ):
                    self._release_mode_if_idle()
                    self._condition.wait(timeout=0.25)

                if not self._running:
                    return

                if self._emergency_stopped:
                    self._queue.clear()
                    self._latest_targets = None
                    self._active = False
                    self._phase = "stopped"
                    self._condition.notify_all()
                    continue

                if self._queue:
                    task = self._queue.popleft()
                elif self._latest_targets is not None:
                    task = {
                        "source": self._latest_target_source,
                        "targets": self._latest_targets
                    }
                    self._latest_targets = None
                    self._latest_target_source = None
                else:
                    continue

                self._active = True
                self._phase = "moving"
                self._current_task = task

            try:
                self._execute_targets(task["targets"])

                with self._condition:
                    self._completed_tasks += 1
                    self._last_error = None
                    self._last_result = {
                        "completed": True,
                        "source": task["source"],
                        "targets": task["targets"]
                    }

                if self.cooldown_seconds > 0:
                    time.sleep(self.cooldown_seconds)

            except InterruptedError as exc:
                with self._condition:
                    self._last_error = str(exc)

            except Exception as exc:
                self._handle_worker_error(exc)

            finally:
                with self._condition:
                    self._active = False
                    self._current_task = None
                    self._phase = (
                        "stopped" if self._emergency_stopped
                        else "fault" if self._faulted
                        else "idle"
                    )
                    self._release_mode_if_idle()
                    self._condition.notify_all()

    def _handle_worker_error(self, error):
        """
        Latch a software/controller fault without impersonating a user E-stop.

        The firmware runs each accepted movement for a bounded duration and
        switches all outputs off at phase completion. A communication or
        software exception therefore stops future submissions and requires
        operator inspection, but does not send the firmware's latched `X`.
        Only emergency_stop() sends `X`.
        """
        with self._condition:
            self._last_error = str(error)
            self._last_result = {
                "completed": False,
                "error": str(error)
            }
            self._queue.clear()
            self._latest_targets = None
            self._latest_target_source = None
            self._faulted = True
            self._phase = "fault"
            self._condition.notify_all()

    def acknowledge_fault(self, physically_inspected=False):
        """Allow a new run only after an operator has inspected the glove."""
        if not physically_inspected:
            raise RuntimeError(
                "Inspect the glove and confirm it is stationary before acknowledging the fault."
            )
        with self._condition:
            if self._active or self._queue or self._latest_targets is not None:
                raise RuntimeError("Wait until all pending movement has stopped.")
            self._faulted = False
            self._last_error = None
            self._phase = "idle"
            self._condition.notify_all()
        return True

    # =================================================
    # EMERGENCY STOP / RESET
    # =================================================

    def emergency_stop(self):
        with self._condition:
            self._emergency_stopped = True
            self._queue.clear()
            self._latest_targets = None
            self._phase = "stopping"
            self._condition.notify_all()

        sent = False

        try:
            if self.arduino and self.arduino.is_connected():
                self.arduino.send_command("X")
                sent = True
        except Exception as exc:
            with self._condition:
                self._last_error = str(exc)

        return sent

    def confirm_home(self, physically_open_confirmed=False):
        if not physically_open_confirmed:
            raise RuntimeError(
                "Physically inspect the glove before resetting emergency stop."
            )

        with self._condition:
            if self._active or self._queue or self._latest_targets is not None:
                raise RuntimeError("Wait until all movement has stopped.")

        # The firmware has its own latched E-stop state. Reset it explicitly;
        # never clear only the Python latch while Arduino remains stopped.
        self._require_connection()
        if hasattr(self.arduino, "clear_responses"):
            self.arduino.clear_responses()
        self.arduino.send_command("RESET")
        response = self.arduino.wait_for_response(
            lambda line: line == "RESET_OK" or line.startswith("ERROR,"),
            timeout=3.0
        )
        if response != "RESET_OK":
            raise RuntimeError(f"Arduino rejected reset: {response}")

        with self._condition:
            self._emergency_stopped = False
            self._faulted = False
            self._last_error = None
            self._phase = "idle"
            # This is a user-confirmed estimate, not sensor feedback.
            self._estimated_targets = {
                finger: 0 for finger in self.FINGERS
            }
            self._condition.notify_all()

        return True

    # =================================================
    # QUEUE MANAGEMENT
    # =================================================

    def clear_pending(self):
        with self._condition:
            count = len(self._queue)

            self._queue.clear()
            self._latest_targets = None
            self._latest_target_source = None

            self._condition.notify_all()
            return count

    def wait_until_idle(self, timeout=None):
        deadline = (
            None if timeout is None
            else time.monotonic() + timeout
        )

        with self._condition:
            while (
                self._active
                or self._queue
                or self._latest_targets is not None
            ):
                if deadline is None:
                    self._condition.wait(timeout=0.25)
                else:
                    remaining = deadline - time.monotonic()

                    if remaining <= 0:
                        return False

                    self._condition.wait(
                        timeout=min(0.25, remaining)
                    )

            return True

    # =================================================
    # STATUS
    # =================================================

    @property
    def completed_tasks(self):
        with self._condition:
            return self._completed_tasks

    @property
    def queued_tasks(self):
        with self._condition:
            return len(self._queue) + (
                1 if self._latest_targets is not None else 0
            )

    @property
    def current_task(self):
        with self._condition:
            return self._current_task

    @property
    def last_result(self):
        with self._condition:
            return self._last_result

    @property
    def last_error(self):
        with self._condition:
            return self._last_error

    def get_status(self):
        with self._condition:
            connected = bool(
                self.arduino and self.arduino.is_connected()
            )

            return {
                "connected": connected,
                "active": self._active,
                "busy": self._active,
                "phase": self._phase,
                "queued_tasks": len(self._queue) + (
                    1 if self._latest_targets is not None else 0
                ),
                "completed_tasks": self._completed_tasks,
                "current_task": self._current_task,
                "last_error": self._last_error,
                "last_result": self._last_result,
                "emergency_stopped": self._emergency_stopped,
                "faulted": self._faulted,
                "mode_owner": self._mode_owner,
                "estimated_targets": dict(self._estimated_targets)
            }
