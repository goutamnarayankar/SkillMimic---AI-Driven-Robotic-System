import unittest

from core.motion.motion_recorder import MotionRecorder
from core.motion.motion_processor import MotionProcessor
from core.motion.motion_replayer import MotionReplayer


class TestMotionRecorder(unittest.TestCase):
    def setUp(self):
        self.recorder = MotionRecorder(target_fps=30)

    def test_initial_recording_state(self):
        self.assertFalse(self.recorder.is_recording())

    def test_start_and_stop_recording(self):
        self.recorder.start_recording()
        self.assertTrue(self.recorder.is_recording())
        result = self.recorder.stop_recording()
        self.assertFalse(self.recorder.is_recording())
        self.assertEqual(result["frames"], [])

    def test_clear_recording_after_stop(self):
        self.recorder.start_recording()
        self.recorder.stop_recording()
        self.recorder.clear_recording()
        self.assertEqual(self.recorder.get_frame_count(), 0)


class TestMotionProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = MotionProcessor()

    def test_rejects_empty_recording(self):
        with self.assertRaises(ValueError):
            self.processor.process_recording({"frames": []})

    def test_normalizes_five_finger_recording(self):
        recording = {
            "duration": 0.1,
            "frames": [{
                "timestamp": 0.0,
                "hands": [{
                    "handedness": "Right",
                    "finger_curls": {
                        "thumb": 1, "index": 20, "middle": 40,
                        "ring": 60, "little": 80
                    }
                }]
            }]
        }
        result = self.processor.process_recording(recording)
        self.assertEqual(result["total_frames"], 1)
        self.assertEqual(
            result["frames"][0]["hands"][0]["finger_curls"]["little"],
            80
        )


class TestMotionReplayer(unittest.TestCase):
    def setUp(self):
        self.replayer = MotionReplayer()

    def test_cannot_play_without_loaded_motion(self):
        with self.assertRaises(ValueError):
            self.replayer.play()

    def test_load_valid_motion(self):
        motion = {
            "duration": 0.1,
            "frames": [{
                "timestamp": 0.0,
                "hands": [{
                    "finger_curls": {
                        "thumb": 0, "index": 0, "middle": 0,
                        "ring": 0, "little": 0
                    }
                }]
            }]
        }
        self.replayer.load_motion(motion)
        status = self.replayer.get_status()
        self.assertEqual(status["total_frames"], 1)
        self.assertEqual(status["state"], "loaded")

    def test_stop_when_idle_is_safe(self):
        self.assertTrue(self.replayer.stop())
        self.assertFalse(self.replayer.is_playing())


if __name__ == "__main__":
    unittest.main()
