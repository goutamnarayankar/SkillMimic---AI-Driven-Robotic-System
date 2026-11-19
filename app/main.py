
import streamlit as st
from pathlib import Path

# Project directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Application configuration
st.set_page_config(
    page_title="SkillMimic | Robotics Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load application CSS
css_path = PROJECT_ROOT / "assets" / "css" / "style.css"

if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as file:
        st.markdown(
            f"<style>{file.read()}</style>",
            unsafe_allow_html=True
        )

# Application session
if "app_initialized" not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.active_mode = "Dashboard"
    st.session_state.recording_active = False
    st.session_state.playback_active = False

# Navigation pages
dashboard_page = st.Page(
    str(PROJECT_ROOT / "pages" / "1_Dashboard.py"),
    title="Dashboard",
    icon="🏠",
    default=True
)

record_page = st.Page(
    str(PROJECT_ROOT / "pages" / "2_Record_Motion.py"),
    title="Record Motion",
    icon="🎥"
)

library_page = st.Page(
    str(PROJECT_ROOT / "pages" / "3_Skill_Library.py"),
    title="Skill Library",
    icon="📚"
)

mirror_page = st.Page(
    str(PROJECT_ROOT / "pages" / "4_Live_Mirror.py"),
    title="Live Mirror",
    icon="🖐️"
)

manual_page = st.Page(
    str(PROJECT_ROOT / "pages" / "5_Manual_Control.py"),
    title="Manual Control",
    icon="🎮"
)

settings_page = st.Page(
    str(PROJECT_ROOT / "pages" / "6_Settings.py"),
    title="Settings",
    icon="⚙️"
)

demo_page = st.Page(
    str(PROJECT_ROOT / "pages" / "8_Demo_Actions.py"),
    title="Demo Actions",
    icon="🎮"
)

# NEW: Model Training page
training_page = st.Page(
    str(PROJECT_ROOT / "pages" / "7_Model_Training.py"),
    title="Model Training",
    icon="🧠"
)

# Sidebar navigation
navigation = st.navigation(
    {
        "WORKSPACE": [
            dashboard_page,
            record_page,
            library_page
        ],
        "CONTROL CENTER": [
            mirror_page,
            manual_page
        ],
        "AI & MACHINE LEARNING": [
            training_page
        ],
        "SYSTEM": [
            settings_page
        ]
    }
)

st.session_state["skillmimic_pages"] = {
    "dashboard": dashboard_page,
    "record": record_page,
    "library": library_page,
    "mirror": mirror_page,
    "manual": manual_page,
    "training": training_page,
    "demo": demo_page,
    "settings": settings_page,
}

navigation.run()
