
import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="Manual Control | SkillMimic",
    page_icon="🖐️",
    layout="wide"
)

from core.hardware.controller_access import get_motion_controller


FINGERS = (
    "thumb",
    "index",
    "middle",
    "ring",
    "little"
)


st.title("Manual Control")
st.caption(
    "Control each finger independently using the pneumatic glove."
)


# --------------------------------------------------
# CONTROLLER CONNECTION
# --------------------------------------------------

try:
    controller = get_motion_controller()

except Exception as error:
    st.error(f"Controller unavailable: {error}")
    st.stop()


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

for finger in FINGERS:
    key = f"manual_{finger}"

    if key not in st.session_state:
        st.session_state[key] = 0

if "manual_pending_action" not in st.session_state:
    st.session_state.manual_pending_action = None


# --------------------------------------------------
# ACTION CALLBACKS
# --------------------------------------------------

def set_finger_values(value):
    for finger in FINGERS:
        st.session_state[f"manual_{finger}"] = value


def request_all_open():
    set_finger_values(0)
    st.session_state.manual_pending_action = "open"


def request_all_closed():
    set_finger_values(100)
    st.session_state.manual_pending_action = "close"


# --------------------------------------------------
# CONTROLLER STATUS
# --------------------------------------------------

status = controller.get_status()

arduino_connected = status.get("connected", False)
active = status.get("active", False)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Arduino",
    "Connected" if arduino_connected else "Disconnected"
)

col2.metric(
    "Movement",
    "Busy" if active else "Idle"
)

col3.metric(
    "Queued Tasks",
    status.get("queued_tasks", 0)
)


if status.get("emergency_stopped", False):
    st.error(
        "Emergency stop is active. Confirm the physical home "
        "position before resuming movement."
    )


# --------------------------------------------------
# FINGER SLIDERS
# --------------------------------------------------

st.divider()

st.subheader("Finger Bend Control")

st.caption(
    "0% = Fully Open | 100% = Fully Curled"
)

with st.form("manual_control_form"):

    columns = st.columns(5)

    for index, finger in enumerate(FINGERS):

        with columns[index]:

            st.slider(
                finger.title(),
                min_value=0,
                max_value=100,
                step=5,
                key=f"manual_{finger}"
            )

    submit = st.form_submit_button(
        "Send Movement",
        use_container_width=True,
        type="primary"
    )


# --------------------------------------------------
# SUBMIT CUSTOM MOVEMENT
# --------------------------------------------------

if submit:

    targets = {
        finger: int(st.session_state[f"manual_{finger}"])
        for finger in FINGERS
    }

    try:
        controller.submit_targets(
            targets,
            source="manual"
        )

        st.success(
            "Movement request submitted. The controller "
            "handles task completion and cooldown."
        )

    except Exception as error:
        st.error(f"Movement failed: {error}")


# --------------------------------------------------
# OPEN ALL / CLOSE ALL
# --------------------------------------------------

st.divider()

st.subheader("Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    st.button(
        "Open All",
        use_container_width=True,
        on_click=request_all_open
    )

with col2:
    st.button(
        "Close All",
        use_container_width=True,
        on_click=request_all_closed
    )

with col3:
    emergency_clicked = st.button(
        "EMERGENCY STOP",
        type="primary",
        use_container_width=True
    )


# Process quick actions after callbacks update the slider state.
pending_action = st.session_state.manual_pending_action

if pending_action is not None:

    value = 0 if pending_action == "open" else 100

    targets = {
        finger: value
        for finger in FINGERS
    }

    try:
        controller.submit_targets(
            targets,
            source="manual"
        )

        st.success(
            f"{pending_action.title()} All movement submitted."
        )

    except Exception as error:
        st.error(f"Movement failed: {error}")

    finally:
        st.session_state.manual_pending_action = None


# --------------------------------------------------
# EMERGENCY STOP
# --------------------------------------------------

if emergency_clicked:

    try:
        controller.emergency_stop()

        st.error(
            "Emergency stop requested. Check the physical "
            "system before attempting another movement."
        )

    except Exception as error:
        st.error(f"Emergency stop failed: {error}")


# --------------------------------------------------
# PHYSICAL HOME CONFIRMATION
# --------------------------------------------------

st.divider()

st.subheader("Physical Home Confirmation")

st.warning(
    "Software reset does not physically open the fingers. "
    "First verify that all fingers are fully open and the "
    "pneumatic system is depressurized."
)

physically_open = st.checkbox(
    "I have physically checked that all fingers are fully open "
    "and the pneumatic system is safe."
)

if st.button(
    "Confirm Home",
    disabled=not physically_open,
    use_container_width=True
):

    try:
        controller.confirm_home(
            physically_open_confirmed=True
        )

        st.success("Physical home position confirmed.")

    except Exception as error:
        st.error(f"Home confirmation failed: {error}")


# --------------------------------------------------
# DETAILED CONTROLLER STATUS
# --------------------------------------------------

st.divider()

st.subheader("Controller Status")

status = controller.get_status()

status_data = {
    "Active": status.get("active"),
    "Current Task": status.get("current_task"),
    "Queued Tasks": status.get("queued_tasks"),
    "Completed Tasks": status.get("completed_tasks"),
    "Cooldown": status.get("cooldown_seconds"),
    "Last Result": status.get("last_result"),
    "Last Error": status.get("last_error")
}

st.json(status_data)

if st.button("Refresh Status"):
    st.rerun()
