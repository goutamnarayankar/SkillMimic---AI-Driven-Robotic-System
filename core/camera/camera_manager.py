
import cv2


class CameraManager:
    def __init__(self, camera_index=0, width=1280, height=720):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.camera = None

    def start(self):
        if self.camera is not None and self.camera.isOpened():
            return True

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = cv2.VideoCapture(self.camera_index)

        if self.camera.isOpened():
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            return True

        self.camera = None
        return False

    def read_frame(self):
        if self.camera is None or not self.camera.isOpened():
            return False, None

        success, frame = self.camera.read()

        if success:
            frame = cv2.flip(frame, 1)

        return success, frame

    def release(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def is_opened(self):
        return self.camera is not None and self.camera.isOpened()
