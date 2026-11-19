
"""
SkillMimic gesture labels and demo shortcuts.

The gesture order must match the output order
of the trained classification model.
"""

# Six gesture classes
GESTURE_LABELS = [
    "Closed",
    "Grasp",
    "Grasp_down",
    "Open",
    "Pinch",
    "Writing"
]

# Gesture display names
GESTURE_DISPLAY_NAMES = {
    "Closed": "Closed Hand",
    "Grasp": "Grasp",
    "Grasp_down": "Grasp Down",
    "Open": "Open Hand",
    "Pinch": "Pinch",
    "Writing": "Writing"
}

# Existing demo keyboard shortcut
DEMO_KEYBOARD_SHORTCUTS = {
    "f": "Open"
}

# Demo action names
DEMO_ACTIONS = {
    "Open": {
        "gesture": "Open",
        "display_name": "Open Hand",
        "shortcut": "F"
    }
}


def get_gesture_display_name(gesture):
    """Return a friendly name for a gesture."""

    return GESTURE_DISPLAY_NAMES.get(
        gesture,
        "Unknown Gesture"
    )


def get_demo_action(key):
    """Return the demo gesture associated with a keyboard key."""

    if not key:
        return None

    return DEMO_KEYBOARD_SHORTCUTS.get(key.lower())


def get_available_gestures():
    """Return all supported gesture labels."""

    return GESTURE_LABELS.copy()


def get_available_demo_actions():
    """Return the configured demo actions."""

    return DEMO_ACTIONS.copy()
