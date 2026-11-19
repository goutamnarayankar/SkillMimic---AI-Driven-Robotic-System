import unittest
from unittest.mock import patch

from core.tracking.landmark_processor import LandmarkProcessor
from core.hardware.motion_controller import MotionController


class CalibrationTests(unittest.TestCase):
    def test_per_finger_open_closed_calibration_maps_endpoints(self):
        processor = LandmarkProcessor()
        open_pose = {f: 10.0 for f in processor.FINGERS}
        closed_pose = {f: 80.0 for f in processor.FINGERS}

        valid_landmarks = [{"x": 0.1, "y": 0.1, "z": 0.0}] * 21
        with patch.object(processor, "_raw_curls", return_value=open_pose):
            processor.calibrate_open(valid_landmarks)
        with patch.object(processor, "_raw_curls", return_value=closed_pose):
            processor.calibrate_closed(valid_landmarks)

        self.assertEqual(processor._apply_calibration("index", 10.0), 0.0)
        self.assertEqual(processor._apply_calibration("index", 80.0), 100.0)
        self.assertEqual(processor._apply_calibration("index", 45.0), 50.0)


class ReplayQueueTests(unittest.TestCase):
    def test_replay_targets_are_appended_fifo(self):
        controller = MotionController()
        # Prevent worker startup; inspect the accepted queue deterministically.
        with patch.object(controller, "start", lambda: None):
            controller.acquire_mode("skill_replay")
            first = dict(thumb=10, index=20, middle=30, ring=40, little=50)
            second = dict(thumb=60, index=70, middle=80, ring=90, little=100)
            controller.submit_targets(first, source="skill_replay")
            controller.submit_targets(second, source="skill_replay")

        self.assertEqual(len(controller._queue), 2)
        self.assertEqual(controller._queue[0]["targets"], first)
        self.assertEqual(controller._queue[1]["targets"], second)
        self.assertIsNone(controller._latest_targets)

    def test_live_mirror_remains_latest_wins(self):
        controller = MotionController()
        with patch.object(controller, "start", lambda: None):
            first = dict(thumb=0, index=0, middle=0, ring=0, little=0)
            second = dict(thumb=100, index=100, middle=100, ring=100, little=100)
            controller.submit_targets(first, source="live_mirror")
            controller.submit_targets(second, source="live_mirror")

        self.assertEqual(len(controller._queue), 0)
        self.assertEqual(controller._latest_targets, second)


if __name__ == "__main__":
    unittest.main()
