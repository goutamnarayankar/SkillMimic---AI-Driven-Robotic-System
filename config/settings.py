
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AppSettings:

    APP_NAME = "SkillMimic"
    APP_VERSION = "1.0.0"

    DEBUG = False

    # Camera settings
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720

    # Hand tracking settings
    MAX_HANDS = 2
    DETECTION_CONFIDENCE = 0.7
    TRACKING_CONFIDENCE = 0.7
    MODEL_COMPLEXITY = 1

    # Movement recording
    RECORDING_FPS = 30
    MOTION_SMOOTHING = 0.65

    # Playback
    DEFAULT_PLAYBACK_SPEED = 1.0
    MIN_PLAYBACK_SPEED = 0.1
    MAX_PLAYBACK_SPEED = 2.0

    # Storage
    DATA_DIRECTORY = PROJECT_ROOT / "data"
    RECORDINGS_DIRECTORY = DATA_DIRECTORY / "recordings"
    PROCESSED_DIRECTORY = DATA_DIRECTORY / "processed"
    EXPORTS_DIRECTORY = DATA_DIRECTORY / "exports"

    # Application assets
    ASSETS_DIRECTORY = PROJECT_ROOT / "assets"
    CSS_FILE = ASSETS_DIRECTORY / "css" / "style.css"

    # Logging
    LOG_DIRECTORY = PROJECT_ROOT / "logs"
    LOG_LEVEL = "INFO"

    @classmethod
    def create_directories(cls):

        directories = [
            cls.RECORDINGS_DIRECTORY,
            cls.PROCESSED_DIRECTORY,
            cls.EXPORTS_DIRECTORY,
            cls.LOG_DIRECTORY
        ]

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True
            )

    @classmethod
    def get_app_info(cls):

        return {
            "name": cls.APP_NAME,
            "version": cls.APP_VERSION
        }
