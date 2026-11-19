
import streamlit as st
import streamlit.components.v1 as components
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tracking.gesture_labels import (
    GESTURE_LABELS,
    GESTURE_DISPLAY_NAMES,
    DEMO_KEYBOARD_SHORTCUTS
)

st.set_page_config(
    page_title="Demo Actions | SkillMimic",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 Demo Actions")
st.caption("Demonstrate predefined hand gestures without recording movement.")

if "demo_action" not in st.session_state:
    st.session_state.demo_action = None

if "demo_history" not in st.session_state:
    st.session_state.demo_history = []

st.subheader("Select a Gesture")

columns = st.columns(3)

for index, gesture in enumerate(GESTURE_LABELS):
    with columns[index % 3]:
        display_name = GESTURE_DISPLAY_NAMES.get(
            gesture, gesture
        )

        if st.button(
            display_name,
            key=f"demo_{gesture}",
            use_container_width=True
        ):
            st.session_state.demo_action = gesture
            st.session_state.demo_history.append(gesture)

st.divider()

st.subheader("Keyboard Shortcut")

st.info("Press F to select the Open Hand demo action.")

components.html(
    """
    <script>
    const doc = window.parent.document;

    if (!window.parent.skillMimicDemoKeyHandler) {
        window.parent.skillMimicDemoKeyHandler = true;

        doc.addEventListener("keydown", function(event) {
            const target = event.target;
            if (
                target &&
                (
                    target.tagName === "INPUT" ||
                    target.tagName === "TEXTAREA" ||
                    target.isContentEditable
                )
            ) {
                return;
            }

            if (event.key.toLowerCase() === "f") {
                const buttons = Array.from(
                    doc.querySelectorAll("button")
                );

                const openButton = buttons.find(
                    button =>
                        button.innerText.trim() === "Open Hand"
                );

                if (openButton) {
                    openButton.click();
                }
            }
        });
    }
    </script>
    """,
    height=0
)

st.divider()

st.subheader("Current Demo Action")

if st.session_state.demo_action:
    gesture = st.session_state.demo_action

    st.success(
        f"Selected: {GESTURE_DISPLAY_NAMES.get(gesture, gesture)}"
    )
else:
    st.info("No demo action selected.")

if st.button("Stop Demo", type="secondary"):
    st.session_state.demo_action = None
    st.rerun()

with st.expander("Demo History"):
    if st.session_state.demo_history:
        for index, gesture in enumerate(
            reversed(st.session_state.demo_history[-20:]),
            start=1
        ):
            st.write(
                f"{index}. {GESTURE_DISPLAY_NAMES.get(gesture, gesture)}"
            )
    else:
        st.write("No demo actions performed yet.")

st.caption(
    "Demo actions currently update the software interface only. "
    "No hardware commands are transmitted."
)
