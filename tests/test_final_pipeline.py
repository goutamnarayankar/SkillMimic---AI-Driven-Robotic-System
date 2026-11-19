import time
import unittest

from core.hardware.motion_controller import MotionController
from core.motion.motion_replayer import MotionReplayer
from core.motion.motion_recorder import MotionRecorder
from core.motion.motion_processor import MotionProcessor
from core.tracking.landmark_processor import LandmarkProcessor


class FakeArduino:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.sent = []
        self.connected = True

    def is_connected(self):
        return self.connected

    def clear_responses(self):
        pass

    def send_command(self, command):
        self.sent.append(command)

    def wait_for_response(self, predicate, timeout=1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.responses:
                value = self.responses.pop(0)
                if predicate(value):
                    return value
            else:
                time.sleep(0.005)
        raise TimeoutError("fake timeout")


class FakeReplayController:
    def __init__(self):
        self.submitted = []

    def wait_until_idle(self, timeout=None):
        return True

    def submit_targets(self, targets, source="manual"):
        self.submitted.append((dict(targets), source))
        return True


class FinalPipelineTests(unittest.TestCase):
    def test_landmark_processor_accepts_handtracker_dicts(self):
        landmarks = [
            {"id": i, "x": 0.2 + (i % 5) * 0.04,
             "y": 0.25 + (i // 5) * 0.06, "z": -0.005 * i}
            for i in range(21)
        ]
        result = LandmarkProcessor().process(landmarks)
        self.assertEqual(
            set(result["finger_curls"]),
            {"thumb", "index", "middle", "ring", "little"}
        )
        self.assertTrue(all(0 <= v <= 100 for v in result["finger_curls"].values()))

    def test_recording_round_trip_preserves_five_targets(self):
        recorder = MotionRecorder(target_fps=100)
        recorder.start_recording()
        hand = {
            "handedness": "Right",
            "finger_curls": {
                "thumb": 10, "index": 20, "middle": 30,
                "ring": 40, "little": 50
            }
        }
        self.assertTrue(recorder.record_frame([hand]))
        recording = recorder.stop_recording()
        processed = MotionProcessor().process_recording(recording)
        self.assertEqual(processed["frames"][0]["hands"][0]["finger_curls"], hand["finger_curls"])

    def test_controller_worker_error_does_not_send_automatic_estop(self):
        arduino = FakeArduino()
        controller = MotionController(arduino=arduino)
        controller._handle_worker_error(RuntimeError("simulated rejected command"))
        status = controller.get_status()
        self.assertTrue(status["faulted"])
        self.assertFalse(status["emergency_stopped"])
        self.assertNotIn("X", arduino.sent)

    def test_replayer_submits_with_skill_replay_owner(self):
        controller = FakeReplayController()
        replayer = MotionReplayer(controller)
        frames = [
            {"timestamp": 0.0, "hands": [{
                "finger_curls": {"thumb": 0, "index": 0, "middle": 0, "ring": 0, "little": 0}
            }]},
            {"timestamp": 0.01, "hands": [{
                "finger_curls": {"thumb": 25, "index": 25, "middle": 25, "ring": 25, "little": 25}
            }]}
        ]
        replayer.load_motion({"frames": frames, "duration": 0.01})
        replayer.play(speed=5.0)
        deadline = time.monotonic() + 2
        while replayer.get_status()["state"] == "playing" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(replayer.get_status()["state"], "completed")
        self.assertGreaterEqual(len(controller.submitted), 1)
        self.assertTrue(all(source == "skill_replay" for _, source in controller.submitted))


    def test_controller_executes_complete_arduino_m_packet(self):
        arduino = FakeArduino(["ACK,M", "MOVING,CLOSE", "DONE,M"])
        controller = MotionController(arduino=arduino)
        targets = {
            "thumb": 0, "index": 25, "middle": 50,
            "ring": 75, "little": 100
        }
        self.assertTrue(controller._execute_targets(targets))
        self.assertEqual(arduino.sent, ["M,0,25,50,75,100"])
        self.assertEqual(controller.get_status()["estimated_targets"], targets)

    def test_emergency_reset_reaches_firmware(self):
        arduino = FakeArduino(["RESET_OK"])
        controller = MotionController(arduino=arduino)
        controller._emergency_stopped = True
        self.assertTrue(controller.confirm_home(physically_open_confirmed=True))
        self.assertEqual(arduino.sent, ["RESET"])
        self.assertFalse(controller.get_status()["emergency_stopped"])

    def test_arduino_target_packet_protocol(self):
        self.assertEqual(
            MotionController.make_packet({
                "thumb": 0, "index": 25, "middle": 50,
                "ring": 75, "little": 100
            }),
            "M,0,25,50,75,100"
        )


if __name__ == "__main__":
    unittest.main()
