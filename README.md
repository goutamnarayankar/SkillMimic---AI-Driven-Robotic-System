# SkillMimic – AI-Driven Hand Movement Recording and Robotic Guidance System

**An AI-powered system for markerless hand-motion tracking, skill recording, and robotic glove movement replication.**

## Overview

SkillMimic is an AI-driven hand movement recording and robotic guidance system designed to capture human hand movements through a standard camera and translate them into structured movement data for robotic glove control.

The system uses computer vision and hand landmark detection to track hand movements without requiring wearable sensors. It processes the detected landmarks, calculates individual finger movement targets, records motion sequences, and provides tools to manage and replay recorded skills.

The project combines computer vision, motion processing, inverse kinematics foundations, serial communication, and embedded hardware control in an integrated application.

## Key Features

- **Markerless Hand Tracking:** Real-time hand tracking using MediaPipe and OpenCV.
- **21 Hand Landmarks:** Detection and processing of 21 hand landmarks.
- **Finger Movement Estimation:** Calculates individual movement targets for the thumb, index, middle, ring, and little fingers.
- **Landmark Processing:** Applies smoothing and deadband logic to reduce unwanted movement fluctuations.
- **Motion Recording:** Captures and stores continuous hand movement sequences.
- **Skill Library:** Saves, organizes, and manages recorded movement sequences.
- **Motion Playback:** Replays recorded movement data through a movement controller.
- **Live Mirror:** Provides a real-time hand-tracking and movement-target interface.
- **Manual Control:** Allows individual finger movement targets to be controlled manually.
- **Calibration:** Supports per-finger open and closed calibration.
- **Arduino Integration:** Provides serial communication with an Arduino-based robotic glove controller.
- **Safety Controls:** Includes software-level emergency-stop and hardware control mechanisms.

## System Architecture

The application is organized into modular components:

1. **Camera Input:** Captures live video using a webcam.
2. **Hand Tracking:** Detects the hand and extracts 21 landmarks using MediaPipe.
3. **Landmark Processing:** Processes landmark coordinates and estimates individual finger movement.
4. **Motion Processing:** Prepares movement data for recording and playback.
5. **Kinematics:** Provides joint-angle calculations and inverse-kinematics foundations.
6. **Motion Recording and Storage:** Saves recorded skills for later use.
7. **Motion Playback:** Sends recorded movement targets to the controller in sequence.
8. **Hardware Communication:** Communicates with the Arduino through serial commands.
9. **Robotic Glove:** Executes the received movement commands through the connected actuators.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python 3.11 |
| User Interface | Streamlit |
| Computer Vision | OpenCV |
| Hand Tracking | MediaPipe |
| Numerical Processing | NumPy |
| Hardware Communication | PySerial |
| Embedded Platform | Arduino Uno |
| Data Storage | JSON |
| Machine Learning Support | TensorFlow |

## Project Structure

```text
SkillMimic/
│
├── app/
│   └── main.py
│
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Record_Motion.py
│   ├── 3_Skill_Library.py
│   ├── 4_Live_Mirror.py
│   ├── 5_Manual_Control.py
│   ├── 6_Settings.py
│   ├── 7_Model_Training.py
│   └── 8_Demo_Actions.py
│
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
│   ├── hardware_config.json
│   └── settings.py
│
├── firmware/
│   └── skillmimic_controller/
│       └── skillmimic_controller.ino
│
├── assets/
│   ├── css/
│   ├── images/
│   └── icons/
│
├── scripts/
├── tests/
├── docs/
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation and Setup

### Prerequisites

- Windows 10/11
- Python 3.11
- Git
- Webcam
- Arduino IDE (for firmware upload)
- Arduino Uno and compatible robotic glove hardware

### 1. Clone the Repository

```bash
git clone https://github.com/goutamnarayankar/SkillMimic---AI-Driven-Robotic-System.git
```

### 2. Navigate to the Project Directory

```bash
cd SkillMimic---AI-Driven-Robotic-System
```

### 3. Create a Virtual Environment

```bash
py -3.11 -m venv venv
```

### 4. Activate the Virtual Environment

```bash
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
python -m pip install --upgrade pip
```

```bash
python -m pip install -r requirements.txt
```

## Running the Application

Start the Streamlit application from the project root:

```bash
python -m streamlit run app/main.py
```

Open the local URL displayed in the terminal, usually:

```text
http://localhost:8501
```

## Application Modules

| Module | Description |
|---|---|
| Dashboard | Main application overview and system status |
| Record Motion | Captures and saves hand movement sequences |
| Skill Library | Manages previously recorded skills |
| Live Mirror | Tracks hand movements and displays movement targets |
| Manual Control | Provides manual finger movement control |
| Settings | Configures application and hardware settings |
| Model Training | Provides model-training functionality |
| Demo Actions | Provides demonstration movement actions |

## Robotic Hardware Configuration

The hardware integration is designed around an Arduino Uno and a pneumatic robotic glove.

### Hardware Pin Mapping

| Component | Arduino Pin |
|---|---|
| Vacuum Valve | D5 |
| Blow / Close Valve | D6 |
| Pump / Motor | D7 |
| Thumb Relay | D8 |
| Index Finger Relay | D9 |
| Middle Finger Relay | D10 |
| Ring Finger Relay | D11 |
| Little Finger Relay | D12 |

**Serial Configuration**

- Board: Arduino Uno
- Baud rate: 9600
- Default configured serial port: COM8 (can be changed in Settings)

The actual pin behaviour, relay polarity, pneumatic timing, and movement limits must be verified against the connected hardware and firmware before operation.

## Movement Control

The system uses five individual finger movement targets:

```text
[THUMB, INDEX, MIDDLE, RING, LITTLE]
```

Movement values are represented on a 0–100 scale:

- `0` – Open position
- `100` – Closed position
- Values between 0 and 100 – Intermediate movement targets

The controller uses structured movement commands in the following format:

```text
M,THUMB,INDEX,MIDDLE,RING,LITTLE
```

For example:

```text
M,0,25,50,75,100
```

This represents an open thumb, partially closed index and middle fingers, a more closed ring finger, and a fully closed little-finger target.

The all-zero command requests an open target for all five fingers:

```text
M,0,0,0,0,0
```

The software uses command acknowledgements and completion responses to coordinate movement execution. The reported positions are estimates; the system does not have physical finger-position sensors to independently verify actual finger angles.

## Motion Queue and Playback Behaviour

- Recorded skill playback is processed sequentially.
- Playback commands are submitted in FIFO order.
- The next recorded movement waits for the previous movement operation to complete.
- Manual movement commands are queued in order.
- Live Mirror uses latest-target-wins behaviour to avoid building up stale webcam movement targets.
- The robotic glove holds its last commanded position after a movement task.
- An explicit all-zero movement command requests the open position.

## Safety Considerations

This project combines software control with pneumatic and electrical hardware. Safe operation is essential.

- Test software and serial communication before connecting pneumatic power.
- Keep hands clear of moving mechanical components during initial testing.
- Verify relay wiring and actuator direction before enabling movement.
- Use a suitable regulated pneumatic supply.
- Check movement limits and actuator timing.
- Keep the emergency-stop mechanism accessible.
- Do not assume estimated positions represent measured physical positions.

**Important:** The software emergency stop does not replace a physical emergency-stop circuit or appropriate pneumatic isolation.

## Testing

The project includes tests for camera, tracking, motion processing, and controller behaviour.

Run the test suite from the project root:

```bash
python -m unittest discover -s tests -v
```

Hardware tests should be conducted separately with the pneumatic supply isolated until the electrical connections, firmware, and movement limits have been verified.

## Current Development Scope

The project brings together markerless hand tracking, movement recording, skill management, movement playback, calibration, and Arduino communication.

Further development and validation can focus on:

- Improving movement replication accuracy.
- Improving real-time tracking stability.
- Integrating physical position feedback.
- Improving pneumatic actuator calibration.
- Evaluating movement consistency and repeatability.
- Expanding skill recording and playback capabilities.

## Future Enhancements

- Sensor-based finger-position feedback.
- More accurate robotic movement replication.
- Advanced motion filtering and tracking.
- Movement accuracy evaluation.
- Expanded skill recognition.
- Improved robotic guidance and haptic feedback.
- Additional hardware and actuator support.

## Contributors

Developed as an academic major project by the project team from the Department of Artificial Intelligence and Machine Learning.

## License

No open-source license has been specified yet. All rights are reserved by the respective project contributors unless a license is added to this repository.
