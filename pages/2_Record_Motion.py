
import streamlit as st
import sys
import time
import cv2
import numpy as np
import base64

from pathlib import Path

# -----------------------------------------
# PROJECT PATH
# -----------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# -----------------------------------------
# PROJECT IMPORTS
# -----------------------------------------

from core.camera.camera_manager import CameraManager
from core.tracking.hand_tracker import HandTracker
from core.tracking.landmark_processor import LandmarkProcessor
from core.tracking.gesture_classifier import GestureClassifier

from core.motion.motion_recorder import MotionRecorder
from core.motion.motion_processor import MotionProcessor

from core.storage.skill_manager import SkillManager


# -----------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------

st.markdown(
    """
    <div class="page-header">
        <div>
            <p class="eyebrow">MOVEMENT CAPTURE</p>
            <h1>Record Motion</h1>
            <p class="subtitle">
                Capture natural hand movements and save them as reusable skills.
            </p>
        </div>
        <div class="system-badge">● CAPTURE WORKSPACE</div>
    </div>
    """,
    unsafe_allow_html=True
)


# -----------------------------------------
# INITIALIZE SESSION COMPONENTS
# -----------------------------------------

def initialize_recording_components():

    if "camera_manager" not in st.session_state:
        st.session_state.camera_manager = CameraManager()

    if (
        "hand_tracker" not in st.session_state
        or getattr(st.session_state.hand_tracker, "max_hands", None) != 1
    ):
        old_tracker = st.session_state.get("hand_tracker")
        if old_tracker is not None:
            try:
                old_tracker.close()
            except Exception:
                pass
        st.session_state.hand_tracker = HandTracker(max_hands=1)

    if "landmark_processor" not in st.session_state:
        st.session_state.landmark_processor = LandmarkProcessor()

    if "motion_recorder" not in st.session_state:
        st.session_state.motion_recorder = MotionRecorder(
            target_fps=15
        )

    if "motion_processor" not in st.session_state:
        st.session_state.motion_processor = MotionProcessor()

    if "skill_manager" not in st.session_state:
        st.session_state.skill_manager = SkillManager()

    if "gesture_classifier" not in st.session_state:

        try:
            st.session_state.gesture_classifier = GestureClassifier()
            st.session_state.gesture_classifier_error = None

        except Exception as error:
            st.session_state.gesture_classifier = None
            st.session_state.gesture_classifier_error = str(error)

    if "recording_active" not in st.session_state:
        st.session_state.recording_active = False

    if "last_recording" not in st.session_state:
        st.session_state.last_recording = None

    if "recording_start_time" not in st.session_state:
        st.session_state.recording_start_time = None

    if "recording_name" not in st.session_state:
        st.session_state.recording_name = ""

    if "recording_description" not in st.session_state:
        st.session_state.recording_description = ""

    if "camera_error" not in st.session_state:
        st.session_state.camera_error = None

    if "mirror_preview" not in st.session_state:
        st.session_state.mirror_preview = True


initialize_recording_components()


# -----------------------------------------
# COMPONENT REFERENCES
# -----------------------------------------

camera = st.session_state.camera_manager
tracker = st.session_state.hand_tracker
landmark_processor = st.session_state.landmark_processor
recorder = st.session_state.motion_recorder
motion_processor = st.session_state.motion_processor
skill_manager = st.session_state.skill_manager
classifier = st.session_state.gesture_classifier


# -----------------------------------------
# RECORDING DETAILS
# -----------------------------------------

st.markdown("### Skill Information")

col1, col2 = st.columns(2)

with col1:
    skill_name = st.text_input(
        "Movement Name",
        placeholder="Example: Hand Opening and Closing",
        key="motion_skill_name"
    )

with col2:
    skill_description = st.text_input(
        "Description",
        placeholder="Describe the movement",
        key="motion_skill_description"
    )


st.divider()


# -----------------------------------------
# CAMERA PREVIEW SETTINGS
# -----------------------------------------

st.markdown("### Camera Settings")

st.session_state.mirror_preview = st.checkbox(
    "Mirror camera preview",
    value=st.session_state.mirror_preview,
    help="Flip the displayed webcam image horizontally."
)


# -----------------------------------------
# RECORDING CONTROLS
# -----------------------------------------

st.markdown("### Recording Controls")

col1, col2, col3 = st.columns(3)

with col1:
    start_clicked = st.button(
        "Start Recording",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.recording_active
    )

with col2:
    stop_clicked = st.button(
        "Stop Recording",
        use_container_width=True,
        disabled=not st.session_state.recording_active
    )

with col3:
    clear_clicked = st.button(
        "Clear Recording",
        use_container_width=True,
        disabled=st.session_state.recording_active
    )


# -----------------------------------------
# START RECORDING
# -----------------------------------------

if start_clicked:

    if not skill_name.strip():

        st.error("Please enter a movement name.")

    else:

        try:

            if camera.start():

                recorder.clear_recording()

                landmark_processor.reset()

                if classifier is not None:
                    classifier.reset_history()

                recorder.start_recording()

                st.session_state.recording_start_time = (
                    time.perf_counter()
                )

                st.session_state.recording_name = skill_name.strip()

                st.session_state.recording_description = (
                    skill_description.strip()
                )

                st.session_state.recording_active = True

                st.session_state.last_recording = None

                st.session_state.camera_error = None

                st.rerun()

            else:

                st.error(
                    "Unable to access the webcam. "
                    "Check camera permissions and availability."
                )

        except Exception as error:

            st.error(f"Camera startup failed: {error}")


# -----------------------------------------
# STOP RECORDING
# -----------------------------------------

if stop_clicked:

    try:

        st.session_state.last_recording = (
            recorder.stop_recording()
        )

        st.session_state.recording_active = False

        camera.release()

        tracker.close()

        st.session_state.hand_tracker = HandTracker(
            max_hands=2
        )

        st.session_state.recording_start_time = None

        st.session_state.camera_error = None

        st.rerun()

    except Exception as error:

        st.error(f"Unable to stop recording: {error}")


# -----------------------------------------
# CLEAR RECORDING
# -----------------------------------------

if clear_clicked:

    recorder.clear_recording()

    motion_processor.reset()

    st.session_state.last_recording = None

    st.session_state.camera_error = None

    st.rerun()


# -----------------------------------------
# LIVE CAMERA PREVIEW
# BASE64 JPEG DISPLAY
# -----------------------------------------

st.divider()

st.markdown("### Live Movement Preview")


@st.fragment(run_every=0.15)
def live_recording_preview():

    if not st.session_state.recording_active:

        st.info(
            "Camera preview will appear when you start recording."
        )

        st.caption(
            "Start Recording to activate the live webcam feed."
        )

        return

    camera = st.session_state.camera_manager

    tracker = st.session_state.hand_tracker

    landmark_processor = st.session_state.landmark_processor

    recorder = st.session_state.motion_recorder

    classifier = st.session_state.gesture_classifier

    try:

        # -------------------------------------
        # READ CAMERA FRAME
        # -------------------------------------

        success, frame = camera.read_frame()

        if not success or frame is None:

            st.error(
                "Unable to receive a camera frame. "
                "Check whether another application is using the webcam."
            )

            return

        # -------------------------------------
        # VALIDATE CAMERA FRAME
        # -------------------------------------

        if (
            not isinstance(frame, np.ndarray)
            or frame.ndim != 3
            or frame.shape[2] != 3
        ):

            st.error("Invalid camera frame received.")

            return

        # -------------------------------------
        # GESTURE RECOGNITION
        # -------------------------------------

        gesture_data = {
            "label": "Unknown",
            "confidence": 0.0,
            "accepted": False
        }

        if classifier is not None:

            try:

                prediction = classifier.predict(
                    frame.copy()
                )

                if prediction:

                    gesture_data = {
                        "label": prediction.get(
                            "gesture",
                            "Unknown"
                        ),
                        "confidence": float(
                            prediction.get("confidence", 0.0)
                        ),
                        "accepted": bool(
                            prediction.get("accepted", False)
                        )
                    }

            except Exception as error:

                st.warning(
                    f"Gesture recognition error: {error}"
                )

        # -------------------------------------
        # HAND DETECTION
        # -------------------------------------

        annotated_frame, detected_hands = tracker.detect(
            frame
        )

        if annotated_frame is None:

            st.error(
                "Hand tracking did not return a valid image."
            )

            return

        # -------------------------------------
        # PROCESS ONE HAND
        # -------------------------------------
        # The pneumatic glove has one five-finger actuator set. HandTracker
        # returns a list of hand dictionaries, while LandmarkProcessor
        # processes one hand's 21 landmarks at a time.
        processed_hands = []

        if detected_hands:
            selected_hand = detected_hands[0]

            try:
                result = landmark_processor.process(
                    selected_hand.get("landmarks", selected_hand)
                )

                processed_hands = [{
                    "hand_id": selected_hand.get("hand_id", 0),
                    "handedness": selected_hand.get("handedness", "Unknown"),
                    "finger_curls": result["finger_curls"],
                }]

            except (ValueError, TypeError, KeyError) as landmark_error:
                st.warning(
                    "Hand detected, but landmarks could not be converted: "
                    f"{landmark_error}"
                )
                processed_hands = []

        # Keep empty frames during brief tracking loss so playback timing
        # remains aligned with the original recording.
        recorder.record_frame(processed_hands)

        # -------------------------------------
        # MIRROR DISPLAY ONLY
        # -------------------------------------

        display_frame = annotated_frame.copy()

        if st.session_state.mirror_preview:

            display_frame = cv2.flip(
                display_frame,
                1
            )

        # -------------------------------------
        # BASE64 IMAGE RENDERING
        # -------------------------------------

        encoded_ok, buffer = cv2.imencode(
            ".jpg",
            display_frame,
            [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        if not encoded_ok:

            st.error("Unable to encode camera image.")

            return

        image_base64 = base64.b64encode(
            buffer.tobytes()
        ).decode("utf-8")

        image_html = f"""
        <div style="
            width:100%;
            overflow:hidden;
            border-radius:12px;
        ">
            <img
                src="data:image/jpeg;base64,{image_base64}"
                alt="Live hand movement preview"
                style="
                    display:block;
                    width:100%;
                    height:auto;
                    object-fit:contain;
                    border-radius:12px;
                "
            />
        </div>
        """

        st.markdown(
            image_html,
            unsafe_allow_html=True
        )

        # -------------------------------------
        # RECORDING STATISTICS
        # -------------------------------------

        elapsed = (
            time.perf_counter()
            - st.session_state.recording_start_time
        )

        frame_count = len(recorder.frames)

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Recording Time",
                f"{elapsed:.1f} sec"
            )

        with col2:

            st.metric(
                "Hands Detected",
                len(processed_hands)
            )

        with col3:

            st.metric(
                "Captured Frames",
                frame_count
            )

        # -------------------------------------
        # GESTURE STATUS
        # -------------------------------------

        st.markdown("### Gesture Recognition")

        if classifier is None:

            st.error(
                "Gesture classifier is unavailable. "
                "Landmark recording is still active."
            )

            if st.session_state.gesture_classifier_error:

                st.caption(
                    st.session_state.gesture_classifier_error
                )

        elif gesture_data["accepted"]:

            st.success(
                f"Recognized: {gesture_data['label']} "
                f"({gesture_data['confidence']:.1%})"
            )

        else:

            st.warning(
                "No accepted gesture recognized."
            )

        # -------------------------------------
        # HAND TRACKING STATUS
        # -------------------------------------

        if len(processed_hands) == 0:

            st.warning(
                "No hands detected. Keep your hand visible "
                "inside the camera frame."
            )

        else:

            st.success("Hand tracking is active.")

    except Exception as error:

        st.error(
            f"Live preview error: "
            f"{type(error).__name__}: {error}"
        )


live_recording_preview()


# -----------------------------------------
# RECORDING SUMMARY
# -----------------------------------------

st.divider()

st.markdown("### Recording Summary")

recording = st.session_state.last_recording

if recording:

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Duration",
        f"{recording['duration']:.2f} sec"
    )

    col2.metric(
        "Total Frames",
        recording["total_frames"]
    )

    col3.metric(
        "Recording FPS",
        recording["target_fps"]
    )

    st.success(
        "Movement recording is ready to be saved."
    )

    # -------------------------------------
    # GESTURE SUMMARY
    # -------------------------------------

    recognized_gestures = {}

    for frame_data in recording.get("frames", []):

        gesture = frame_data.get("gesture") or {}

        label = gesture.get("label", "Unknown")

        if gesture.get("accepted", False):

            recognized_gestures[label] = (
                recognized_gestures.get(label, 0) + 1
            )

    st.markdown("#### Recognized Gesture Summary")

    if recognized_gestures:

        for gesture_name, count in recognized_gestures.items():

            st.write(
                f"**{gesture_name}:** {count} frames"
            )

    else:

        st.warning(
            "No accepted gestures were recorded. "
            "The saved skill will contain landmarks only."
        )

    # -------------------------------------
    # SAVE SKILL
    # -------------------------------------

    save_clicked = st.button(
        "Save Skill to Library",
        type="primary",
        use_container_width=True
    )

    if save_clicked:

        if not st.session_state.recording_name.strip():

            st.error("Movement name is required.")

        elif not recording["frames"]:

            st.error("No movement frames were captured.")

        else:

            try:

                processed_motion = (
                    motion_processor.process_recording(
                        recording
                    )
                )

                result = skill_manager.save_skill(
                    skill_name=st.session_state.recording_name,
                    motion_data=processed_motion,
                    description=st.session_state.recording_description
                )

                st.success(
                    f"Skill '{result['name']}' saved successfully."
                )

                st.session_state.last_recording = None

                recorder.clear_recording()

                st.rerun()

            except FileExistsError:

                st.error(
                    "A skill with this name already exists. "
                    "Choose another name."
                )

            except Exception as error:

                st.error(
                    f"Unable to save the skill: {error}"
                )

else:

    st.info(
        "No completed recording available. "
        "Start and stop a recording to see its summary here."
    )


# -----------------------------------------
# PAGE FOOTER
# -----------------------------------------

st.markdown(
    """
    <div class="footer">
        SkillMimic · Continuous Movement Recording
    </div>
    """,
    unsafe_allow_html=True
)
