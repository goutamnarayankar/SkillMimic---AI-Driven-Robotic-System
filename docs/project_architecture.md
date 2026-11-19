
# SkillMimic - Project Architecture

## 1. Project Overview

SkillMimic is an AI-driven markerless hand movement recording and robotic
guidance system.

The application captures natural human hand movements using a webcam,
processes hand landmarks using MediaPipe, records continuous movement
sequences and prepares them for robotic glove reproduction.

## 2. System Objectives

- Capture continuous human hand movements.
- Track 21 hand landmarks using MediaPipe.
- Process and smooth landmark coordinates.
- Calculate finger joint angles.
- Record and save reusable movement sequences.
- Replay previously recorded movements.
- Support live hand movement monitoring.
- Provide manual movement target controls.
- Integrate with an Arduino-controlled pneumatic glove.
- Provide safety controls for hardware integration.

## 3. System Architecture

### Input Layer

Components:
- Laptop webcam
- Camera Manager
- MediaPipe Hand Tracker

Responsibilities:
- Capture live video.
- Detect hands.
- Extract 21 landmarks.
- Identify left and right hands.

### Tracking and Processing Layer

Components:
- Landmark Processor
- Motion Processor
- Joint Angle Calculator
- Inverse Kinematics

Responsibilities:
- Smooth landmark coordinates.
- Calculate finger measurements.
- Process movement sequences.
- Generate normalized joint targets.

### Motion Management Layer

Components:
- Motion Recorder
- Motion Replayer
- Skill Manager

Responsibilities:
- Record timestamped movements.
- Process recorded sequences.
- Replay movement data.
- Save and load skills.

### Hardware Layer

Components:
- Arduino Connection
- Command Manager
- Device Manager

Responsibilities:
- Manage serial connections.
- Prepare hardware commands.
- Monitor device availability.

Hardware actuation remains disabled until the existing Arduino
protocol and pneumatic glove calibration are verified.

### Safety Layer

Components:
- Safety Controller
- Emergency Stop

Responsibilities:
- Software arming and disarming.
- Emergency-stop state management.
- Command validation.
- Software watchdog monitoring.

A separate physical safety arrangement is required for pneumatic operation.

### User Interface Layer

Technology:
- Python
- Streamlit
- OpenCV
- CSS

Pages:
- Dashboard
- Motion Recording
- Skill Library
- Live Mirror
- Manual Control
- Settings

## 4. Movement Recording Workflow

Webcam
  -> Hand Detection
  -> Landmark Extraction
  -> Landmark Processing
  -> Motion Recording
  -> Motion Processing
  -> Skill Storage

## 5. Movement Reproduction Workflow

Saved Skill
  -> Motion Loading
  -> Motion Playback
  -> Joint Angle Calculation
  -> Inverse Kinematics
  -> Hardware Command Preparation
  -> Verified Hardware Interface

## 6. Storage Architecture

data/
  recordings/
  processed/
  models/
  exports/

Recordings contain timestamped movement sequences.
Processed contains processed movement data.
Models contains optional model files.
Exports contains exported movement data.

## 7. Development Technology

- Python 3.11
- Streamlit
- OpenCV
- MediaPipe
- NumPy
- PySerial
- JSON

## 8. Future Development

- Continuous robotic movement reproduction.
- Pneumatic glove calibration.
- Real-time hand-to-glove synchronization.
- Hardware feedback integration.
- Secure cloud-to-local communication.
- Improved movement smoothing.
- Movement comparison and accuracy analysis.
