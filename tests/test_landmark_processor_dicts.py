import unittest
from core.tracking.landmark_processor import LandmarkProcessor


class DictionaryLandmarkTests(unittest.TestCase):
    def test_handtracker_dictionary_points(self):
        landmarks = [
            {"id": i, "x": 0.2 + (i % 5) * 0.05,
             "y": 0.3 + (i // 5) * 0.07, "z": -0.01 * i}
            for i in range(21)
        ]
        result = LandmarkProcessor().process(landmarks)
        self.assertEqual(
            set(result["finger_curls"]),
            {"thumb", "index", "middle", "ring", "little"}
        )
        for value in result["finger_curls"].values():
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)


if __name__ == "__main__":
    unittest.main()
