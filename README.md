
# SkillMimic - AI-Driven Hand Movement Recording and Robotic Guidance

## Overview

SkillMimic is a markerless hand movement recording and robotic
guidance application.

It uses computer vision to capture human hand movements, extract
hand landmarks, record continuous movement sequences and prepare
movement data for robotic glove integration.

## Main Features

- Real-time hand tracking using MediaPipe.
- 21 hand landmark extraction.
- Hand landmark smoothing.
- Continuous movement recording.
- Persistent movement storage.
- Saved skill library.
- Movement playback engine.
- Joint angle calculation.
- Inverse kinematics foundation.
- Live mirror interface.
- Manual movement target controls.
- Arduino communication architecture.
- Software safety controller.
- Emergency-stop interface.

## Technology Stack

- Python 3.11
- Streamlit
- OpenCV
- MediaPipe
- NumPy
- PySerial
- JSON

## Project Structure

```text
SkillMimic/
│
├── app/
├── pages/
├── core/
│   ├── camera/
│   ├── tracking/
│   ├── motion/
│   ├── kinematics/
│   ├── hardware/
│   ├── storage/
│   └── safety/
│
├── config/
├── data/
│   ├── recordings/
│   ├── processed/
│   ├── models/
│   └── exports/
│
├── assets/
│   ├── css/
│   ├── images/
│   └── icons/
│
├── scripts/
├── tests/
├── docs/
├── logs/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation

Open CMD in the project directory.

Create the virtual environment:

```cmd
py -3.11 -m venv venv
```

Activate it:

```cmd
venv\Scripts\activate.bat
```

Install dependencies:

```cmd
python -m pip install -r requirements.txt
```

## Run the Application

From the project root:

```cmd
venv\Scripts\activate.bat
```

Then:

```cmd
python -m streamlit run app\main.py
```

Alternatively, launch:

```cmd
scripts\run_local.bat
```

## Main Application Pages

1. Dashboard
2. Record Motion
3. Skill Library
4. Live Mirror
5. Manual Control
6. Settings

## Data Storage

Movement recordings are stored locally in:

```text
data/recordings/
```

Processed movement data is stored in:

```text
data/processed/
```

Exports are stored in:

```text
data/exports/
```

## Hardware Integration

The intended hardware platform includes an Arduino Uno and a
pneumatic robotic glove.

The software contains a hardware communication layer and
structured movement command preparation.

Actual hardware activation requires verification of:

- Existing Arduino firmware and serial protocol.
- Finger and valve mapping.
- Pneumatic calibration.
- Pressure and electrical safety.
- Physical emergency-stop arrangements.

Hardware commands remain disabled until these requirements
are verified.

## Development Status

The initial application structure and core software modules
have been authored.

Integration, runtime validation, calibration and hardware
testing remain necessary.

## Future Enhancements

- Accurate continuous movement reproduction.
- Live robotic glove synchronization.
- Hardware feedback integration.
- Movement accuracy analysis.
- Secure local hardware agent for cloud access.
- Improved movement visualization.
- Cloud deployment.

## License

Project license to be determined.
```
