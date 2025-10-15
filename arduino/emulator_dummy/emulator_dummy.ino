// Uncomment this to allow LCD (e.g. LCD1602) for visual checking of command status
#define USE_LCD

#define CMD_NONE nullptr
#define CMD_HOME "$H"
#define CMD_HOME_DURATION 5000
#define CMD_STOP "$X"
// Debug command for injecting errors into running commands
// for testing how UI parses and displays command failures
#define CMD_ERROR "$DE"

#define ANS_OK "OK"
#define ANS_ERR "ERR"
#define ERR_OK 0
#define ERR_UNKNOWN 100
#define ERR_CMD_UNKNOWN 101
#define ERR_CMD_RUNNIG 102
#define ERR_CMD_FOOLISH 103

#define BAUD_RATE 115200

#ifdef USE_LCD
// On Uno R4 there is the warning "LiquidCrystal I2C claims to run on avr architecture" but it works fine
#include <LiquidCrystal_I2C.h>
#define SCREEN_W 16
#define SCREEN_H 2
LiquidCrystal_I2C lcd(0x27, SCREEN_W, SCREEN_H);
#endif

// Currently runnng command
char* cmd = 0;
unsigned long cmdStart = 0;
unsigned long cmdDuration = 0;

#ifdef USE_LCD
void showCommand() {
  char *msg = " ";
  if (cmd == CMD_NONE) {
    msg = "Ready";
  } else if (cmd == CMD_HOME) {
    msg = "Homing... ";
  }
  lcd.setCursor(0, 1);
  lcd.print(msg);
  for (int c = strlen(msg); c < SCREEN_W; c++) {
    lcd.setCursor(c, 1);
    lcd.write(' ');
  }
}
#else
// No operation
#define showCommand()
#endif

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial);

#ifdef USE_LCD
  lcd.init();
  lcd.backlight();
  lcd.begin(SCREEN_W, SCREEN_H);
  lcd.setCursor(0, 0);
  lcd.print("Pulse Inspector");
  showCommand();
#endif
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
      lcd.setCursor(0, 1);
      lcd.print("ERROR");
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
  cmd = CMD_NONE;
  cmdStart = 0;
  cmdDuration = 0;
  if (ok) {
    Serial.println(ANS_OK);
  }
  showCommand();
}

