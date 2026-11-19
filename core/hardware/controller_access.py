
import streamlit as st

from core.hardware.arduino_connection import ArduinoConnection
from core.hardware.motion_controller import MotionController


DEFAULT_BAUDRATE = 9600
DEFAULT_DURATION_MS = 800


def _initialize_state():
    defaults = {
        "skillmimic_arduino": None,
        "skillmimic_controller": None,
        "skillmimic_port": None,
        "skillmimic_connection_error": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_arduino_connection():
    """
    Return the shared ArduinoConnection instance.
    """

    _initialize_state()

    arduino = st.session_state.skillmimic_arduino

    if arduino is None:
        arduino = ArduinoConnection(
            port=st.session_state.skillmimic_port,
            baudrate=DEFAULT_BAUDRATE
        )

        st.session_state.skillmimic_arduino = arduino

    return arduino


def get_motion_controller():
    """
    Return the shared MotionController instance.
    """

    _initialize_state()

    controller = st.session_state.skillmimic_controller

    if controller is None:
        arduino = get_arduino_connection()

        controller = MotionController(
            arduino=arduino,
            default_duration_ms=DEFAULT_DURATION_MS,
            cooldown_seconds=0,
            movement_timeout=40
        )

        st.session_state.skillmimic_controller = controller

    return controller


def get_available_ports():
    """
    Return available serial ports.
    """

    arduino = get_arduino_connection()
    return arduino.get_available_ports()


def connect_arduino(port):
    """
    Connect the existing shared Arduino instance.
    """

    _initialize_state()

    if not port:
        raise ValueError("Select an Arduino COM port.")

    arduino = get_arduino_connection()
    controller = get_motion_controller()

    if arduino.is_connected():
        if arduino.port == port:
            return True

        controller.clear_pending()
        arduino.disconnect()

    try:
        result = arduino.connect(port)

        if not result:
            raise ConnectionError("Arduino connection failed.")

        controller.set_arduino(arduino)

        st.session_state.skillmimic_port = port
        st.session_state.skillmimic_connection_error = None

        return True

    except Exception as error:
        st.session_state.skillmimic_connection_error = str(error)
        raise


def disconnect_arduino():
    """
    Disconnect Arduino after pending work is cleared.
    """

    _initialize_state()

    controller = get_motion_controller()
    arduino = get_arduino_connection()

    controller.clear_pending()

    if controller.get_status()["active"]:
        raise RuntimeError(
            "Wait for the current movement to finish before disconnecting."
        )

    arduino.disconnect()

    st.session_state.skillmimic_port = None
    return True


def is_arduino_connected():
    """
    Return connection state.
    """

    try:
        return get_arduino_connection().is_connected()
    except Exception:
        return False


def get_hardware_status():
    """
    Return combined Arduino and controller status.
    """

    arduino = get_arduino_connection()
    controller = get_motion_controller()

    return {
        "arduino": arduino.get_status(),
        "controller": controller.get_status()
    }


def emergency_stop():
    """
    Trigger the controller emergency stop.
    """

    controller = get_motion_controller()
    return controller.emergency_stop()


def reset_emergency_stop(physically_open_confirmed=False):
    """
    Reset the software emergency-stop latch only after
    the operator physically checks the glove.
    """

    controller = get_motion_controller()

    return controller.confirm_home(
        physically_open_confirmed=physically_open_confirmed
    )
