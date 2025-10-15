# Emulator Dummy

This is a test sketch that allows testing the interaction of the UI with boards in the absence of real hardware parts. Only an Arduino board is needed - the sketch emulates the behavior of hardware components that would normally be connected to it.

This approach is somewhat analogous to what the `virtual_board.py` module does, except that `virtual_board.py` simulates the entire board in software (no hardware required at all), while this sketch runs on real hardware (an Arduino board) but simulates the connected hardware parts.

Use this sketch for UI testing and development when you have an Arduino board available but don't have access to the actual hardware components.

An LCD screen with I2C can be used optionally to show currently running operations on the board. But the sketch is fully functional even without it; just comment the `USE_LCD` definition.

![](./emulator_dummy.png)
