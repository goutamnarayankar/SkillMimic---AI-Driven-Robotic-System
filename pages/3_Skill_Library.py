
import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.storage.skill_manager import SkillManager
from core.motion.motion_replayer import MotionReplayer
from core.hardware.controller_access import get_motion_controller


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Skill Library | SkillMimic",
    page_icon="🖐️",
    layout="wide"
)

FINGERS = ("thumb", "index", "middle", "ring", "little")


# =========================================================
# SESSION INITIALIZATION
# =========================================================

DEFAULTS = {
    "skill_manager": None,
    "motion_replayer": None,
    "selected_skill": None,
    "loaded_motion": None,
    "loaded_skill_name": None,
    "delete_skill_name": None,
    "delete_skill_confirm": False,
    "skill_playback_speed": 1.0,
    "skill_replay_mode_acquired": False,
    "skill_replay_error": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.skill_manager is None:
    st.session_state.skill_manager = SkillManager()

if st.session_state.motion_replayer is None:
    st.session_state.motion_replayer = MotionReplayer(
        motion_controller=get_motion_controller()
    )

skill_manager = st.session_state.skill_manager
motion_replayer = st.session_state.motion_replayer


# =========================================================
# HELPERS
# =========================================================

def get_controller():
    return get_motion_controller()


def reset_replay_state():
    st.session_state.skill_replay_error = None
    st.session_state.skill_replay_mode_acquired = False


def release_replay_mode():
    if not st.session_state.skill_replay_mode_acquired:
        return

    try:
        get_controller().release_mode("skill_replay")
    finally:
        st.session_state.skill_replay_mode_acquired = False


def load_selected_skill(skill_name):
    if motion_replayer.is_playing() or motion_replayer.is_paused():
        raise RuntimeError("Stop playback before loading another skill.")

    skill_data = skill_manager.load_skill(skill_name)
    motion_data = skill_data["motion"]

    motion_replayer.load_motion(motion_data)

    st.session_state.loaded_motion = motion_data
    st.session_state.loaded_skill_name = skill_name
    st.session_state.selected_skill = skill_name

    reset_replay_state()

    return skill_data


def start_replay():
    if st.session_state.loaded_motion is None:
        raise ValueError("Load a skill before starting playback.")

    if motion_replayer.is_playing() or motion_replayer.is_paused():
        raise RuntimeError("A replay is already active.")

    controller = get_controller()
    status = controller.get_status()

    if not status.get("connected"):
        raise ConnectionError("Arduino is not connected.")

    if status.get("emergency_stopped"):
        raise RuntimeError(
            "Emergency stop is active. Recover the controller safely first."
        )

    if status.get("active") or status.get("queued_tasks", 0) > 0:
        raise RuntimeError(
            "The pneumatic controller is busy. Wait until it becomes idle."
        )

    controller.acquire_mode("skill_replay")
    st.session_state.skill_replay_mode_acquired = True

    try:
        motion_replayer.play(
            speed=st.session_state.skill_playback_speed,
            loop=False
        )

    except Exception:
        release_replay_mode()
        raise


def stop_replay(emergency=False):
    controller = get_controller()

    if emergency:
        controller.emergency_stop()

    motion_replayer.stop(wait=False)

    if not emergency:
        release_replay_mode()


# =========================================================
# PAGE HEADER
# =========================================================

st.markdown(
    """
    <div class="page-header">
        <div>
            <p class="eyebrow">MOVEMENT MANAGEMENT</p>
            <h1>Skill Library</h1>
            <p class="subtitle">
                Manage, explore and reproduce recorded hand movements.
            </p>
        </div>
        <div class="system-badge">● SKILL STORAGE</div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# LIBRARY OVERVIEW
# =========================================================

skills = skill_manager.list_skills()

st.markdown("### Library Overview")

col1, col2, col3 = st.columns(3)

total_duration = sum(
    float(skill.get("duration", 0))
    for skill in skills
)

total_frames = sum(
    int(skill.get("total_frames", 0))
    for skill in skills
)

col1.metric("Total Skills", len(skills))
col2.metric("Total Recording Time", f"{total_duration:.1f} sec")
col3.metric("Total Captured Frames", total_frames)

st.divider()


# =========================================================
# SEARCH AND SORT
# =========================================================

st.markdown("### Explore Your Skills")

search_query = st.text_input(
    "Search Skills",
    placeholder="Search by movement name or description..."
)

sort_option = st.selectbox(
    "Sort Skills",
    [
        "Recently Created",
        "Name (A-Z)",
        "Longest Duration",
        "Most Frames"
    ]
)

query = search_query.strip().lower()

filtered_skills = [
    skill for skill in skills
    if (
        query in skill.get("name", "").lower()
        or query in skill.get("description", "").lower()
    )
]

if sort_option == "Recently Created":
    filtered_skills.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True
    )

elif sort_option == "Name (A-Z)":
    filtered_skills.sort(
        key=lambda item: item.get("name", "").lower()
    )

elif sort_option == "Longest Duration":
    filtered_skills.sort(
        key=lambda item: float(item.get("duration", 0)),
        reverse=True
    )

elif sort_option == "Most Frames":
    filtered_skills.sort(
        key=lambda item: int(item.get("total_frames", 0)),
        reverse=True
    )


# =========================================================
# SAVED SKILLS
# =========================================================

st.markdown(f"### Saved Movements ({len(filtered_skills)})")

if not filtered_skills:

    st.info(
        "No saved movements found. "
        "Go to Record Motion, capture a movement and save it."
    )

else:

    for index, skill in enumerate(filtered_skills):

        skill_name = skill.get("name", "Unnamed Skill")

        with st.container(border=True):

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"#### 🖐️ {skill_name}")

                st.caption(
                    skill.get("description")
                    or "No description provided."
                )

                st.caption(
                    f"Created: {skill.get('created_at', 'Unknown')}"
                )

            with col2:
                st.metric(
                    "Duration",
                    f"{float(skill.get('duration', 0)):.2f} sec"
                )

            with col3:
                st.metric(
                    "Frames",
                    skill.get("total_frames", 0)
                )

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button(
                    "View Details",
                    key=f"view_{index}",
                    use_container_width=True
                ):
                    st.session_state.selected_skill = skill_name
                    st.rerun()

            with b2:
                if st.button(
                    "Load Skill",
                    key=f"load_{index}",
                    use_container_width=True,
                    disabled=(
                        motion_replayer.is_playing()
                        or motion_replayer.is_paused()
                    )
                ):
                    try:
                        load_selected_skill(skill_name)
                        st.success(f"{skill_name} loaded successfully.")
                        st.rerun()

                    except Exception as error:
                        st.error(f"Unable to load skill: {error}")

            with b3:
                if st.button(
                    "Delete",
                    key=f"delete_{index}",
                    use_container_width=True,
                    disabled=(
                        motion_replayer.is_playing()
                        or motion_replayer.is_paused()
                    )
                ):
                    st.session_state.delete_skill_name = skill_name
                    st.session_state.delete_skill_confirm = True
                    st.rerun()


# =========================================================
# DELETE CONFIRMATION
# =========================================================

if st.session_state.delete_skill_confirm:

    delete_name = st.session_state.delete_skill_name

    st.warning(f"Are you sure you want to delete '{delete_name}'?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Confirm Delete",
            type="primary",
            use_container_width=True
        ):
            try:
                if skill_manager.delete_skill(delete_name):

                    if st.session_state.selected_skill == delete_name:
                        st.session_state.selected_skill = None

                    if st.session_state.loaded_skill_name == delete_name:
                        st.session_state.loaded_motion = None
                        st.session_state.loaded_skill_name = None

                    st.success("Skill deleted successfully.")

                else:
                    st.error("Unable to delete the selected skill.")

            except Exception as error:
                st.error(f"Delete failed: {error}")

            st.session_state.delete_skill_confirm = False
            st.session_state.delete_skill_name = None
            st.rerun()

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.delete_skill_confirm = False
            st.session_state.delete_skill_name = None
            st.rerun()


# =========================================================
# SELECTED SKILL DETAILS
# =========================================================

selected_name = st.session_state.selected_skill

if selected_name:

    st.divider()
    st.markdown("### Selected Skill Details")

    try:
        selected_data = skill_manager.load_skill(selected_name)
        motion = selected_data["motion"]

        st.markdown(f"#### {selected_data['name']}")

        st.write(
            selected_data.get("description")
            or "No description available."
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Duration",
            f"{float(motion.get('duration', 0)):.2f} sec"
        )

        c2.metric(
            "Frames",
            motion.get("total_frames", 0)
        )

        c3.metric(
            "Recording FPS",
            motion.get("target_fps", 0)
        )

        with st.expander("View Recorded Movement Data"):
            st.json(motion, expanded=False)

    except Exception as error:
        st.error(f"Unable to display skill details: {error}")


# =========================================================
# SKILL PLAYBACK
# =========================================================

st.divider()
st.markdown("### Physical Skill Playback")

loaded_motion = st.session_state.loaded_motion
loaded_name = st.session_state.loaded_skill_name

if loaded_motion is None:

    st.info("Load a saved skill to prepare it for physical playback.")

else:

    st.success(f"Loaded Skill: **{loaded_name}**")

    try:
        controller = get_controller()
        hardware = controller.get_status()

        st.write(
            f"Arduino connection: "
            f"{'Connected' if hardware.get('connected') else 'Disconnected'}"
        )

        st.caption(
            f"Controller: {'BUSY' if hardware.get('active') else 'IDLE'}"
            f" · Queued commands: {hardware.get('queued_tasks', 0)}"
        )

        if hardware.get("emergency_stopped"):
            st.error(
                "Emergency stop is active. Recover the controller "
                "safely before starting playback."
            )

    except Exception as error:
        controller = None
        hardware = {}
        st.error(f"Motion controller unavailable: {error}")

    st.warning(
        "Safety: Secure the glove, keep fingers clear of pinch points, "
        "use low safe air pressure, and keep the pneumatic shutoff accessible."
    )

    playback_speed = st.select_slider(
        "Playback Speed",
        options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
        value=st.session_state.skill_playback_speed,
        disabled=(
            motion_replayer.is_playing()
            or motion_replayer.is_paused()
        )
    )

    st.session_state.skill_playback_speed = playback_speed

    status = motion_replayer.get_status()
    current_state = status["state"]

    # -----------------------------------------------------
    # PLAYBACK CONTROLS
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
            "▶ Play",
            type="primary",
            use_container_width=True,
            disabled=(
                controller is None
                or motion_replayer.is_playing()
                or motion_replayer.is_paused()
                or hardware.get("emergency_stopped", False)
            )
        ):
            try:
                reset_replay_state()
                start_replay()
                st.rerun()

            except Exception as error:
                st.session_state.skill_replay_error = str(error)
                st.error(str(error))

    with col2:
        if st.button(
            "⏸ Pause",
            use_container_width=True,
            disabled=not motion_replayer.is_playing()
        ):
            motion_replayer.pause()
            st.rerun()

    with col3:
        if st.button(
            "▶ Resume",
            use_container_width=True,
            disabled=not motion_replayer.is_paused()
        ):
            motion_replayer.resume()
            st.rerun()

    with col4:
        if st.button(
            "■ Stop",
            use_container_width=True,
            disabled=not (
                motion_replayer.is_playing()
                or motion_replayer.is_paused()
            )
        ):
            try:
                stop_replay(emergency=False)
                st.rerun()

            except Exception as error:
                st.session_state.skill_replay_error = str(error)
                st.error(str(error))

    # -----------------------------------------------------
    # EMERGENCY STOP
    # -----------------------------------------------------

    if motion_replayer.is_playing() or motion_replayer.is_paused():

        if st.button(
            "EMERGENCY STOP",
            type="primary",
            use_container_width=True
        ):
            try:
                stop_replay(emergency=True)
                st.warning(
                    "Emergency stop sent. Inspect the glove and "
                    "pneumatic system before attempting recovery."
                )
                st.rerun()

            except Exception as error:
                st.error(f"Emergency stop failed: {error}")

    # -----------------------------------------------------
    # PLAYBACK STATUS REFRESH
    # -----------------------------------------------------

    @st.fragment(run_every=0.5)
    def playback_status():

        replayer = st.session_state.motion_replayer
        current = replayer.get_status()

        if current["state"] in ("completed", "stopped", "error"):
            try:
                release_replay_mode()
            except Exception as error:
                st.session_state.skill_replay_error = str(error)

        if current["state"] == "error":
            st.session_state.skill_replay_error = current["last_error"]

        if current["state"] == "completed":
            st.success("Skill playback completed.")

        elif current["state"] == "paused":
            st.info("Playback paused.")

        elif current["state"] == "playing":
            st.info("Playing recorded movement.")

        elif current["state"] == "stopped":
            st.warning("Playback stopped.")

        elif current["state"] == "error":
            st.error(
                st.session_state.skill_replay_error
                or "Playback failed."
            )

        else:
            st.info("Playback is ready.")

        progress = current["progress"] / 100.0

        st.progress(
            min(1.0, max(0.0, progress)),
            text=f"Playback progress: {progress * 100:.1f}%"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Current Frame",
            current["current_frame"]
        )

        c2.metric(
            "Total Frames",
            current["total_frames"]
        )

        c3.metric(
            "Playback Speed",
            f"{current['playback_speed']:.2f}x"
        )

        try:
            hardware_status = get_controller().get_status()

            st.caption(
                f"Hardware: "
                f"{'Busy' if hardware_status.get('active') else 'Idle'}"
                f" · Queued commands: "
                f"{hardware_status.get('queued_tasks', 0)}"
            )

        except Exception as error:
            st.warning(str(error))

    playback_status()

    # -----------------------------------------------------
    # UNLOAD SKILL
    # -----------------------------------------------------

    if st.button(
        "Unload Selected Skill",
        use_container_width=True,
        disabled=(
            motion_replayer.is_playing()
            or motion_replayer.is_paused()
        )
    ):

        st.session_state.loaded_motion = None
        st.session_state.loaded_skill_name = None
        st.session_state.selected_skill = None

        motion_replayer.reset()
        reset_replay_state()

        st.success("Skill unloaded.")
        st.rerun()
