
from pathlib import Path
import json


class ModelManager:
    """
    Manages gesture recognition models stored in data/models.
    Does not overwrite or delete existing models.
    """

    MODEL_FILES = [
        "best_fast_gesture.h5",
        "fast_gesture_model.h5"
    ]

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        self.models_dir = (
            self.project_root / "data" / "models"
        )

        self.labels_file = (
            self.models_dir / "gesture_labels.json"
        )

        self.models_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------
    # GET AVAILABLE MODELS
    # --------------------------------------------------

    def get_available_models(self):
        available = []

        for filename in self.MODEL_FILES:
            model_path = self.models_dir / filename

            if model_path.exists():
                available.append({
                    "name": filename,
                    "path": str(model_path),
                    "size_mb": round(
                        model_path.stat().st_size / (1024 * 1024),
                        2
                    )
                })

        return available

    # --------------------------------------------------
    # GET DEFAULT MODEL
    # --------------------------------------------------

    def get_default_model(self):
        """
        Prefer the best validation checkpoint.
        Fall back to the regular trained model.
        """

        for filename in self.MODEL_FILES:
            model_path = self.models_dir / filename

            if model_path.exists():
                return model_path

        return None

    # --------------------------------------------------
    # SELECT MODEL
    # --------------------------------------------------

    def select_model(self, filename):
        if filename not in self.MODEL_FILES:
            raise ValueError("Unsupported model filename.")

        model_path = self.models_dir / filename

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {filename}"
            )

        return model_path

    # --------------------------------------------------
    # SAVE LABELS
    # --------------------------------------------------

    def save_labels(self, labels):
        if not isinstance(labels, list) or not labels:
            raise ValueError("Labels must be a non-empty list.")

        temporary_file = self.labels_file.with_suffix(".tmp")

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(labels, file, indent=4)

        temporary_file.replace(self.labels_file)

        return self.labels_file

    # --------------------------------------------------
    # LOAD LABELS
    # --------------------------------------------------

    def load_labels(self):
        if not self.labels_file.exists():
            return [
                "Closed",
                "Grasp",
                "Grasp_down",
                "Open",
                "Pinch",
                "Writing"
            ]

        with open(
            self.labels_file,
            "r",
            encoding="utf-8"
        ) as file:
            labels = json.load(file)

        if not isinstance(labels, list):
            raise ValueError("Invalid gesture labels file.")

        return labels

    # --------------------------------------------------
    # MODEL STATUS
    # --------------------------------------------------

    def get_model_status(self):
        models = self.get_available_models()

        return {
            "available": len(models) > 0,
            "count": len(models),
            "models": models,
            "default_model": (
                self.get_default_model().name
                if self.get_default_model()
                else None
            )
        }
