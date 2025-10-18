// Uncomment this to allow LCD (e.g. LCD1602) for visual checking of command status
#define USE_LCD

#include "protocol.h"

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
float scanStep = 0;
bool scanBack = false;

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
      endCommand(false);
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
        endCommand(true);
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
    else if (newCmd == CMD_SCAN)
    {
      if (!checkHome()) return;
      startScan(false);
    }
    else if (newCmd == CMD_SCANS)
    {
      if (!checkHome()) return;
      startScan(true);
    }
    else
    {
      sendError(ERR_CMD_UNKNOWN);
      return;
    }
    showCommand();
    showPosition();
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

void endCommand(bool stopped)
{
  if (cmd == CMD_HOME)
  {
    homed = true;
    position = 0;
    Serial.print(ANS_OK);
    Serial.print(' ');
    Serial.println(position);
  }
  else if (cmd == CMD_MOVE)
  {
    position = cmdArg.targetPosition;
    Serial.print(ANS_OK);
    Serial.print(' ');
    Serial.println(position);
  }
  else if (cmd == CMD_JOG)
  {
    position += cmdArg.jogDistance;
    if (homed)
    {
      Serial.print(ANS_OK);
      Serial.print(' ');
      Serial.println(position);
    }
    else
      Serial.println(ANS_OK);
  }
  else if (cmd == CMD_SCAN || cmd == CMD_SCANS)
  {
    if (stopped)
    {
      Serial.println(ANS_OK);
    }
    else
    {
      position += scanStep;
      if (sendScanPoint())
        return;
    }
  }
  cmd = CMD_NONE;
  cmdStart = 0;
  cmdDuration = 0;
  showCommand();
  showPosition();
}

void startScan(bool inf)
{
  cmd = inf ? CMD_SCANS : CMD_SCAN;
  cmdDuration = SCAN_POINT_DURATION;
  cmdArg.profileCenter = position + SCAN_HALF_RANGE;
  pointsSent = 0;
  scanStep = SCAN_POINT_DISTANCE;
  scanBack = false;
  // Start scanning from the current position
  sendScanPoint();
}

bool sendScanPoint()
{
  float x = cmdArg.profileCenter - position;
  float level = SCAN_PROFILE_AMPLITUDE * exp(-sq(x) / (2.0 * sq(SCAN_PROFILE_WIDTH)));
  float noise = random(-1000, 1000) / 1000.0 * SCAN_PROFILE_AMPLITUDE * SCAN_PROFILE_NOISE;
  Serial.print(ANS_OK);
  Serial.print(' ');
  Serial.print(position);
  Serial.print(' ');
  Serial.println(max(0, level + noise));
  pointsSent++;
  if (scanStep == 0)
    scanStep = scanBack ? -SCAN_POINT_DISTANCE : SCAN_POINT_DISTANCE;
  if (pointsSent == SCAN_POINT_COUNT)
  {
    // Send addition OK to show the scan is finished
    Serial.println(ANS_OK);
    if (cmd == CMD_SCAN)
    {
      // Finish the command
      return false;
    }
    else
    {
      pointsSent = 0;
      scanBack = !scanBack;
      // When reversing the scan direction,
      // the next point should be measured at the same position
      // in order to have the same point number for both directions
      scanStep = 0;
    }
  }
  if (SCAN_POINT_DURATION >= 250 || pointsSent % 10 == 0)
  {
    showCommand();
    showPosition();
  }
  cmdStart = millis();    
  return true;
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
