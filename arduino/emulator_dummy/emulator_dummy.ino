// Uncomment this to allow LCD (e.g. LCD1602) for visual checking of command status
#define USE_LCD

#define CMD_NONE nullptr
#define CMD_HOME "$H"
#define CMD_HOME_DURATION 2000
#define CMD_STOP "$X"
#define CMD_MOVE "$G"
#define CMD_MOVE_DURATION 2000
#define CMD_JOG "$J"
#define CMD_JOG_DURATION 1000
#define CMD_SCAN "$MS"
#define CMD_SCANS "$MC"
#define CMD_ERROR "$DE"

#define SCAN_POINT_HALF_COUNT 100
#define SCAN_POINT_COUNT (2*SCAN_POINT_HALF_COUNT + 1)
#define SCAN_POINT_DISTANCE 0.1
#define SCAN_POINT_DURATION 10
#define SCAN_HALF_RANGE (SCAN_POINT_DISTANCE * SCAN_POINT_HALF_COUNT)
#define SCAN_PROFILE_AMPLITUDE 1000
#define SCAN_PROFILE_NOISE 0.05
#define SCAN_PROFILE_WIDTH = (SCAN_HALF_RANGE / 5.0)

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
union {
float targetPosition = 0;
float jogDistance;
float profileCenter;
} cmdArg;
int pointsSent = 0;

// Stage position
bool homed = false;
float position = 0;

// Include after global vars
#include "lcd.h"

void setup()
{
  Serial.begin(BAUD_RATE);
  while (!Serial);

  randomSeed(analogRead(A0));

  showHello();
}

void loop()
{
  delay(1);

  if (cmdStart > 0)
  {
    auto elapsed = millis() - cmdStart;
    if (elapsed >= cmdDuration)
      endCommand();
  }

  if (Serial.available() > 0)
  {
    String newCmd = Serial.readString();
    newCmd.trim();

    // Send debug error
    if (newCmd == CMD_ERROR)
    {
      simulateError();
      return;
    }

    // STOP command can interrupt other commands
    if (newCmd == CMD_STOP)
    {
      if (cmd == CMD_NONE)
        sendError(ERR_CMD_FOOLISH);
      else
        endCommand();
      return;
    } 

    // Another command is already running
    if (cmd != CMD_NONE)
    {
      sendError(ERR_CMD_RUNNIG);
      return;
    }
    
    if (newCmd == CMD_HOME)
    {
      cmd = CMD_HOME;
      cmdStart = millis();
      cmdDuration = CMD_HOME_DURATION;
    }
    else if (newCmd.startsWith(CMD_MOVE))
    {
      if (!checkHome()) return;
      cmd = CMD_MOVE;
      cmdStart = millis();
      cmdDuration = CMD_MOVE_DURATION;
      cmdArg.targetPosition = newCmd.substring(strlen(CMD_MOVE)+1).toFloat();
    }
    else if (newCmd.startsWith(CMD_JOG))
    {
      cmd = CMD_JOG;
      cmdStart = millis();
      cmdDuration = CMD_JOG_DURATION;
      cmdArg.jogDistance = newCmd.substring(strlen(CMD_JOG)+1).toFloat();
    }
    else if (newCmd = CMD_SCAN)
    {
      if (!checkHome()) return;
      cmd = CMD_SCAN;
      cmdStart = millis();
      cmdDuration = SCAN_POINT_DURATION;
      // The middle of the profile
      cmdArg.profileCenter = position + SCAN_HALF_RANGE;
      pointsSent = 0;
    }
    else
    {
      sendError(ERR_CMD_UNKNOWN);
      return;
    }
    showCommand();
  }
}

void sendError(int code)
{
  Serial.print(ANS_ERR);
  Serial.print(' ');
  Serial.println(code);
}

bool checkHome()
{
  if (homed)
    return true;
  // Current position unknown, can't move
  sendError(ERR_POS_LOST);
  return false;
}

void endCommand()
{
  Serial.print(ANS_OK);
  if (cmd == CMD_HOME)
  {
    homed = true;
    position = 0;
    showPosition();
    Serial.print(' ');
    Serial.println(position);
  }
  else if (cmd == CMD_MOVE)
  {
    position = cmdArg.targetPosition;
    showPosition();
    Serial.print(' ');
    Serial.println(position);
  }
  else if (cmd == CMD_JOG)
  {
    position += cmdArg.jogDistance;
    showPosition();
    if (homed)
    {
      Serial.print(' ');
      Serial.println(position);
    }
  }
  else if (cmd == CMD_SCAN)
  {
    float x = cmdArg.profileCenter - position;
    float level = SCAN_PROFILE_AMPLITUDE * exp(-sq(x) / (2.0 * sq(SCAN_PROFILE_WIDTH)));
    float noise = random(-1000, 1000) / 1000.0 * SCAN_PROFILE_AMPLITUDE * SCAN_PROFILE_NOISE;
    Serial.print(' ');
    Serial.print(position);
    Serial.print(' ');
    Serial.println(max(0, level + noise));
    pointsSent++;
    if (pointsSent == SCAN_POINT_COUNT)
    {
      // Send addition OK to show the scan is finished
      Serial.println(ANS_OK);
    }
    else
    {
      position += SCAN_POINT_DISTANCE;
      cmdStart = millis();    
      if (pointsSent % 10 == 0)
      {
        showCommand();
        showPosition();
      }
      return;
    }
  }
  cmd = CMD_NONE;
  cmdStart = 0;
  cmdDuration = 0;
  showCommand();
}

void simulateError()
{
  if (cmd == CMD_HOME || cmd == CMD_MOVE || CMD_JOG || CMD_SCAN || CMD_SCANS)
  {
    // Error during moving, position lost
    homed = false;
    position = 0;
    showPosition();
  }
  cmd = CMD_NONE;
  cmdStart = 0;
  cmdDuration = 0;
  showCommand();
  sendError(ERR_UNKNOWN);
}
