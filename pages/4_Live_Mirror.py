
import streamlit as st
import cv2
import time

from core.camera.camera_manager import CameraManager
from core.tracking.hand_tracker import HandTracker
from core.tracking.landmark_processor import LandmarkProcessor
from core.hardware.controller_access import (
    get_motion_controller,
    get_arduino_connection,
)


# =====================================================
# CONFIGURATION
# =====================================================

FINGERS = ("thumb", "index", "middle", "ring", "little")

DEFAULT_ACTUATION_MS = 800
TRACKING_CONFIRMATION_FRAMES = 3
FRAGMENT_INTERVAL = 0.1
MIN_TARGET_DELTA = 4
MIN_SUBMISSION_INTERVAL = 0.30


# =====================================================
# PAGE HEADER
# =====================================================

st.markdown(
    """
    <div class="page-header">
        <div>
            <p class="eyebrow">REAL-TIME MOVEMENT</p>
            <h1>Live Mirror</h1>
            <p class="subtitle">
                Track natural hand movements and replicate
                five independent finger targets using the
                SkillMimic pneumatic controller.
            </p>
        </div>
        <div class="system-badge">● LIVE TRACKING</div>
    </div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# SESSION STATE
# =====================================================

DEFAULTS = {
    "mirror_camera": None,
    "mirror_tracker": None,
    "mirror_processor": None,

    "mirror_active": False,
    "mirror_hardware_stream": False,

    "mirror_last_error": None,
    "mirror_last_targets": None,
    "mirror_last_submitted_targets": None,

    "mirror_controller_mode": False,
    "mirror_actuation_ms": DEFAULT_ACTUATION_MS,

    "mirror_hand_present": False,
    "mirror_valid_frames": 0,
    "mirror_hand_identity": None,

    "mirror_tracking_status": "Inactive",
    "mirror_last_submission_time": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =====================================================
# INITIALIZE COMPONENTS
# =====================================================

if st.session_state.mirror_camera is None:
    st.session_state.mirror_camera = CameraManager()

if (
    st.session_state.mirror_tracker is None
    or getattr(st.session_state.mirror_tracker, "max_hands", None) != 1
):
    old_tracker = st.session_state.mirror_tracker
    if old_tracker is not None:
        try:
            old_tracker.close()
        except Exception:
            pass
    st.session_state.mirror_tracker = HandTracker(max_hands=1)

if st.session_state.mirror_processor is None:
    st.session_state.mirror_processor = LandmarkProcessor()

camera = st.session_state.mirror_camera
tracker = st.session_state.mirror_tracker
processor = st.session_state.mirror_processor


# =====================================================
# CONTROLLER HELPERS
# =====================================================

def get_controller():
    return get_motion_controller()


def get_hardware_status():
    # Rebind to the canonical connection shared by Settings and all pages.
    arduino = get_arduino_connection()
    controller = get_controller()
    controller.set_arduino(arduino)

    status = controller.get_status()
    serial_status = arduino.get_status()

    # The serial object is the source of truth for USB/COM connectivity.
    status["connected"] = bool(serial_status.get("connected"))
    status["port"] = serial_status.get("port")
    status["baudrate"] = serial_status.get("baudrate")
    status["serial_error"] = serial_status.get("last_error")
    return status


def reset_tracking_confirmation():
    st.session_state.mirror_valid_frames = 0
    st.session_state.mirror_hand_identity = None
    st.session_state.mirror_hand_present = False
    st.session_state.mirror_tracking_status = "Searching"


def release_live_mode():
    """
    Stop accepting Live Mirror targets.
    This is not an emergency stop.
    """

    try:
        controller = get_controller()

        controller.clear_pending()

        if st.session_state.mirror_controller_mode:
            controller.release_mode("live_mirror")

    except Exception as error:
        st.session_state.mirror_last_error = str(error)

    st.session_state.mirror_controller_mode = False
    st.session_state.mirror_last_submitted_targets = None


def stop_live_mirror():
    """
    Stop camera tracking and release Live Mirror ownership.
    """

    release_live_mode()

    st.session_state.mirror_hardware_stream = False
    st.session_state.mirror_active = False

    st.session_state.mirror_last_targets = None
    st.session_state.mirror_last_submission_time = None

    reset_tracking_confirmation()
    processor.reset()

    try:
        camera.release()
    except Exception:
        pass

    try:
        tracker.close()
    except Exception:
        pass

    st.session_state.mirror_tracker = HandTracker(max_hands=1)


def emergency_stop():
    """
    Immediately stop the controller.
    """

    controller = get_controller()
    controller.emergency_stop()

    st.session_state.mirror_active = False
    st.session_state.mirror_hardware_stream = False
    st.session_state.mirror_controller_mode = False

    st.session_state.mirror_last_targets = None

    reset_tracking_confirmation()

    try:
        camera.release()
    except Exception:
        pass


# =====================================================
# HAND NORMALIZATION
# =====================================================

def get_hand_landmarks(hand):
    """
    Extract the 21 landmarks from a detected hand.

    Supports dictionaries and MediaPipe landmark objects.
    """

    if isinstance(hand, dict):
        landmarks = hand.get("landmarks")

        if landmarks is None:
            landmarks = hand.get("landmark_list")

        if landmarks is None:
            landmarks = hand.get("hand_landmarks")

    else:
        landmarks = hand

    if hasattr(landmarks, "landmark"):
        landmarks = landmarks.landmark

    if landmarks is None or len(landmarks) != 21:
        return None

    return landmarks


def get_hand_identity(hand, index=0):
    """
    Use handedness when available to detect hand changes.
    """

    if not isinstance(hand, dict):
        return str(index)

    handedness = hand.get("handedness")

    if handedness is None:
        return str(index)

    if isinstance(handedness, dict):
        return str(
            handedness.get("label")
            or handedness.get("classification")
            or index
        )

    return str(handedness)


def process_detected_hands(detected_hands):
    """
    Convert detected hands into independent finger-curl values.
    """

    processed = []

    if not detected_hands:
        return processed

    for index, hand in enumerate(detected_hands):

        landmarks = get_hand_landmarks(hand)

        if landmarks is None:
            continue

        try:
            result = processor.process(landmarks)

            processed_hand = {
                "handedness": get_hand_identity(hand, index),
                "landmarks": landmarks,
                "finger_curls": result["finger_curls"],
            }

            if isinstance(hand, dict):
                processed_hand["hand_id"] = hand.get(
                    "hand_id",
                    index
                )

            processed.append(processed_hand)

        except (ValueError, TypeError) as error:
            st.session_state.mirror_last_error = str(error)

    return processed


# =====================================================
# TARGET VALIDATION
# =====================================================

def extract_finger_targets(hand):
    curls = hand.get("finger_curls")

    if not isinstance(curls, dict):
        raise ValueError("Missing finger_curls from LandmarkProcessor.")

    targets = {}

    for finger in FINGERS:

        if finger not in curls:
            raise ValueError(f"Missing target for {finger}.")

        value = float(curls[finger])

        if not 0 <= value <= 100:
            raise ValueError(
                f"{finger} target must be between 0 and 100."
            )

        targets[finger] = int(round(value))

    return targets


# =====================================================
# HARDWARE TRANSMISSION
# =====================================================

def transmit_hand_targets(hand):
    """
    Submit only the newest valid hand targets.

    MotionController handles the sequential OPEN/CLOSE phases.
    """

    controller = get_controller()
    status = controller.get_status()

    if not status["connected"]:
        raise ConnectionError("Arduino is disconnected.")

    if status["emergency_stopped"]:
        raise RuntimeError("Emergency stop is active.")
    if status.get("faulted"):
        raise RuntimeError(
            "Controller fault is active. Inspect the glove and acknowledge the fault."
        )

    targets = extract_finger_targets(hand)

    if not st.session_state.mirror_controller_mode:
        controller.acquire_mode("live_mirror")
        st.session_state.mirror_controller_mode = True

    previous = st.session_state.mirror_last_submitted_targets
    if previous is not None:
        max_delta = max(
            abs(targets[finger] - previous[finger])
            for finger in FINGERS
        )
        if max_delta < MIN_TARGET_DELTA:
            return False

        last_sent = st.session_state.mirror_last_submission_time
        if last_sent is not None and (time.time() - last_sent) < MIN_SUBMISSION_INTERVAL:
            return False

    controller.submit_latest_targets(
        targets,
        source="live_mirror",
        duration_ms=int(st.session_state.mirror_actuation_ms)
    )

    st.session_state.mirror_last_submitted_targets = targets.copy()
    st.session_state.mirror_last_targets = targets.copy()
    st.session_state.mirror_last_submission_time = time.time()

    return True


# =====================================================
# TRACKING CONFIRMATION
# =====================================================

def confirm_hand(hand):
    """
    Require three consecutive valid frames before the first
    hardware command and after tracking loss or hand change.
    """

    identity = hand["handedness"]

    previous_identity = st.session_state.mirror_hand_identity

    if previous_identity != identity:
        st.session_state.mirror_hand_identity = identity
        st.session_state.mirror_valid_frames = 1
        st.session_state.mirror_tracking_status = "Confirming hand"
        return False

    st.session_state.mirror_valid_frames += 1

    if (
        st.session_state.mirror_valid_frames
        < TRACKING_CONFIRMATION_FRAMES
    ):
        st.session_state.mirror_tracking_status = (
            "Confirming hand "
            f"({st.session_state.mirror_valid_frames}/"
            f"{TRACKING_CONFIRMATION_FRAMES})"
        )
        return False

    st.session_state.mirror_tracking_status = "Tracking confirmed"
    return True


# =====================================================
# PAGE CONTROLS
# =====================================================

st.markdown("### Mirror Controls")

col1, col2, col3 = st.columns(3)

with col1:
    start_clicked = st.button(
        "Start Live Mirror",
        type="primary",
        width="stretch",
        disabled=st.session_state.mirror_active
    )

with col2:
    stop_clicked = st.button(
        "Stop Live Mirror",
        width="stretch",
        disabled=not st.session_state.mirror_active
    )

with col3:
    reset_clicked = st.button(
        "Reset Tracking",
        width="stretch"
    )


# =====================================================
# START
# =====================================================

if start_clicked:

    try:
        replayer = st.session_state.get("motion_replayer")

        if replayer is not None and replayer.is_playing():
            raise RuntimeError(
                "Stop Skill Library playback before starting Live Mirror."
            )

        controller = get_controller()
        hardware = controller.get_status()

        if not hardware["connected"]:
            raise ConnectionError("Connect Arduino before starting.")

        if hardware["emergency_stopped"]:
            raise RuntimeError(
                "Emergency stop is active. Recover it safely first."
            )
        if hardware.get("faulted"):
            raise RuntimeError(
                "Controller fault is active. Inspect and acknowledge it first."
            )

        if hardware["active"] or hardware["queued_tasks"]:
            raise RuntimeError(
                "The pneumatic glove is busy. Wait until it becomes idle."
            )

        if not camera.start():
            raise RuntimeError("Unable to access the webcam.")

        processor.reset()
        reset_tracking_confirmation()

        st.session_state.mirror_active = True
        st.session_state.mirror_last_error = None
        st.session_state.mirror_last_targets = None
        st.session_state.mirror_last_submitted_targets = None
        st.session_state.mirror_controller_mode = False

        st.rerun()

    except Exception as error:
        st.session_state.mirror_last_error = str(error)
        st.error(f"Unable to start Live Mirror: {error}")


# =====================================================
# STOP
# =====================================================

if stop_clicked:
    stop_live_mirror()
    st.rerun()


# =====================================================
# RESET
# =====================================================

if reset_clicked:

    try:
        processor.reset()
        reset_tracking_confirmation()

        if st.session_state.mirror_controller_mode:
            release_live_mode()

        st.session_state.mirror_last_targets = None
        st.session_state.mirror_last_error = None

        st.rerun()

    except Exception as error:
        st.error(f"Tracking reset failed: {error}")


# =====================================================
# HARDWARE STATUS
# =====================================================

st.divider()
st.markdown("### Arduino Synchronization")

try:
    hardware = get_hardware_status()

    connected = hardware["connected"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Arduino",
            "Connected" if connected else "Disconnected"
        )

    with col2:
        st.metric(
            "Serial Port",
            hardware.get("port") or "Unavailable"
        )

    with col3:
        st.metric(
            "Controller",
            "BUSY" if hardware["active"] else "IDLE"
        )

    st.caption(
        f"Queued tasks: {hardware['queued_tasks']} · "
        f"Completed tasks: {hardware['completed_tasks']} · "
        f"Phase: {hardware['phase']}"
    )

    if hardware["emergency_stopped"]:
        st.error("Emergency stop is active. Reset only after physically inspecting the glove.")

    if hardware.get("faulted"):
        st.error(
            "Controller fault: new commands are blocked. The controller did not send "
            "an automatic emergency-stop command. Inspect the glove and acknowledge "
            "the fault before retrying."
        )
        inspected = st.checkbox(
            "I have physically inspected the glove and confirmed it is stationary.",
            key="mirror_fault_inspected"
        )
        if st.button(
            "Acknowledge Controller Fault",
            key="mirror_ack_fault",
            disabled=not inspected
        ):
            try:
                get_controller().acknowledge_fault(
                    physically_inspected=True
                )
                st.session_state.mirror_last_error = None
                st.rerun()
            except Exception as error:
                st.error(f"Could not acknowledge fault: {error}")

    if hardware.get("serial_error"):
        st.error(f"Serial communication error: {hardware['serial_error']}")

except Exception as error:
    hardware = None
    connected = False
    st.error(f"Controller unavailable: {error}")


# =====================================================
# STREAMING SETTINGS
# =====================================================

st.markdown("### Streaming Settings")

st.number_input(
    "Finger actuation time (milliseconds)",
    min_value=100,
    max_value=10000,
    step=100,
    key="mirror_actuation_ms",
    disabled=st.session_state.mirror_active,
    help="Starting value only. Calibrate with the pneumatic system safely."
)

stream_allowed = (
    hardware is not None
    and connected
    and not hardware["emergency_stopped"]
    and not hardware.get("faulted", False)
)

st.checkbox(
    "Enable pneumatic glove synchronization",
    key="mirror_hardware_stream",
    disabled=(
        not st.session_state.mirror_active
        or not stream_allowed
    ),
    help="Submit the newest five-finger targets to the motion controller."
)

if st.session_state.mirror_hardware_stream and stream_allowed:
    st.success("Pneumatic glove synchronization enabled.")

elif not connected:
    st.warning("Connect Arduino from Settings before enabling synchronization.")


# =====================================================
# CAMERA PREVIEW
# =====================================================

st.divider()
st.markdown("### Camera Preview")

camera_placeholder = st.empty()
metrics_placeholder = st.empty()
data_placeholder = st.empty()


# =====================================================
# LIVE CAMERA FRAGMENT
# =====================================================

@st.fragment(run_every=FRAGMENT_INTERVAL)
def mirror_camera_preview():

    if not st.session_state.mirror_active:
        camera_placeholder.info(
            "Select Start Live Mirror to activate hand tracking."
        )
        return

    current_camera = st.session_state.mirror_camera
    current_tracker = st.session_state.mirror_tracker
    current_processor = st.session_state.mirror_processor

    success, frame = current_camera.read_frame()

    if not success or frame is None:
        camera_placeholder.error("Camera frame unavailable.")
        return

    try:
        annotated_frame, detected_hands = current_tracker.detect(frame)

        processed_hands = process_detected_hands(detected_hands)

    except Exception as error:
        st.session_state.mirror_last_error = str(error)
        camera_placeholder.error(f"Tracking error: {error}")
        return

    # -------------------------------------------------
    # TRACKING LOSS
    # -------------------------------------------------

    if not processed_hands:

        reset_tracking_confirmation()

        if st.session_state.mirror_controller_mode:
            release_live_mode()

    else:

        selected_hand = processed_hands[0]

        confirmed = confirm_hand(selected_hand)

        st.session_state.mirror_hand_present = confirmed

        # -------------------------------------------------
        # HARDWARE TRANSMISSION
        # -------------------------------------------------

        if (
            confirmed
            and st.session_state.mirror_hardware_stream
        ):

            try:
                transmit_hand_targets(selected_hand)
                st.session_state.mirror_last_error = None

            except Exception as error:
                st.session_state.mirror_last_error = str(error)

                st.session_state.mirror_hardware_stream = False
                release_live_mode()

    # -------------------------------------------------
    # STREAMING DISABLED
    # -------------------------------------------------

    if (
        not st.session_state.mirror_hardware_stream
        and st.session_state.mirror_controller_mode
    ):
        release_live_mode()

    # -------------------------------------------------
    # CAMERA DISPLAY
    # -------------------------------------------------

    rgb_frame = cv2.cvtColor(
        annotated_frame,
        cv2.COLOR_BGR2RGB
    )

    camera_placeholder.image(
        rgb_frame,
        channels="RGB",
        width="stretch"
    )

    # -------------------------------------------------
    # METRICS
    # -------------------------------------------------

    with metrics_placeholder.container():

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Hands Detected",
            len(processed_hands)
        )

        col2.metric(
            "Valid Frames",
            st.session_state.mirror_valid_frames
        )

        col3.metric(
            "Tracking",
            st.session_state.mirror_tracking_status
        )

    # -------------------------------------------------
    # FIVE-FINGER VALUES
    # -------------------------------------------------

    with data_placeholder.container():

        st.markdown("### Live Finger Measurements")

        if processed_hands:

            hand = processed_hands[0]

            st.caption(
                f"Selected hand: {hand['handedness']}"
            )

            curls = hand["finger_curls"]

            st.markdown("#### Personal Finger Calibration")
            st.caption(
                "Capture a fully open palm first, then a comfortable fully closed fist. "
                "Keep the same hand and camera position for both captures."
            )
            cal_col1, cal_col2, cal_col3 = st.columns(3)
            with cal_col1:
                if st.button("Set Open = 0%", key="mirror_calibrate_open", width="stretch"):
                    try:
                        processor.calibrate_open(hand["landmarks"])
                        st.success("Open-hand references captured.")
                    except Exception as calibration_error:
                        st.error(f"Open calibration failed: {calibration_error}")
            with cal_col2:
                if st.button("Set Closed = 100%", key="mirror_calibrate_closed", width="stretch"):
                    try:
                        processor.calibrate_closed(hand["landmarks"])
                        st.success("Closed-hand references captured.")
                    except Exception as calibration_error:
                        st.error(f"Closed calibration failed: {calibration_error}")
            with cal_col3:
                if st.button("Reset Calibration", key="mirror_calibration_reset", width="stretch"):
                    processor.clear_calibration()
                    st.success("Finger calibration cleared.")

            calibration_status = processor.get_calibration_status()
            ready_count = sum(1 for item in calibration_status.values() if item["ready"])
            st.caption(f"Calibrated fingers: {ready_count}/5")

            columns = st.columns(5)

            for index, finger in enumerate(FINGERS):

                with columns[index]:
                    st.metric(
                        finger.capitalize(),
                        f"{curls[finger]}%"
                    )

                    st.progress(
                        int(curls[finger]) / 100.0
                    )

        else:
            st.info(
                "No hand detected. Place one hand clearly in front of the camera."
            )

        if st.session_state.mirror_last_targets:
            st.markdown("### Last Submitted Targets")
            st.json(st.session_state.mirror_last_targets)

        if st.session_state.mirror_last_error:
            st.error(st.session_state.mirror_last_error)


mirror_camera_preview()


# =====================================================
# ROBOTIC GLOVE STATUS
# =====================================================

st.divider()
st.markdown("### Robotic Glove Status")

try:
    hardware = get_hardware_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Hand Tracking",
            "Active" if st.session_state.mirror_active else "Inactive"
        )

    with col2:
        st.metric(
            "Arduino",
            "Connected" if hardware["connected"] else "Disconnected"
        )

    with col3:
        st.metric(
            "Hardware Streaming",
            "Enabled" if st.session_state.mirror_hardware_stream else "Disabled"
        )

    if hardware["emergency_stopped"]:
        st.error("Emergency stop is active.")

    elif st.session_state.mirror_last_error:
        st.error(st.session_state.mirror_last_error)

    elif (
        st.session_state.mirror_hardware_stream
        and st.session_state.mirror_hand_present
    ):
        st.success(
            "Tracking confirmed. Latest finger targets are being submitted."
        )

    elif st.session_state.mirror_hardware_stream:
        st.warning(
            "Waiting for three consecutive valid tracking frames."
        )

    else:
        st.info(
            "Camera tracking is available. Enable synchronization "
            "to submit targets to the pneumatic glove."
        )

except Exception as error:
    st.error(f"Unable to read controller status: {error}")


# =====================================================
# EMERGENCY STOP
# =====================================================

st.divider()
st.markdown("### Safety Controls")

if st.button(
    "EMERGENCY STOP",
    type="primary",
    width="stretch"
):

    try:
        emergency_stop()
        st.error("Emergency stop activated.")
        st.rerun()

    except Exception as error:
        st.error(f"Emergency stop failed: {error}")


# =====================================================
# FOOTER
# =====================================================

st.markdown(
    """
    <div class="footer">
        SkillMimic · Live Hand Movement Monitoring
    </div>
    """,
    unsafe_allow_html=True
)
