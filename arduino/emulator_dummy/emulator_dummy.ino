// Uncomment this to allow LCD (e.g. LCD1602) for visual checking of command status
#define USE_LCD

#define CMD_NONE nullptr
#define CMD_HOME "$H"
#define CMD_HOME_DURATION 2000
#define CMD_STOP "$X"
#define CMD_MOVE "$G"
#define CMD_MOVE_DURATION 2000
// Debug command for injecting errors into running commands
// for testing how UI parses and displays command failures
#define CMD_ERROR "$DE"

#define ANS_OK "OK"
#define ANS_ERR "ERR"
#define ERR_OK 0
#define ERR_UNKNOWN 100 // Unknown error
#define ERR_CMD_UNKNOWN 101 // Unknown command
#define ERR_CMD_RUNNIG 102 // Another command is already running
#define ERR_CMD_FOOLISH 103 // Command is not applicable
#define ERR_POS_LOST 104 // Position lost, homing required
#define ERR_CMD_BAD_PARAM 105 // Invalid command parameter

#define BAUD_RATE 115200

// Currently runnng command
char* cmd = CMD_NONE;
unsigned long cmdStart = 0;
unsigned long cmdDuration = 0;
float cmdParam = 0;

// Stage position
bool homed = false;
float position = 0;

// Include after global vars
#include "lcd.h"

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial);

  showHello();
}

void loop() {
  delay(1);

  if (cmdStart > 0) {
    auto elapsed = millis() - cmdStart;
    if (elapsed >= cmdDuration) {
      endCommand(true);
    }
  }

  if (Serial.available() > 0) {
    String newCmd = Serial.readString();
    newCmd.trim();

    // Send debug error
    if (newCmd == CMD_ERROR) {
      endCommand(false);
      sendError(ERR_UNKNOWN);
      return;
    }
    // STOP command can interrupt other commands
    if (newCmd == CMD_STOP) {
      if (cmd == CMD_NONE) {
        sendError(ERR_CMD_FOOLISH);
      } else {
        endCommand(true);
      }
      return;
    } 
    // Another command is already running
    if (cmd != CMD_NONE) {
      sendError(ERR_CMD_RUNNIG);
      return;
    }
    if (newCmd == CMD_HOME) {
      cmd = CMD_HOME;
      cmdStart = millis();
      cmdDuration = CMD_HOME_DURATION;
    } else if (newCmd.startsWith(CMD_MOVE)) {
      if (!homed) {
      // Current position unknown, can't move
        sendError(ERR_POS_LOST);
        return;
      }
      cmd = CMD_MOVE;
      cmdStart = millis();
      cmdDuration = CMD_MOVE_DURATION;
      cmdParam = newCmd.substring(strlen(CMD_MOVE)+1).toFloat();
    } else {
      sendError(ERR_CMD_UNKNOWN);
      return;
    }
    showCommand();
  }
}

void sendError(int code) {
  Serial.print(ANS_ERR);
  Serial.print(' ');
  Serial.println(code);
}

void endCommand(bool ok) {
  if (ok) {
    Serial.print(ANS_OK);
    if (cmd == CMD_HOME) {
      homed = true;
      position = 0;
      showPosition();
      Serial.print(' ');
      Serial.print(position);
    } else if (cmd == CMD_MOVE) {
      position = cmdParam;
      showPosition();
      Serial.print(' ');
      Serial.print(position);
      Serial.println();
    }
    Serial.println();
  } else {
    if (cmd == CMD_HOME || cmd == CMD_MOVE) {
      // Error during moving, position lost
      homed = false;
      position = 0;
      showPosition();
    }
  }
  cmd = CMD_NONE;
  cmdStart = 0;
  cmdDuration = 0;
  showCommand();
}

