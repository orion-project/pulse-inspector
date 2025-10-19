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
union {
  int sent = 0;
} points;
float scanStep = 0;
bool scanBack = false;
struct {
  int sent = -1;
  int index = -1;
  bool set = false;
  float value = 0;
} cmdParamArgs;

// Stage position
bool homed = false;
float position = 0;

// "Persistent" memory
struct Param
{
  char* name;
  float value;
};
Param params[PARAM_COUNT] = {
  { .name = "p1", .value = 16 },
  { .name = "p2", .value = 50 },
  { .name = "p3", .value = 0.5 },
};

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
    else if (newCmd == CMD_PARAM)
    {
      cmd = CMD_PARAM;
      cmdStart = millis();
      cmdDuration = CMD_PARAM_DURATION;
      cmdParamArgs.sent = 0;
      cmdParamArgs.index = -1;
    }
    else if (newCmd.startsWith(CMD_PARAM))
    {
      auto split1 = newCmd.indexOf(' ');
      auto split2 = newCmd.lastIndexOf(' ');
      if (split1 < 0 || split2 < 0) {
        sendError(ERR_CMD_BAD_ARG);
        return;
      }
      String paramName;
      if (split1 == split2) { // e.g. `$P p1`
        paramName = newCmd.substring(strlen(CMD_PARAM)+1);
        cmdParamArgs.set = false;
      } else { // e.g. `$P p1 42`
        paramName = newCmd.substring(split1+1, split2);
        cmdParamArgs.value = newCmd.substring(split2+1).toFloat();
        cmdParamArgs.set = true;
      }
      cmdParamArgs.sent = -1;
      cmdParamArgs.index = -1;
      for (int i = 0; i < PARAM_COUNT; i++)
        if (paramName == params[i].name) {
          cmdParamArgs.index = i;
          break;
        }
      if (cmdParamArgs.index < 0) {
        sendError(ERR_PARAM_UNKNOWN);
        return;
      }
      cmd = CMD_PARAM;
      cmdStart = millis();
      cmdDuration = CMD_PARAM_DURATION;
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
  else if (cmd == CMD_PARAM)
  {
    // Get/set parameter
    if (cmdParamArgs.index >= 0) {
      if (cmdParamArgs.index < PARAM_COUNT) {
        if (cmdParamArgs.set) {
          params[cmdParamArgs.index].value = cmdParamArgs.value;
          Serial.println(ANS_OK);
        } else {
          sendParam(cmdParamArgs.index);
        }
      } else {
        sendError(ERR_PARAM_UNKNOWN);
      }
    }
    // Get all parameters
    else if (cmdParamArgs.sent < PARAM_COUNT) {
      sendParam(cmdParamArgs.sent);
      cmdParamArgs.sent++;
      if (cmdParamArgs.sent < PARAM_COUNT) {
        // Continue sending
        cmdStart = millis();    
        return; 
      }
      // Finish sending
      Serial.println(ANS_OK); 
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
  points.sent = 0;
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
  points.sent++;
  if (scanStep == 0)
    scanStep = scanBack ? -SCAN_POINT_DISTANCE : SCAN_POINT_DISTANCE;
  if (points.sent == SCAN_POINT_COUNT)
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
      points.sent = 0;
      scanBack = !scanBack;
      // When reversing the scan direction,
      // the next point should be measured at the same position
      // in order to have the same point number for both directions
      scanStep = 0;
    }
  }
  if (SCAN_POINT_DURATION >= 250 || points.sent % 10 == 0)
  {
    showCommand();
    showPosition();
  }
  cmdStart = millis();    
  return true;
}

void sendParam(int i)
{
  Serial.print(ANS_OK);
  Serial.print(' ');
  Serial.print(params[i].name);
  Serial.print(' ');
  if (i == 0) // Let's be an int param
    Serial.println((int)params[i].value);
  else // remaining are floats
    Serial.println(params[i].value);
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
