
# SkillMimic - Hardware Documentation

## 1. Hardware Overview

The current physical system uses:

- Arduino Uno
- Pneumatic robotic glove
- Air pump
- Pneumatic valves
- Relay control components
- Air tubes
- USB connection to laptop

The exact electrical and pneumatic specifications must be
confirmed from the existing hardware.

## 2. Hardware Architecture

Laptop
  |
  | USB Serial Connection
  |
Arduino Uno
  |
  | Existing Control Circuit
  |
Relay Components
  |
Pneumatic Valves
  |
Air Supply
  |
Robotic Glove

This is a conceptual representation, not a verified wiring diagram.

## 3. Software Communication

The SkillMimic hardware software contains:

- ArduinoConnection
- DeviceManager
- CommandManager
- SafetyController
- EmergencyStop

The software prepares structured movement targets.

The actual serial command format is not yet configured.

## 4. Required Hardware Information

Before hardware activation, document:

1. Arduino firmware and existing serial protocol.
2. Serial baud rate.
3. Existing COM port.
4. Relay board model and input logic.
5. Valve model and operating characteristics.
6. Pump electrical ratings.
7. Pneumatic pressure limits.
8. Finger-to-valve mapping.
9. Exhaust and pressure-release arrangement.
10. Physical emergency-stop arrangement.

## 5. Safety Requirements

- Never send unverified serial commands.
- Never assume relay activation polarity.
- Never assume valve default positions.
- Verify pressure limits before operation.
- Provide a safe pressure-release arrangement.
- Keep electrical and pneumatic emergency controls independent
  of the application.
- Prevent unexpected movement during startup.
- Require deliberate operator authorization.
- Disconnect safely when communication is lost.

The software emergency stop is not a substitute for a physical
emergency stop or pressure-release mechanism.

## 6. Calibration Requirements

Each finger requires individual calibration.

Calibration should establish:

- Open position.
- Closed position.
- Safe movement range.
- Response time.
- Pressure requirements.
- Finger mapping.
- Repeatability.

Do not use the initial software joint limits as physical calibration data.

## 7. Hardware Integration Status

Current status:

- Arduino connection software: Prepared.
- Structured command preparation: Prepared.
- Serial command encoding: Pending.
- Hardware calibration: Pending.
- Pneumatic safety verification: Pending.
- Live robotic movement: Pending.
