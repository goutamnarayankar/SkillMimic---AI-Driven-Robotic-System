
import unittest

from core.camera.camera_manager import CameraManager


class TestCameraManager(unittest.TestCase):

    def setUp(self):
        self.camera = CameraManager()

    def test_initial_camera_state(self):
        self.assertFalse(self.camera.is_opened())

    def test_release_without_starting(self):
        self.camera.release()
        self.assertFalse(self.camera.is_opened())


if __name__ == "__main__":
    unittest.main()
