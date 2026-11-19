
import sys
from pathlib import Path

import cv2
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.storage.skill_manager import SkillManager
from core.hardware.controller_access import get_motion_controller


# =========================================================
# DASHBOARD THEME
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(ellipse at 85% 5%, rgba(0, 210, 190, .12), transparent 32%),
            linear-gradient(135deg, #07111f 0%, #0a1728 55%, #071421 100%);
        color: #edf7ff;
    }

    [data-testid="stHeader"] {
        background: rgba(5, 14, 26, .7);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #081321, #0b1c2c);
        border-right: 1px solid rgba(0, 220, 200, .16);
    }

    [data-testid="stSidebar"] * {
        color: #dcecf5;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .brand {
        font-size: 27px;
        font-weight: 900;
        letter-spacing: -.8px;
        color: #f2fbff;
    }

    .brand span {
        color: #20e0cf;
    }

    .brand-sub {
        color: #86a6b8;
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 34px;
        min-height: 230px;
        border: 1px solid rgba(42, 226, 211, .28);
        border-radius: 24px;
        background:
            radial-gradient(circle at 80% 50%, rgba(0, 225, 210, .20), transparent 28%),
            linear-gradient(115deg, #10243a, #0c1b2d 60%, #102c3a);
        box-shadow: 0 15px 45px rgba(0, 0, 0, .24);
    }

    .eyebrow {
        color: #31e0d0;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 3px;
        margin-bottom: 10px;
    }

    .hero h1 {
        color: #f4fbff;
        font-size: clamp(36px, 5vw, 58px);
        font-weight: 900;
        letter-spacing: -2px;
        margin: 0;
    }

    .hero p {
        color: #a9c3d3;
        font-size: 15px;
        max-width: 600px;
        margin-top: 10px;
    }

    .hero-art {
        position: absolute;
        right: 5%;
        top: 10px;
        font-size: 145px;
        opacity: .82;
        filter: drop-shadow(0 0 22px rgba(20, 230, 220, .55));
    }

    .hero-tag {
        display: inline-block;
        margin-top: 14px;
        padding: 7px 13px;
        border-radius: 30px;
        color: #55f2dc;
        border: 1px solid rgba(60, 240, 215, .35);
        background: rgba(20, 210, 190, .09);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
    }

    .section-heading {
        margin: 28px 0 14px;
        color: #eaf8ff;
        font-size: 21px;
        font-weight: 800;
    }

    .metric-card {
        background: linear-gradient(145deg, rgba(20, 43, 64, .96), rgba(11, 28, 44, .96));
        border: 1px solid rgba(108, 174, 200, .19);
        border-radius: 18px;
        padding: 19px;
        min-height: 130px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .16);
    }

    .metric-label {
        color: #91b1c2;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .metric-value {
        color: #eafaff;
        font-size: 27px;
        font-weight: 900;
        margin: 12px 0 3px;
    }

    .metric-note {
        color: #829eaf;
        font-size: 11px;
    }

    .metric-icon {
        float: right;
        font-size: 25px;
    }

    .workspace-card {
        border: 1px solid rgba(88, 188, 202, .22);
        border-radius: 20px;
        padding: 22px;
        min-height: 180px;
        background:
            radial-gradient(circle at 100% 0%, rgba(21, 215, 202, .10), transparent 40%),
            linear-gradient(145deg, #142a40, #0d1c2d);
        box-shadow: 0 12px 30px rgba(0, 0, 0, .18);
        margin-bottom: 5px;
    }

    .workspace-icon {
        font-size: 30px;
        margin-bottom: 8px;
    }

    .workspace-card h3 {
        color: #f1fbff;
        font-size: 20px;
        margin: 0 0 8px;
    }

    .workspace-card p {
        color: #9eb8c8;
        font-size: 13px;
        min-height: 40px;
        margin-bottom: 0;
    }

    .recent-card {
        background: rgba(15, 34, 52, .88);
        border: 1px solid rgba(108, 174, 200, .17);
        border-radius: 17px;
        padding: 17px;
    }

    .status-dot {
        display: inline-block;
        height: 8px;
        width: 8px;
        border-radius: 50%;
        margin-right: 7px;
    }

    .status-good {
        background: #20dfaa;
        box-shadow: 0 0 10px #20dfaa;
    }

    .status-bad {
        background: #ff657b;
        box-shadow: 0 0 10px #ff657b;
    }

    .status-warn {
        background: #ffbd59;
        box-shadow: 0 0 10px #ffbd59;
    }

    .stButton > button {
        border-radius: 11px;
        border: 1px solid rgba(45, 224, 210, .35);
        background: linear-gradient(100deg, #0d827f, #116b80);
        color: white;
        font-weight: 750;
        min-height: 42px;
        transition: .2s ease;
    }

    .stButton > button:hover {
        border-color: #54f5df;
        background: linear-gradient(100deg, #119c92, #1385a0);
        color: white;
        transform: translateY(-1px);
    }

    .footer {
        text-align: center;
        color: #68879b;
        font-size: 11px;
        padding: 25px 0 5px;
        letter-spacing: 1px;
    }

    @media (max-width: 800px) {
        .hero-art {
            opacity: .18;
            right: 2%;
        }
        .hero {
            padding: 24px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "recording_active" not in st.session_state:
    st.session_state.recording_active = False

if "playback_active" not in st.session_state:
    st.session_state.playback_active = False


# =========================================================
# SYSTEM STATUS
# =========================================================

skills = []
skill_error = None

try:
    manager = SkillManager()
    skills = manager.list_skills() or []
except Exception as error:
    skill_error = str(error)


# Camera probe: opens briefly and releases immediately.
camera_connected = False

try:
    camera_probe = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if camera_probe.isOpened():
        camera_connected = True

    camera_probe.release()

except Exception:
    camera_connected = False


arduino_connected = False
arduino_port = "Unavailable"
controller_error = None
controller_status = {}

try:
    controller = get_motion_controller()
    controller_status = controller.get_status()

    arduino_connected = bool(
        controller_status.get("connected", False)
    )

    arduino_port = (
        controller_status.get("port")
        or "Connected"
        if arduino_connected
        else "Unavailable"
    )

except Exception as error:
    controller_error = str(error)


if controller_status.get("emergency_stopped"):
    session_status = "Emergency Stop"
    session_color = "#ff657b"

elif controller_status.get("active"):
    session_status = "Running"
    session_color = "#20dfaa"

elif st.session_state.recording_active:
    session_status = "Recording"
    session_color = "#ffbd59"

elif st.session_state.playback_active:
    session_status = "Playback"
    session_color = "#ffbd59"

else:
    session_status = "Idle"
    session_color = "#20dfaa"


# =========================================================
# SIDEBAR BRAND
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding:12px 5px 24px;">
            <div style="font-size:43px;">🦾</div>
            <div class="brand">Skill<span>Mimic</span></div>
            <div class="brand-sub">Robotics Movement Studio</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("### System Status")

    st.markdown(
        f"""
        <div style="padding:8px 0;">
            <span class="status-dot {'status-good' if camera_connected else 'status-bad'}"></span>
            <b>Camera</b><br>
            <span style="color:#91aebe;font-size:12px;">
                {'Connected' if camera_connected else 'Not Connected'}
            </span>
        </div>
        <div style="padding:8px 0;">
            <span class="status-dot {'status-good' if arduino_connected else 'status-bad'}"></span>
            <b>Arduino</b><br>
            <span style="color:#91aebe;font-size:12px;">
                {'Connected · ' + str(arduino_port) if arduino_connected else 'Disconnected'}
            </span>
        </div>
        <div style="padding:8px 0;">
            <span class="status-dot {'status-good' if session_status == 'Idle' else 'status-warn'}"></span>
            <b>Session</b><br>
            <span style="color:{session_color};font-size:12px;">
                {session_status}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.caption("SKILLMIMIC · LOCAL WORKSPACE")
    st.caption("Camera and controller status are checked when this page loads.")


# =========================================================
# HERO HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">ROBOTICS WORKSPACE</div>
        <h1>Dashboard</h1>
        <p>
            Record, understand and reproduce human hand movements.
            Your intelligent movement workspace starts here.
        </p>
        <div class="hero-tag">● SKILLMIMIC SYSTEM INTERFACE</div>
        <div class="hero-art">🦾</div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# METRIC CARDS
# =========================================================

st.markdown(
    '<div class="section-heading">✦ Workspace Overview</div>',
    unsafe_allow_html=True
)

metric_columns = st.columns(4)

metric_data = [
    (
        "📚",
        "Saved Skills",
        str(len(skills)),
        "Stored movement recordings"
    ),
    (
        "📷",
        "Camera",
        "Connected" if camera_connected else "Not Connected",
        "Hand tracking input"
    ),
    (
        "🔌",
        "Arduino",
        "Connected" if arduino_connected else "Disconnected",
        f"Controller: {arduino_port}"
    ),
    (
        "〰️",
        "Session",
        session_status,
        "Current system state"
    )
]

for column, item in zip(metric_columns, metric_data):

    icon, label, value, note = item

    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <span class="metric-icon">{icon}</span>
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# WORKSPACE NAVIGATION
# =========================================================

st.markdown(
    '<div class="section-heading">✦ Your Workspace</div>',
    unsafe_allow_html=True
)

workspace = [
    {
        "title": "Motion Recording",
        "icon": "🎥",
        "description": (
            "Capture natural hand movements and create "
            "reusable movement sequences."
        ),
        "page": "record",
        "button": "Open Motion Recording"
    },
    {
        "title": "Skill Library",
        "icon": "📚",
        "description": (
            "Explore, organize and manage your previously "
            "recorded movement sequences."
        ),
        "page": "library",
        "button": "Open Skill Library"
    },
    {
        "title": "Live Mirror",
        "icon": "🖐️",
        "description": (
            "Track hand movements in real time and submit "
            "finger targets to the robotic controller."
        ),
        "page": "mirror",
        "button": "Open Live Mirror"
    },
    {
        "title": "Manual Control",
        "icon": "🎮",
        "description": (
            "Control and test individual pneumatic glove "
            "fingers for calibration."
        ),
        "page": "manual",
        "button": "Open Manual Control"
    }
]


def navigate_to_page(page_key):
    pages = st.session_state.get("skillmimic_pages", {})

    target_page = pages.get(page_key)

    if target_page is None:
        st.error(
            f"Navigation page '{page_key}' is not registered in app.py."
        )
        return

    st.switch_page(target_page)


for row_start in (0, 2):

    columns = st.columns(2)

    for column, item in zip(
        columns,
        workspace[row_start:row_start + 2]
    ):

        with column:

            st.markdown(
                f"""
                <div class="workspace-card">
                    <div class="workspace-icon">{item['icon']}</div>
                    <h3>{item['title']}</h3>
                    <p>{item['description']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(
                item["button"] + "  →",
                key=f"open_{item['page']}",
                use_container_width=True
            ):
                navigate_to_page(item["page"])


# =========================================================
# RECENT SKILLS
# =========================================================

st.markdown(
    '<div class="section-heading">✦ Recent Movement Recordings</div>',
    unsafe_allow_html=True
)

if skill_error:

    st.warning(f"Skill Library could not be loaded: {skill_error}")

elif not skills:

    st.info(
        "No saved movements yet. Open Motion Recording to create your first skill."
    )

else:

    sorted_skills = sorted(
        skills,
        key=lambda item: item.get("created_at") or "",
        reverse=True
    )

    for skill in sorted_skills[:5]:

        skill_name = skill.get("name", "Unnamed Skill")
        duration = float(skill.get("duration", 0))
        frames = int(skill.get("total_frames", 0))
        created = skill.get("created_at", "Unknown date")

        with st.container(border=True):

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**🖐️ {skill_name}**")
                st.caption(f"Created: {created}")

            with col2:
                st.metric("Duration", f"{duration:.1f}s")

            with col3:
                st.metric("Frames", frames)


# =========================================================
# SYSTEM DIAGNOSTICS
# =========================================================

st.markdown(
    '<div class="section-heading">✦ System Diagnostics</div>',
    unsafe_allow_html=True
)

diag1, diag2 = st.columns(2)

with diag1:

    with st.container(border=True):

        st.markdown("#### 📷 Camera Input")

        if camera_connected:
            st.success("Camera device is available.")
        else:
            st.error(
                "Camera is not available. Check the webcam and camera index."
            )

with diag2:

    with st.container(border=True):

        st.markdown("#### 🔌 Motion Controller")

        if controller_error:
            st.error(f"Controller error: {controller_error}")

        elif arduino_connected:
            st.success(
                f"Arduino connected on {arduino_port}."
            )
        else:
            st.error(
                "Arduino is disconnected from MotionController."
            )

        if controller_status.get("emergency_stopped"):
            st.warning("Emergency stop is active.")

        if controller_status.get("last_error"):
            st.caption(
                f"Last controller error: {controller_status['last_error']}"
            )


# =========================================================
# QUICK PROJECT REMINDER
# =========================================================

st.markdown(
    """
    <div class="recent-card">
        <div class="eyebrow">PROJECT WORKFLOW</div>
        <h3 style="color:#eaf8ff;">Capture → Process → Store → Reproduce</h3>
        <p style="color:#9eb8c8;">
            Record hand landmarks, process finger movement targets,
            save reusable skills, and reproduce them through the
            pneumatic glove controller.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        SKILLMIMIC · ROBOTICS MOVEMENT STUDIO · LOCAL DEVELOPMENT
    </div>
    """,
    unsafe_allow_html=True
)
