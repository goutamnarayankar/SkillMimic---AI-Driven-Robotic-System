
import json
from pathlib import Path
from collections import deque

import cv2
import numpy as np


class GestureClassifier:
    """
    Loads a trained gesture recognition model and predicts
    one of the six supported hand gestures.
    """

    GESTURES = [
        "Closed",
        "Grasp",
        "Grasp_down",
        "Open",
        "Pinch",
        "Writing"
    ]

    def __init__(
        self,
        model_path=None,
        labels_path=None,
        confidence_threshold=0.70,
        history_size=7
    ):
        self.project_root = Path(__file__).resolve().parents[2]

        self.model_dir = self.project_root / "data" / "models"

        self.model_path = Path(model_path) if model_path else (
            self.model_dir / "best_fast_gesture.h5"
        )

        self.labels_path = Path(labels_path) if labels_path else (
            self.model_dir / "gesture_labels.json"
        )

        self.confidence_threshold = confidence_threshold
        self.history = deque(maxlen=history_size)

        self.model = None
        self.labels = self.GESTURES.copy()
        self.last_prediction = None

    # --------------------------------------------------
    # LOAD LABELS
    # --------------------------------------------------

    def load_labels(self):
        if not self.labels_path.exists():
            self.labels = self.GESTURES.copy()
            return self.labels

        with open(self.labels_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            self.labels = data

        elif isinstance(data, dict):
            if all(str(key).isdigit() for key in data):
                self.labels = [
                    data[key]
                    for key in sorted(data, key=lambda x: int(x))
                ]
            else:
                self.labels = list(data.keys())

        else:
            raise ValueError("Unsupported gesture labels format.")

        return self.labels

    # --------------------------------------------------
    # LOAD MODEL
    # --------------------------------------------------

    def load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Gesture model not found: {self.model_path}"
            )

        try:
            from tensorflow.keras.models import load_model
        except ImportError as error:
            raise ImportError(
                "TensorFlow is not installed in this environment."
            ) from error

        self.load_labels()

        self.model = load_model(
            str(self.model_path),
            compile=False
        )

        return True

    # --------------------------------------------------
    # PREPROCESS IMAGE
    # --------------------------------------------------

    @staticmethod
    def preprocess_frame(frame):
        if frame is None:
            raise ValueError("Input frame is empty.")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        resized = cv2.resize(
            rgb_frame,
            (160, 160),
            interpolation=cv2.INTER_AREA
        )

        # Preserve the 0-255 float32 input format
        # used by the provided training script.
        image = resized.astype(np.float32)

        image = np.expand_dims(image, axis=0)

        return image

    # --------------------------------------------------
    # PREDICT GESTURE
    # --------------------------------------------------

    def predict(self, frame, use_smoothing=True):

        if self.model is None:
            self.load_model()

        processed_image = self.preprocess_frame(frame)

        predictions = self.model.predict(
            processed_image,
            verbose=0
        )

        probabilities = predictions[0]

        class_index = int(np.argmax(probabilities))

        confidence = float(probabilities[class_index])

        if class_index >= len(self.labels):
            raise ValueError(
                "Model output count does not match gesture labels."
            )

        gesture = self.labels[class_index]

        if confidence < self.confidence_threshold:
            result = {
                "gesture": "Unknown",
                "predicted_gesture": gesture,
                "confidence": confidence,
                "accepted": False
            }

            self.last_prediction = result
            return result

        if use_smoothing:
            self.history.append(gesture)

            stable_gesture = max(
                set(self.history),
                key=self.history.count
            )

            if self.history.count(stable_gesture) < 4:
                result = {
                    "gesture": "Unstable",
                    "predicted_gesture": gesture,
                    "confidence": confidence,
                    "accepted": False
                }

                self.last_prediction = result
                return result

            gesture = stable_gesture

        result = {
            "gesture": gesture,
            "predicted_gesture": self.labels[class_index],
            "confidence": confidence,
            "accepted": True
        }

        self.last_prediction = result

        return result

    # --------------------------------------------------
    # RESET PREDICTION HISTORY
    # --------------------------------------------------

    def reset_history(self):
        self.history.clear()
        self.last_prediction = None

    # --------------------------------------------------
    # RELEASE MODEL
    # --------------------------------------------------

    def unload_model(self):
        self.model = None
        self.reset_history()
