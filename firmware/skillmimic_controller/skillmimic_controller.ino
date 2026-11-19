
#include <Arduino.h>
#include <stdlib.h>
#include <string.h>

// ==================================================
// SKILLMIMIC - SAFE NON-BLOCKING FIRMWARE
// Arduino Uno | 9600 baud
// ==================================================

const byte OPEN_VALVE  = 5;
const byte CLOSE_VALVE = 6;
const byte PUMP        = 7;

const byte FINGER_PINS[5] = {8, 9, 10, 11, 12};

const unsigned long MS_PER_PERCENT = 18;
const unsigned long MAX_MOVE_MS = 2000;

int currentPosition[5] = {100, 100, 100, 100, 100};
int targetPosition[5]  = {0, 0, 0, 0, 0};

bool openingMask[5];
bool closingMask[5];

char inputLine[80];
byte inputLength = 0;

bool moving = false;
byte phase = 0; // 1 = opening, 2 = closing

unsigned long moveStarted = 0;
unsigned long moveDuration = 0;

// Independent actuator safety timer
bool actuatorsEnergised = false;
unsigned long actuatorStarted = 0;

bool emergencyStopped = false;


// ==================================================
// ALL OUTPUTS OFF
// ==================================================

void outputsOff() {
  digitalWrite(PUMP, LOW);
  digitalWrite(OPEN_VALVE, LOW);
  digitalWrite(CLOSE_VALVE, LOW);

  for (byte i = 0; i < 5; i++) {
    digitalWrite(FINGER_PINS[i], LOW);
  }

  actuatorsEnergised = false;
}


// ==================================================
// START ONE MOVEMENT PHASE
// ==================================================

void startPhase(bool opening, bool mask[5],
                unsigned long duration) {

  outputsOff();

  if (emergencyStopped) return;

  for (byte i = 0; i < 5; i++) {
    digitalWrite(FINGER_PINS[i], mask[i] ? HIGH : LOW);
  }

  if (opening) {
    digitalWrite(CLOSE_VALVE, LOW);
    digitalWrite(OPEN_VALVE, HIGH);
  } else {
    digitalWrite(OPEN_VALVE, LOW);
    digitalWrite(CLOSE_VALVE, HIGH);
  }

  digitalWrite(PUMP, HIGH);

  actuatorStarted = millis();
  moveStarted = millis();

  if (duration > MAX_MOVE_MS) {
    duration = MAX_MOVE_MS;
  }

  moveDuration = duration;
  actuatorsEnergised = true;
  moving = true;
}


// ==================================================
// STOP MOVEMENT
// ==================================================

void stopMovement() {
  outputsOff();
  moving = false;
  phase = 0;
}


// ==================================================
// FINISH CURRENT PHASE
// ==================================================

void finishPhase() {
  outputsOff();

  if (phase == 1) {
    for (byte i = 0; i < 5; i++) {
      if (openingMask[i]) {
        currentPosition[i] = targetPosition[i];
      }
    }

    int maxClose = 0;

    for (byte i = 0; i < 5; i++) {
      int difference =
        targetPosition[i] - currentPosition[i];

      closingMask[i] = difference > 0;

      if (difference > maxClose) {
        maxClose = difference;
      }
    }

    if (maxClose > 0) {
      unsigned long duration =
        (unsigned long)maxClose * MS_PER_PERCENT;

      if (duration < 50) duration = 50;

      phase = 2;
      startPhase(false, closingMask, duration);
      Serial.println("MOVING,CLOSE");
      return;
    }
  }

  if (phase == 2) {
    for (byte i = 0; i < 5; i++) {
      if (closingMask[i]) {
        currentPosition[i] = targetPosition[i];
      }
    }
  }

  stopMovement();
  Serial.println("DONE,M");
}


// ==================================================
// MOVEMENT UPDATE - NON BLOCKING
// ==================================================

void updateMovement() {

  // Independent safety cutoff
  if (actuatorsEnergised &&
      millis() - actuatorStarted >= MAX_MOVE_MS) {

    stopMovement();
    Serial.println("ERROR,MOVE_TIMEOUT");
    return;
  }

  if (!moving) return;

  if (millis() - moveStarted >= moveDuration) {
    finishPhase();
  }
}


// ==================================================
// EMERGENCY STOP
// ==================================================

void emergencyStop() {
  stopMovement();
  emergencyStopped = true;
  Serial.println("STOPPED");
}


// ==================================================
// PARSE TARGET COMMAND
// Format: M,0,20,40,60,80
// ==================================================

bool parseTargets(char *command) {
  char *token;
  char *savePointer;

  token = strtok_r(command, ",", &savePointer);

  if (token == NULL || strcmp(token, "M") != 0) {
    return false;
  }

  for (byte i = 0; i < 5; i++) {
    token = strtok_r(NULL, ",", &savePointer);

    if (token == NULL || *token == '\0') return false;

    char *endPointer;
    long value = strtol(token, &endPointer, 10);

    if (*endPointer != '\0' || value < 0 || value > 100) {
      return false;
    }

    targetPosition[i] = (int)value;
  }

  if (strtok_r(NULL, ",", &savePointer) != NULL) {
    return false;
  }

  return true;
}


// ==================================================
// PROCESS MOVEMENT COMMAND
// ==================================================

void processTargets(char *command) {

  if (emergencyStopped) {
    Serial.println("ERROR,ESTOP");
    return;
  }

  if (moving) {
    Serial.println("ERROR,BUSY");
    return;
  }

  if (!parseTargets(command)) {
    Serial.println("ERROR,FORMAT");
    return;
  }

  int maxOpen = 0;
  int maxClose = 0;

  for (byte i = 0; i < 5; i++) {
    openingMask[i] = false;
    closingMask[i] = false;

    int difference =
      targetPosition[i] - currentPosition[i];

    if (difference < 0) {
      openingMask[i] = true;
      if (-difference > maxOpen) maxOpen = -difference;
    }

    if (difference > 0) {
      closingMask[i] = true;
      if (difference > maxClose) maxClose = difference;
    }
  }

  Serial.println("ACK,M");

  if (maxOpen > 0) {
    unsigned long duration =
      (unsigned long)maxOpen * MS_PER_PERCENT;

    if (duration < 50) duration = 50;

    phase = 1;
    startPhase(true, openingMask, duration);
    Serial.println("MOVING,OPEN");
    return;
  }

  if (maxClose > 0) {
    unsigned long duration =
      (unsigned long)maxClose * MS_PER_PERCENT;

    if (duration < 50) duration = 50;

    phase = 2;
    startPhase(false, closingMask, duration);
    Serial.println("MOVING,CLOSE");
    return;
  }

  stopMovement();
  Serial.println("DONE,M");
}


// ==================================================
// STATUS
// ==================================================

void sendStatus() {
  Serial.print("STATUS,");

  for (byte i = 0; i < 5; i++) {
    Serial.print(currentPosition[i]);
    if (i < 4) Serial.print(",");
  }

  Serial.println();
}


// ==================================================
// SERIAL COMMANDS
// ==================================================

void processCommand(char *command) {

  if (strcmp(command, "X") == 0) {
    emergencyStop();
    return;
  }

  if (strcmp(command, "S") == 0) {
    sendStatus();
    return;
  }

  if (strcmp(command, "RESET") == 0) {
    if (moving) {
      Serial.println("ERROR,BUSY");
      return;
    }

    emergencyStopped = false;
    outputsOff();
    Serial.println("RESET_OK");
    return;
  }

  if (strncmp(command, "M,", 2) == 0) {
    processTargets(command);
    return;
  }

  Serial.println("ERROR,UNKNOWN_COMMAND");
}


// ==================================================
// READ SERIAL WITHOUT BLOCKING MOVEMENT
// ==================================================

void readSerial() {
  byte processed = 0;

  while (Serial.available() > 0 && processed < 16) {
    processed++;

    char c = Serial.read();

    if (c == '\n') {
      inputLine[inputLength] = '\0';

      if (inputLength > 0 &&
          inputLine[inputLength - 1] == '\r') {
        inputLine[inputLength - 1] = '\0';
      }

      if (inputLength > 0) {
        processCommand(inputLine);
      }

      inputLength = 0;
    }
    else if (inputLength < sizeof(inputLine) - 1) {
      inputLine[inputLength++] = c;
    }
    else {
      inputLength = 0;
      Serial.println("ERROR,LINE_TOO_LONG");
    }
  }
}


// ==================================================
// SETUP
// ==================================================

void setup() {
  pinMode(OPEN_VALVE, OUTPUT);
  pinMode(CLOSE_VALVE, OUTPUT);
  pinMode(PUMP, OUTPUT);

  for (byte i = 0; i < 5; i++) {
    pinMode(FINGER_PINS[i], OUTPUT);
  }

  outputsOff();

  Serial.begin(9600);
  Serial.println("READY");
}


// ==================================================
// MAIN LOOP
// ==================================================

void loop() {
  readSerial();
  updateMovement();
}
