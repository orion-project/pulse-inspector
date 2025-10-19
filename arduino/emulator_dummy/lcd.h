#ifndef USE_LCD
// No operations
#define showPosition()
#define showCommand()
#define showHello()
#else

// On Uno R4 there is the warning 
// "LiquidCrystal I2C claims to run on avr architecture"
// but it works fine anyway
#include <LiquidCrystal_I2C.h>

#define SCREEN_W 16
#define SCREEN_H 2

LiquidCrystal_I2C lcd(0x27, SCREEN_W, SCREEN_H);

void showText(const String &str, int row)
{
  lcd.setCursor(0, row);
  lcd.print(str);
  for (int c = str.length(); c < SCREEN_W; c++)
    lcd.write(' ');
}

void showCommand()
{
  #define _(s) showText(s, 1)
  if (cmd == CMD_NONE) _("Ready");
  else if (cmd == CMD_HOME) _("Home... ");
  else if (cmd == CMD_MOVE) _("Move... ");
  else if (cmd == CMD_JOG) _("Jog... ");
  else if (cmd == CMD_SCAN || cmd == CMD_SCANS)
  {
    String s = "Scan... ";
    s += points.sent;
    _(s);
  }
  else if (cmd == CMD_PARAM)
  {
    if (cmdParamArgs.sent >= 0)
        _("Send params...");
    else _("Write param...");
  }
  else _("");
  #undef _
}

void showPosition()
{
  String msg;
  if (homed)
  {
    msg = "Pos: ";
    msg += position;
  }
  else
    msg = "Need homing";
  showText(msg, 0);
}

void showHello()
{
  lcd.init();
  lcd.backlight();
  lcd.begin(SCREEN_W, SCREEN_H);
  lcd.setCursor(0, 0);
  lcd.print("Pulse Inspector");
  showCommand();
  delay(1000);
  showPosition();
}

#endif // USE_LCD