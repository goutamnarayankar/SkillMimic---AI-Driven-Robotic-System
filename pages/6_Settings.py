
import streamlit as st
import sys
import json

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import AppSettings
from core.hardware.controller_access import (
    get_arduino_connection,
    get_motion_controller,
    get_available_ports,
    connect_arduino,
    disconnect_arduino,
)


# -----------------------------------------
# PAGE HEADER
# -----------------------------------------

st.markdown(
    """
    <div class="page-header">
        <div>
            <p class="eyebrow">APPLICATION CONFIGURATION</p>
            <h1>Settings</h1>
            <p class="subtitle">
                Configure your SkillMimic environment and preferences.
            </p>
        </div>
        <div class="system-badge">● SYSTEM SETTINGS</div>
    </div>
    """,
    unsafe_allow_html=True
)


# -----------------------------------------
# LOAD SETTINGS
# -----------------------------------------

config_path = PROJECT_ROOT / "config" / "hardware_config.json"

if "settings_camera_index" not in st.session_state:
    st.session_state.settings_camera_index = AppSettings.CAMERA_INDEX

if "settings_camera_width" not in st.session_state:
    st.session_state.settings_camera_width = AppSettings.CAMERA_WIDTH

if "settings_camera_height" not in st.session_state:
    st.session_state.settings_camera_height = AppSettings.CAMERA_HEIGHT

if "settings_max_hands" not in st.session_state:
    st.session_state.settings_max_hands = AppSettings.MAX_HANDS

if "settings_detection_confidence" not in st.session_state:
    st.session_state.settings_detection_confidence = AppSettings.DETECTION_CONFIDENCE

if "settings_tracking_confidence" not in st.session_state:
    st.session_state.settings_tracking_confidence = AppSettings.TRACKING_CONFIDENCE

if "settings_recording_fps" not in st.session_state:
    st.session_state.settings_recording_fps = AppSettings.RECORDING_FPS

if "settings_playback_speed" not in st.session_state:
    st.session_state.settings_playback_speed = AppSettings.DEFAULT_PLAYBACK_SPEED


try:
    with open(config_path, "r", encoding="utf-8") as file:
        hardware_config = json.load(file)

except (OSError, json.JSONDecodeError):
    hardware_config = {}


# -----------------------------------------
# CAMERA SETTINGS
# -----------------------------------------

st.markdown("### 📷 Camera Configuration")

with st.container(border=True):

    camera_index = st.number_input(
        "Camera Device Index",
        min_value=0,
        max_value=10,
        value=st.session_state.settings_camera_index,
        step=1
    )

    col1, col2 = st.columns(2)

    with col1:
        camera_width = st.selectbox(
            "Camera Width",
            [640, 800, 1280, 1920],
            index=(
                [640, 800, 1280, 1920].index(
                    st.session_state.settings_camera_width
                )
                if st.session_state.settings_camera_width
                in [640, 800, 1280, 1920] else 2
            )
        )

    with col2:
        camera_height = st.selectbox(
            "Camera Height",
            [480, 600, 720, 1080],
            index=(
                [480, 600, 720, 1080].index(
                    st.session_state.settings_camera_height
                )
                if st.session_state.settings_camera_height
                in [480, 600, 720, 1080] else 2
            )
        )


# -----------------------------------------
# TRACKING SETTINGS
# -----------------------------------------

st.divider()

st.markdown("### 🖐️ Hand Tracking Configuration")

with st.container(border=True):

    max_hands = st.selectbox(
        "Maximum Hands",
        [1, 2],
        index=[1, 2].index(
            st.session_state.settings_max_hands
        )
    )

    detection_confidence = st.slider(
        "Detection Confidence",
        min_value=0.1,
        max_value=1.0,
        value=float(
            st.session_state.settings_detection_confidence
        ),
        step=0.05
    )

    tracking_confidence = st.slider(
        "Tracking Confidence",
        min_value=0.1,
        max_value=1.0,
        value=float(
            st.session_state.settings_tracking_confidence
        ),
        step=0.05
    )

    st.caption(
        "Higher confidence thresholds can reduce false detections "
        "but may make tracking harder in difficult lighting."
    )


# -----------------------------------------
# RECORDING SETTINGS
# -----------------------------------------

st.divider()

st.markdown("### 🎥 Recording Configuration")

with st.container(border=True):

    recording_fps = st.select_slider(
        "Recording Frame Rate",
        options=[10, 15, 20, 24, 30, 60],
        value=(
            st.session_state.settings_recording_fps
            if st.session_state.settings_recording_fps
            in [10, 15, 20, 24, 30, 60]
            else 30
        )
    )

    st.caption(
        "Higher frame rates capture more movement detail "
        "but require more storage and processing."
    )


# -----------------------------------------
# PLAYBACK SETTINGS
# -----------------------------------------

st.divider()

st.markdown("### ▶️ Playback Preferences")

with st.container(border=True):

    playback_speed = st.slider(
        "Default Playback Speed",
        min_value=0.1,
        max_value=2.0,
        value=float(
            st.session_state.settings_playback_speed
        ),
        step=0.1
    )

    st.caption(
        "Playback speed is a software preference. "
        "Physical movement speed requires separate hardware calibration."
    )


# -----------------------------------------
# ARDUINO CONFIGURATION
# -----------------------------------------

device_config = hardware_config.get("device", {})
configured_port = device_config.get("serial_port")
configured_baudrate = int(device_config.get("baudrate", 9600))

# Use the SAME session-scoped connection as Live Mirror and Manual Control.
arduino = get_arduino_connection()
controller = get_motion_controller()

if not arduino.is_connected():
    arduino.baudrate = configured_baudrate

try:
    available_ports = get_available_ports()
    port_options = [item["device"] for item in available_ports]
except Exception as error:
    port_options = []
    st.error(f"Unable to enumerate serial ports: {error}")

default_port = configured_port or st.session_state.get("skillmimic_port")
if default_port and default_port not in port_options:
    port_options.insert(0, default_port)

with st.container(border=True):
    st.write("**Arduino USB Connection**")

    selected_port = (
        st.selectbox(
            "Arduino COM Port",
            port_options,
            index=(port_options.index(default_port)
                   if default_port in port_options else 0),
            key="arduino_selected_port",
        )
        if port_options else None
    )

    baudrate_options = [9600, 19200, 38400, 57600, 115200]
    selected_baudrate = st.selectbox(
        "Serial Baud Rate",
        baudrate_options,
        index=(baudrate_options.index(configured_baudrate)
               if configured_baudrate in baudrate_options else 0),
        key="arduino_selected_baudrate",
    )

    serial_status = arduino.get_status()

    if serial_status["connected"]:
        st.success(
            f"Arduino serial port is open: {serial_status.get('port')} "
            f"at {serial_status.get('baudrate')} baud."
        )
    else:
        st.warning("Arduino serial port is disconnected.")

    if serial_status.get("last_error"):
        st.error(f"Serial error: {serial_status['last_error']}")

    if st.session_state.get("skillmimic_connection_error"):
        st.error(st.session_state.skillmimic_connection_error)

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Connect Arduino",
            type="primary",
            use_container_width=True,
            disabled=(selected_port is None or serial_status["connected"]),
            key="connect_arduino_button",
        ):
            try:
                arduino.baudrate = int(selected_baudrate)
                connect_arduino(selected_port)
                st.success(f"Connected to {selected_port}.")
                st.rerun()
            except Exception as error:
                st.error(f"Connection failed: {type(error).__name__}: {error}")

    with col2:
        if st.button(
            "Disconnect",
            use_container_width=True,
            disabled=not serial_status["connected"],
            key="disconnect_arduino_button",
        ):
            try:
                disconnect_arduino()
                st.success("Arduino disconnected.")
                st.rerun()
            except Exception as error:
                st.error(f"Disconnection failed: {error}")

    st.caption(
        "This shared connection is used by Live Mirror and Manual Control. "
        "An open COM port confirms serial access, not pneumatic readiness."
    )
    st.caption(
        "Opening an Arduino Uno serial connection can reset the board. "
        "Keep pneumatic outputs isolated during connection and testing."
    )

    controller_status = controller.get_status()
    st.markdown("**Controller safety state**")
    if controller_status.get("emergency_stopped"):
        st.error("Emergency stop is latched in the controller.")
        physically_home = st.checkbox(
            "I have isolated the air supply, physically returned the glove to its open/home position, and verified it is safe to reset.",
            key="settings_confirm_physical_home"
        )
        if st.button(
            "Reset Arduino and software emergency stop",
            disabled=(not physically_home or not serial_status["connected"]),
            key="settings_reset_estop"
        ):
            try:
                controller.confirm_home(
                    physically_open_confirmed=True
                )
                st.success("Arduino and software emergency-stop latches reset.")
                st.rerun()
            except Exception as error:
                st.error(f"Emergency-stop reset failed: {error}")

    elif controller_status.get("faulted"):
        st.warning(
            "A controller fault is blocking new commands. This is not an "
            "operator-requested emergency stop."
        )
        inspected = st.checkbox(
            "I have inspected the glove and confirmed it is stationary.",
            key="settings_confirm_fault_inspected"
        )
        if st.button(
            "Acknowledge controller fault",
            disabled=not inspected,
            key="settings_ack_fault"
        ):
            try:
                controller.acknowledge_fault(
                    physically_inspected=True
                )
                st.success("Controller fault acknowledged.")
                st.rerun()
            except Exception as error:
                st.error(f"Fault acknowledgement failed: {error}")


# SAVE SETTINGS
# -----------------------------------------

st.divider()

st.markdown("### Save Configuration")

if st.button(
    "Save All Settings",
    type="primary",
    use_container_width=True
):

    st.session_state.settings_camera_index = int(camera_index)
    st.session_state.settings_camera_width = int(camera_width)
    st.session_state.settings_camera_height = int(camera_height)

    st.session_state.settings_max_hands = int(max_hands)

    st.session_state.settings_detection_confidence = float(
        detection_confidence
    )

    st.session_state.settings_tracking_confidence = float(
        tracking_confidence
    )

    st.session_state.settings_recording_fps = int(recording_fps)

    st.session_state.settings_playback_speed = float(
        playback_speed
    )

    hardware_config.setdefault("device", {})

    hardware_config["device"]["serial_port"] = selected_port
    hardware_config["device"]["baudrate"] = int(selected_baudrate)

    hardware_config.setdefault("tracking", {})

    hardware_config["tracking"]["max_hands"] = int(max_hands)

    hardware_config["tracking"]["detection_confidence"] = float(
        detection_confidence
    )

    hardware_config["tracking"]["tracking_confidence"] = float(
        tracking_confidence
    )

    hardware_config.setdefault("camera", {})

    hardware_config["camera"]["index"] = int(camera_index)
    hardware_config["camera"]["width"] = int(camera_width)
    hardware_config["camera"]["height"] = int(camera_height)

    hardware_config.setdefault("recording", {})
    hardware_config["recording"]["fps"] = int(recording_fps)

    hardware_config.setdefault("playback", {})

    hardware_config["playback"]["default_speed"] = float(
        playback_speed
    )

    try:

        with open(config_path, "w", encoding="utf-8") as file:

            json.dump(
                hardware_config,
                file,
                indent=4
            )

        st.success(
            "Application settings saved successfully."
        )

    except OSError as error:

        st.error(
            f"Could not save settings: {error}"
        )


# -----------------------------------------
# STORAGE INFORMATION
# -----------------------------------------

st.divider()

st.markdown("### 💾 Storage Information")

storage_locations = {
    "Recordings": AppSettings.RECORDINGS_DIRECTORY,
    "Processed Data": AppSettings.PROCESSED_DIRECTORY,
    "Exports": AppSettings.EXPORTS_DIRECTORY,
    "Logs": AppSettings.LOG_DIRECTORY
}

for name, directory in storage_locations.items():

    st.write(f"**{name}:** `{directory}`")


# -----------------------------------------
# APPLICATION INFORMATION
# -----------------------------------------

st.divider()

st.markdown("### ℹ️ Application Information")

col1, col2, col3 = st.columns(3)

app_info = AppSettings.get_app_info()

col1.metric(
    "Application",
    app_info["name"]
)

col2.metric(
    "Version",
    app_info["version"]
)

col3.metric(
    "Environment",
    "Local"
)


# -----------------------------------------
# FOOTER
# -----------------------------------------

st.markdown(
    """
    <div class="footer">
        SkillMimic · System Configuration
    </div>
    """,
    unsafe_allow_html=True
)
