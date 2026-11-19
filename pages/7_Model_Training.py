
import streamlit as st
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# --------------------------------------------------
# PATHS
# --------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "data" / "dataset"
MODELS_DIR = ROOT_DIR / "data" / "models"
SCRIPT_PATH = ROOT_DIR / "scripts" / "train_gesture_model.py"
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "training.log"

GESTURES = [
    "Closed",
    "Grasp",
    "Grasp_down",
    "Open",
    "Pinch",
    "Writing"
]

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Model Training | SkillMimic",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Gesture Model Training")
st.caption("Train and manage your hand gesture recognition model.")

# --------------------------------------------------
# DATASET STATUS
# --------------------------------------------------

st.subheader("Dataset Verification")

if not DATASET_DIR.exists():
    st.error("Dataset folder not found: data/dataset/")
    st.stop()

dataset_status = {}

for gesture in GESTURES:
    folder = DATASET_DIR / gesture

    if folder.exists():
        image_count = sum(
            1 for file in folder.rglob("*")
            if file.is_file() and file.suffix.lower()
            in [".jpg", ".jpeg", ".png", ".bmp"]
        )
        dataset_status[gesture] = image_count
    else:
        dataset_status[gesture] = 0

columns = st.columns(3)

for index, (gesture, count) in enumerate(dataset_status.items()):
    with columns[index % 3]:
        if count > 0:
            st.metric(gesture, f"{count} images")
        else:
            st.metric(gesture, "0 images")
            st.warning(f"{gesture} folder is empty or missing.")

total_images = sum(dataset_status.values())

st.info(f"Total dataset images detected: {total_images}")

# --------------------------------------------------
# EXISTING MODEL STATUS
# --------------------------------------------------

st.divider()
st.subheader("Existing Models")

MODELS_DIR.mkdir(parents=True, exist_ok=True)

model_files = [
    "fast_gesture_model.h5",
    "best_fast_gesture.h5"
]

for model_name in model_files:
    model_path = MODELS_DIR / model_name

    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        st.success(f"{model_name} — Available ({size_mb:.2f} MB)")
    else:
        st.warning(f"{model_name} — Not found")

# --------------------------------------------------
# TRAINING CONTROLS
# --------------------------------------------------

st.divider()
st.subheader("Start Training")

if not SCRIPT_PATH.exists():
    st.error(
        "Training script not found. "
        "Check scripts/train_gesture_model.py"
    )
    st.stop()

if total_images == 0:
    st.warning("Add your gesture images before starting training.")

if "training_process" not in st.session_state:
    st.session_state.training_process = None

if "training_started" not in st.session_state:
    st.session_state.training_started = False

process = st.session_state.training_process

training_running = (
    process is not None and process.poll() is None
)

if training_running:
    st.info("Training is currently running.")
else:
    if st.button(
        "🚀 Start Model Training",
        type="primary",
        disabled=(total_images == 0)
    ):
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        try:
            log_handle = open(LOG_FILE, "w", encoding="utf-8")

            process = subprocess.Popen(
                [sys.executable, str(SCRIPT_PATH)],
                cwd=str(ROOT_DIR),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt" else 0
                )
            )

            st.session_state.training_process = process
            st.session_state.training_started = True
            st.session_state.training_log_handle = log_handle

            st.success("Training process started.")

        except Exception as error:
            st.error(f"Could not start training: {error}")

# --------------------------------------------------
# TRAINING MONITOR
# --------------------------------------------------

@st.fragment(run_every=2)
def training_monitor():

    process = st.session_state.get("training_process")

    if process is None:
        return

    return_code = process.poll()

    if return_code is None:
        st.info("⏳ Training in progress...")

    elif return_code == 0:
        st.success("Training completed successfully!")
        st.session_state.training_process = None

        log_handle = st.session_state.get("training_log_handle")
        if log_handle:
            log_handle.close()
            st.session_state.training_log_handle = None

    else:
        st.error(
            f"Training stopped with exit code {return_code}. "
            "Check the training log below."
        )
        st.session_state.training_process = None

        log_handle = st.session_state.get("training_log_handle")
        if log_handle:
            log_handle.close()
            st.session_state.training_log_handle = None

    if LOG_FILE.exists():
        st.subheader("Training Output")

        log_text = LOG_FILE.read_text(
            encoding="utf-8",
            errors="replace"
        )

        st.code(
            log_text[-10000:] if log_text else "Waiting for output...",
            language="text"
        )

training_monitor()

# --------------------------------------------------
# TRAINING INFORMATION
# --------------------------------------------------

st.divider()

with st.expander("Training Information"):
    st.write("""
    - Dataset: Six gesture categories.
    - Model: MobileNetV2-based classifier.
    - Input image size: 160 × 160.
    - Training script: scripts/train_gesture_model.py.
    - Model output: data/models/.
    
    Training creates model files separately from your existing models.
    """)
