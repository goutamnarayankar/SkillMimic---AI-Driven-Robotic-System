import unittest

from core.tracking.landmark_processor import LandmarkProcessor


class TestLandmarkProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = LandmarkProcessor()

    def test_landmark_distance(self):
        point1 = {"x": 0.0, "y": 0.0, "z": 0.0}
        point2 = {"x": 1.0, "y": 0.0, "z": 0.0}
        self.assertAlmostEqual(
            self.processor._distance(point1, point2),
            1.0
        )

    def test_process_returns_five_finger_values(self):
        landmarks = [
            {"id": i, "x": 0.2 + (i % 5) * 0.05,
             "y": 0.3 + (i // 5) * 0.07, "z": -0.01 * i}
            for i in range(21)
        ]
        result = self.processor.process(landmarks)
        self.assertEqual(
            set(result["finger_curls"]),
            {"thumb", "index", "middle", "ring", "little"}
        )

    def test_reset_clears_smoothing(self):
        self.processor._smoothed["index"] = 40.0
        self.processor._last_output["index"] = 40.0
        self.processor.reset()
        self.assertEqual(self.processor._smoothed, {})
        self.assertEqual(self.processor._last_output, {})


if __name__ == "__main__":
    unittest.main()
