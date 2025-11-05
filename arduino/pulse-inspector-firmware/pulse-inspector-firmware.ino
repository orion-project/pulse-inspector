// Uncomment this to allow LCD (e.g. LCD1602) for visual checking of command status
// #define USE_LCD

/* Imports */
#include "protocol.h"
#include <TMCStepper.h>
#include "lcd.h"

/* pin definitions */
#define ENABLE_PIN 3
#define STALLGUARD_PIN 2
#define DIR_PIN 5
#define STEP_PIN 4
#define ADC_PIN A3

/* hard coded parameters */
#define SLOW_BLINK_DELAY 200
#define FAST_BLINK_DELAY 50

/* TMC2209 setup */
#define R_SENSE 0.11f     // Resistors for current sensing, here 110 mΩ
#define DRIVER_ADDRESS 0  // TMC2209 Driver address. 0 --> MS1 and MS2 tied do ground

// Currently runnng command
const char* cmd = CMD_NONE;
unsigned long cmdStart = 0;
unsigned long cmdDuration = 0;
union {
  float targetPosition = 0;
  float jogDistance;
} cmdArg;
struct {
  float center = 0;
  float step = 0;
  bool back = false;
  int sent = 0;
} cmdScanArgs;
struct {
  int sent = -1;
  int index = -1;
  bool set = false;
  float value = 0;
} cmdParamArgs;

// Stage position
bool homed = false;
float position = 0;  // Convention: Position is given in μm!
float steps_per_um = 0.05102; // --> Pitch of lead screw / steps per full motor revolution: In this example pitch is 3.92 mm, 200 steps/rev
const float um_per_step = 1.0f / steps_per_um;  // ~19.6078 µm/step

// "Persistent" memory
struct Param
{
  const char* name;
  float value;
};
Param params[PARAM_COUNT] = {
  { .name = "p1", .value = 16 },
  { .name = "p2", .value = 50.005 },
  { .name = "p3", .value = 0.5 },
};

/* homing parameters */
uint16_t homing_motor_microsteps = 0; 
uint16_t post_homing_steps = 350; // (small stage: 350, big stage: 2000)
uint32_t homing_stepper_current = 300; // default: 300
int32_t homing_velocity = 1000 / 0.715f;

/* normal movement parameters */
uint16_t motor_microsteps = 0;
uint32_t stepper_current = 300; // default: 300

// IF StallGuard does not work, it's because these two values are not set correctly or your pins are not correct.
uint8_t set_stall = 50;         //Do not set the value too high or the TMC will not detect it. Start low and work your way up. (small stage: 50, big stage: )
uint32_t set_tcools = 70;      // Set 1.2 times higher than the max TSTEP value you see

volatile bool stalled_motor = false;
bool motor_moving = false;
bool isRunning = false;
bool move_to_max = false;
bool started = false;

TMC2209Stepper driver(&Serial1, R_SENSE, DRIVER_ADDRESS);

void stalled_position() {
  stalled_motor = true;
}

// This is a function for debugging purpose to blink the arduino onboard LED
void blink(int n, int delay_ms){
  while (n > 0){
    digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on
    delay(delay_ms);                  // wait for the given delay
    digitalWrite(LED_BUILTIN, LOW);   // turn the LED off
    delay(delay_ms);                  // wait for the given delay
    n--;
  }
}

void homing(){
  // reset flags
  stalled_motor = false;
  isRunning = false;

  Serial.println("homing start");

  digitalWrite(DIR_PIN, HIGH);

  /* set current and microstepping to homing parameters */
  attachInterrupt(digitalPinToInterrupt(STALLGUARD_PIN), stalled_position, RISING);
  driver.rms_current(homing_stepper_current);
  driver.microsteps(homing_motor_microsteps);
  

  // start moving
  driver.VACTUAL(-homing_velocity);
  
  isRunning = true;
  // stop when stalled at the endstop
  while (isRunning){
    // Uncomment below for debugging
    // Serial.print(driver.SG_RESULT());
    // Serial.print(" ");
    // Serial.println(driver.TSTEP());
    if (stalled_motor) {
      driver.VACTUAL(0);
      isRunning = false;
    };
  }

  // reset after stalling
  delay(100);
  digitalWrite(ENABLE_PIN, HIGH);
  delay(100);
  digitalWrite(ENABLE_PIN, LOW);
  delay(100);

  // move back to roughly the middle of the stage
  digitalWrite(DIR_PIN, LOW);
  uint32_t idx = post_homing_steps; 
  while (idx > 0){
    idx--;
    digitalWrite(STEP_PIN, HIGH);
    delay(2);
    digitalWrite(STEP_PIN, LOW);
    delay(2);
  }

  /* set current and microstepping to homing parameters */
  detachInterrupt(digitalPinToInterrupt(STALLGUARD_PIN));
  driver.rms_current(stepper_current);
  driver.microsteps(motor_microsteps);

  // set position to 0.0
  position = 0.0;

  //Serial.println("OK 0.0");
  blink(6, FAST_BLINK_DELAY);

}

/*
void move_to_position(float target_position){
  bool dir;
  float sign;
  if (target_position - position > 0){
    dir = HIGH;
    sign = +1.0;
  } else {
    dir = LOW;
    sign = -1.0;
  }
  digitalWrite(DIR_PIN, dir);
  int steps = abs((target_position - position) * steps_per_um);
  Serial.print("moving to position  ");
  Serial.print(target_position);
  Serial.print("  from  ");
  Serial.print(position);
  Serial.print("  by taking steps  ");
  Serial.println(steps);
  for (steps; steps > 0; steps--){
    digitalWrite(STEP_PIN, HIGH);
    delay(2);
    digitalWrite(STEP_PIN, LOW);
    delay(2);    
    position = position + sign / steps_per_um;
  }
}
*/

void move_to_position(float target_position){
  float delta_um = target_position - position;
  int steps = (int)llroundf((target_position - position) / um_per_step);
  if (steps == 0) return;  // nothing to do

  bool dir = steps > 0 ? HIGH : LOW;
  int n = abs(steps);
  digitalWrite(DIR_PIN, dir);

  for (int i = 0; i < n; i++){
    digitalWrite(STEP_PIN, HIGH);
    delay(2);
    digitalWrite(STEP_PIN, LOW);
    delay(2);
  }

  position += steps / steps_per_um;  // exactly matches what we stepped
}

void setup()
{
  // wait after power up before starting the setup. This step is crucial. There might be voltage spikes on the interupt pins on power up that leave the arduino in the stall state
  delay(200);

  // start serial comms
  Serial.begin(BAUD_RATE);
  Serial1.begin(115200);
  

  // define pin modes
  pinMode(STALLGUARD_PIN, INPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(ADC_PIN, INPUT);

  // setup motor controller
  driver.begin();                       // Start all the UART communications functions behind the scenes
  driver.toff(4);                       // For operation with StealthChop, this parameter is not used, but it is required to enable the motor. In case of operation with StealthChop only, any setting is OK
  driver.blank_time(24);                // Recommended blank time select value
  driver.I_scale_analog(false);         // Disbaled to use the extrenal current sense resistors
  driver.internal_Rsense(false);        // Use the external Current Sense Resistors. Do not use the internal resistor as it can't handle high current.
  driver.mstep_reg_select(true);        // Microstep resolution selected by MSTEP register and NOT from the legacy pins.
  driver.microsteps(motor_microsteps);  // Set the number of microsteps. Due to the "MicroPlyer" feature, all steps get converterd to 256 microsteps automatically. However, setting a higher step count allows you to more accurately more the motor exactly where you want.
  driver.TPWMTHRS(0);                   // DisableStealthChop PWM mode/ Page 25 of datasheet
  driver.semin(0);                      // Turn off smart current control, known as CoolStep. It's a neat feature but is more complex and messes with StallGuard.
  driver.shaft(false);                  // Set the shaft direction. Only use this command one time during setup to change the direction of your motor.
  driver.en_spreadCycle(false);         // Disable SpreadCycle. We want StealthChop becuase it works with StallGuard.
  driver.pdn_disable(true);             // Enable UART control
  driver.VACTUAL(0);                    // Enable UART control
  driver.rms_current(stepper_current);
  driver.SGTHRS(set_stall);
  driver.TCOOLTHRS(set_tcools);
  //driver.index_step(true);

  // enable the motor driver
  digitalWrite(ENABLE_PIN, LOW);
  
  blink(3, FAST_BLINK_DELAY);

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

  // Start processing serial here
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
    
    // process homing command
    if (newCmd == CMD_HOME)
    {
      cmd = CMD_HOME;
      cmdStart = millis();
      cmdDuration = CMD_HOME_DURATION;
      homing();
    }

    // process move command
    else if (newCmd.startsWith(CMD_MOVE))
    {
      if (!checkHome()) return;  // if not homed, an error is sent by the checkHome function
      cmd = CMD_MOVE;
      cmdStart = millis();
      cmdDuration = CMD_MOVE_DURATION;
      cmdArg.targetPosition = newCmd.substring(strlen(CMD_MOVE)+1).toFloat();
      move_to_position(cmdArg.targetPosition);
    }

    // process jog command
    else if (newCmd.startsWith(CMD_JOG))
    {
      cmd = CMD_JOG;
      cmdStart = millis();
      cmdDuration = CMD_JOG_DURATION;
      cmdArg.jogDistance = newCmd.substring(strlen(CMD_JOG)+1).toFloat();
      move_to_position(position + cmdArg.jogDistance);
    }

    // process scan command
    else if (newCmd == CMD_SCAN)
    {
      if (!checkHome()) return;
      startScan(false);
    }

    // process scans command
    else if (newCmd == CMD_SCANS)
    {
      if (!checkHome()) return;
      startScan(true);
    }

    // process param command without arguments
    else if (newCmd == CMD_PARAM)
    {
      cmd = CMD_PARAM;
      cmdStart = millis();
      cmdDuration = CMD_PARAM_DURATION;
      cmdParamArgs.sent = 0;
      cmdParamArgs.index = -1;
    }

    // process param command with additional arguments
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

    // process all other inputs, i.e. unknown commands
    else
    {
      sendError(ERR_CMD_UNKNOWN);
      return;
    }
    
    showCommand(); // update LCD screen with command
    showPosition(); // update LCD screen with position
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

// processing finishing a command
void endCommand(bool stopped)
{
  if (cmd == CMD_HOME)
  {
    homed = true;
    position = 0;
    Serial.print(ANS_OK); Serial.print(' '); Serial.println(position);
  }
  else if (cmd == CMD_MOVE)
  {
    position = cmdArg.targetPosition;
    Serial.print(ANS_OK); Serial.print(' '); Serial.println(position);
  }
  else if (cmd == CMD_JOG)
  {
    position += cmdArg.jogDistance;
    if (homed)
    {
      Serial.print(ANS_OK); Serial.print(' '); Serial.println(position);
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
      move_to_position(position + cmdScanArgs.step);
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
  cmdScanArgs.center = position;
  cmdScanArgs.sent = 0;
  cmdScanArgs.step = SCAN_POINT_DISTANCE;
  cmdScanArgs.back = false;
  // Start scanning from the current position
  move_to_position(position - SCAN_HALF_RANGE);
  sendScanPoint();
}

bool sendScanPoint()
{
  int sensorValue = analogRead(ADC_PIN);
  // Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V):
  float level = sensorValue * (5.0 / 1023.0);
  Serial.print(ANS_OK); Serial.print(' '); Serial.print(position); Serial.print(' '); Serial.println(level);
  cmdScanArgs.sent++;
  if (cmdScanArgs.step == 0)
    cmdScanArgs.step = cmdScanArgs.back ? -SCAN_POINT_DISTANCE : SCAN_POINT_DISTANCE;
  if (cmdScanArgs.sent == SCAN_POINT_COUNT)
  {
    move_to_position(cmdScanArgs.center);
    // Send addition OK to show the scan is finished
    Serial.println(ANS_OK);
    if (cmd == CMD_SCAN)
    {
      // Finish the command
      return false;
    }
    else
    {
      cmdScanArgs.sent = 0;
      cmdScanArgs.back = !cmdScanArgs.back;
      // When reversing the scan direction,
      // the next point should be measured at the same position
      // in order to have the same point number for both directions
      cmdScanArgs.step = 0;
    }
  }
  if (SCAN_POINT_DURATION >= 250 || cmdScanArgs.sent % 10 == 0)
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
  if (i == 0) {
    // This parameter is integer
    Serial.println((int)params[i].value);
  } else if (i == 1) {
    // By default, Serial formats floats with 2 decimal digits
    // So if we know a parameter has a higher resolution,
    // we should configure both - the sending here 
    // and the parameter spec in board_config.ini
    Serial.println(params[i].value, 3);
  } else {
    Serial.println(params[i].value);
  }
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
