
"""
SkillMimic - Skill Manager

Handles persistent storage of recorded hand movements.

Features:
- Save skills as individual JSON files
- Load saved skills
- List all saved skills
- Delete skills
- Validate motion data before saving and loading
- Prevent duplicate skill names
- Atomic file writes to reduce the risk of corrupted files

Motion format:
{
    "frames": [
        {
            "timestamp": 0.0,
            "hands": [
                {
                    "hand_id": 0,
                    "handedness": "Right",
                    "finger_curls": {
                        "thumb": 0,
                        "index": 25,
                        "middle": 50,
                        "ring": 75,
                        "little": 100
                    }
                }
            ]
        }
    ],
    "duration": 2.0,
    "total_frames": 30
}
"""

import json
import re
import threading
import uuid

from datetime import datetime
from pathlib import Path
from copy import deepcopy


class SkillManager:

    FINGER_ORDER = (
        "thumb",
        "index",
        "middle",
        "ring",
        "little",
    )

    FORMAT_VERSION = 2

    def __init__(self, storage_dir=None):

        project_root = Path(__file__).resolve().parents[2]

        if storage_dir is None:
            storage_dir = project_root / "data" / "skills"

        self.storage_dir = Path(storage_dir).expanduser().resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()

    # -------------------------------------------------
    # NAME HANDLING
    # -------------------------------------------------

    @staticmethod
    def _clean_name(skill_name):

        if not isinstance(skill_name, str):
            raise ValueError("Skill name must be text.")

        name = skill_name.strip()

        if not name:
            raise ValueError("Skill name cannot be empty.")

        if len(name) > 100:
            raise ValueError("Skill name cannot exceed 100 characters.")

        if name in (".", ".."):
            raise ValueError("Invalid skill name.")

        if any(ord(char) < 32 for char in name):
            raise ValueError("Skill name contains invalid characters.")

        return name

    @staticmethod
    def _slugify(name):

        slug = name.lower().strip()

        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        slug = slug.strip("_")

        if not slug:
            raise ValueError("Skill name must contain letters or numbers.")

        return slug

    def _skill_path(self, skill_name):

        name = self._clean_name(skill_name)
        slug = self._slugify(name)

        return self.storage_dir / f"{slug}.json"

    def _find_existing_path(self, skill_name):

        requested = self._clean_name(skill_name).casefold()

        for path in self.storage_dir.glob("*.json"):

            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

                stored_name = data.get("name", path.stem)

                if stored_name.casefold() == requested:
                    return path

            except (OSError, json.JSONDecodeError):
                continue

        return None

    # -------------------------------------------------
    # MOTION VALIDATION
    # -------------------------------------------------

    @classmethod
    def validate_motion(cls, motion_data):

        if not isinstance(motion_data, dict):
            raise ValueError("Motion data must be a dictionary.")

        frames = motion_data.get("frames")

        if not isinstance(frames, list) or not frames:
            raise ValueError("Motion contains no recorded frames.")

        previous_timestamp = -1.0

        for frame_index, frame in enumerate(frames):

            if not isinstance(frame, dict):
                raise ValueError(
                    f"Invalid frame at index {frame_index}."
                )

            try:
                timestamp = float(frame["timestamp"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(
                    f"Invalid timestamp in frame {frame_index}."
                )

            if timestamp < 0 or timestamp < previous_timestamp:
                raise ValueError(
                    "Frame timestamps must be nonnegative "
                    "and in chronological order."
                )

            previous_timestamp = timestamp

            hands = frame.get("hands")

            if not isinstance(hands, list):
                raise ValueError(
                    f"Invalid hands list in frame {frame_index}."
                )

            for hand_index, hand in enumerate(hands):

                if not isinstance(hand, dict):
                    raise ValueError(
                        f"Invalid hand in frame {frame_index}."
                    )

                curls = hand.get("finger_curls")

                if not isinstance(curls, dict):
                    raise ValueError(
                        f"Missing finger_curls in frame {frame_index}."
                    )

                for finger in cls.FINGER_ORDER:

                    if finger not in curls:
                        raise ValueError(
                            f"Missing {finger} in frame {frame_index}."
                        )

                    value = curls[finger]

                    if isinstance(value, bool):
                        raise ValueError(
                            f"Invalid {finger} value in frame {frame_index}."
                        )

                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        raise ValueError(
                            f"Invalid {finger} value in frame {frame_index}."
                        )

                    if not 0 <= value <= 100:
                        raise ValueError(
                            f"{finger} must be between 0 and 100."
                        )

        return True

    # -------------------------------------------------
    # NORMALIZE MOTION DATA
    # -------------------------------------------------

    @classmethod
    def _normalize_motion(cls, motion_data):

        cls.validate_motion(motion_data)

        motion = deepcopy(motion_data)
        normalized_frames = []

        for frame in motion["frames"]:

            normalized_hands = []

            for hand in frame["hands"]:

                normalized_hand = deepcopy(hand)

                normalized_hand["finger_curls"] = {
                    finger: int(round(float(
                        hand["finger_curls"][finger]
                    )))
                    for finger in cls.FINGER_ORDER
                }

                normalized_hands.append(normalized_hand)

            normalized_frames.append({
                "timestamp": float(frame["timestamp"]),
                "hands": normalized_hands,
            })

        motion["frames"] = normalized_frames
        motion["total_frames"] = len(normalized_frames)
        motion["finger_order"] = list(cls.FINGER_ORDER)
        motion["format_version"] = cls.FORMAT_VERSION

        if len(normalized_frames) > 1:

            calculated_duration = (
                normalized_frames[-1]["timestamp"]
                - normalized_frames[0]["timestamp"]
            )

        else:
            calculated_duration = 0.0

        try:
            original_duration = float(motion.get("duration", 0))
        except (TypeError, ValueError):
            original_duration = 0.0

        if original_duration < 0:
            original_duration = 0.0

        motion["duration"] = max(
            original_duration,
            calculated_duration,
        )

        return motion

    # -------------------------------------------------
    # SAVE SKILL
    # -------------------------------------------------

    def save_skill(
        self,
        skill_name,
        motion_data,
        description=""
    ):

        name = self._clean_name(skill_name)

        if not isinstance(description, str):
            raise ValueError("Description must be text.")

        if len(description) > 1000:
            raise ValueError("Description cannot exceed 1000 characters.")

        motion = self._normalize_motion(motion_data)

        with self._lock:

            existing_path = self._find_existing_path(name)

            if existing_path is not None:
                raise FileExistsError(
                    f"A skill named '{name}' already exists."
                )

            skill_id = str(uuid.uuid4())

            created_at = datetime.now().astimezone().isoformat(
                timespec="seconds"
            )

            skill_data = {
                "id": skill_id,
                "name": name,
                "description": description.strip(),
                "created_at": created_at,
                "duration": motion["duration"],
                "total_frames": motion["total_frames"],
                "format_version": self.FORMAT_VERSION,
                "motion": motion,
            }

            destination = self._skill_path(name)
            temporary = destination.with_suffix(".tmp")

            try:

                with temporary.open("w", encoding="utf-8") as file:

                    json.dump(
                        skill_data,
                        file,
                        indent=2,
                        ensure_ascii=False,
                        allow_nan=False,
                    )

                    file.flush()

                temporary.replace(destination)

            except Exception:

                if temporary.exists():
                    temporary.unlink()

                raise

            return {
                "id": skill_id,
                "name": name,
                "description": description.strip(),
                "created_at": created_at,
                "duration": motion["duration"],
                "total_frames": motion["total_frames"],
                "file_path": str(destination),
            }

    # -------------------------------------------------
    # LOAD SKILL
    # -------------------------------------------------

    def load_skill(self, skill_name):

        name = self._clean_name(skill_name)

        with self._lock:

            path = self._find_existing_path(name)

            if path is None:
                raise FileNotFoundError(
                    f"Skill '{name}' was not found."
                )

            try:

                with path.open("r", encoding="utf-8") as file:
                    skill_data = json.load(file)

            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Skill '{name}' contains invalid JSON."
                ) from error

            if not isinstance(skill_data, dict):
                raise ValueError("Invalid saved skill structure.")

            if "motion" not in skill_data:
                raise ValueError("Saved skill has no motion data.")

            motion = self._normalize_motion(skill_data["motion"])

            skill_data["motion"] = motion
            skill_data["duration"] = motion["duration"]
            skill_data["total_frames"] = motion["total_frames"]

            return skill_data

    # -------------------------------------------------
    # LIST SKILLS
    # -------------------------------------------------

    def list_skills(self):

        skills = []

        with self._lock:

            for path in self.storage_dir.glob("*.json"):

                try:

                    with path.open("r", encoding="utf-8") as file:
                        data = json.load(file)

                    if not isinstance(data, dict):
                        continue

                    motion = data.get("motion", {})

                    skills.append({
                        "id": data.get("id", ""),
                        "name": data.get("name", path.stem),
                        "description": data.get("description", ""),
                        "created_at": data.get("created_at", ""),
                        "duration": float(
                            data.get(
                                "duration",
                                motion.get("duration", 0)
                            )
                        ),
                        "total_frames": int(
                            data.get(
                                "total_frames",
                                motion.get("total_frames", 0)
                            )
                        ),
                    })

                except (
                    OSError,
                    ValueError,
                    TypeError,
                    json.JSONDecodeError,
                ):
                    # Skip damaged files rather than crashing the library.
                    continue

        skills.sort(
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

        return skills

    # -------------------------------------------------
    # DELETE SKILL
    # -------------------------------------------------

    def delete_skill(self, skill_name):

        name = self._clean_name(skill_name)

        with self._lock:

            path = self._find_existing_path(name)

            if path is None:
                return False

            try:
                path.unlink()
                return True

            except OSError:
                return False

    # -------------------------------------------------
    # SKILL EXISTENCE
    # -------------------------------------------------

    def skill_exists(self, skill_name):

        name = self._clean_name(skill_name)

        with self._lock:
            return self._find_existing_path(name) is not None

    # -------------------------------------------------
    # STORAGE INFORMATION
    # -------------------------------------------------

    def get_storage_info(self):

        skills = self.list_skills()

        return {
            "storage_directory": str(self.storage_dir),
            "total_skills": len(skills),
            "total_frames": sum(
                skill["total_frames"]
                for skill in skills
            ),
            "total_duration": sum(
                skill["duration"]
                for skill in skills
            ),
        }

    # -------------------------------------------------
    # CLEAR LIBRARY
    # -------------------------------------------------

    def clear_library(self):

        """
        Delete all saved skill JSON files.

        Use carefully: this operation cannot be undone.
        """

        deleted = 0
        failed = []

        with self._lock:

            for path in self.storage_dir.glob("*.json"):

                try:
                    path.unlink()
                    deleted += 1

                except OSError:
                    failed.append(path.name)

        return {
            "deleted": deleted,
            "failed": failed,
        }
