# Arduino Sketches

## Protocol

### Commands

#### Home `$H`

Move the stage to a known reference position.

Parameters:
- None

Returns:
- New current position, e.g. `OK 0`

#### Stop `$X`

Cancel any movement or measurement.

Parameters:
- None

Returns:
- None

#### Move `$G`

Go to an absolute position; available only after homing.

Parameters:
- Position to go to (in µm) or none

Returns:
- New current position, e.g. `OK 20.5`

Examples:
- `$G 10` - go to 10µm from zero
- `$G` - only return the current position

#### Jog `$J`

Go to a position relative to the current one.

Parameters:
- Distance in µm or steps
- Use steps instead of µm

Returns:
- New current position if the board has been homed, none otherwise

Examples:
- `$J -10` - jog backward to 10 µm
- `$J 200 S` - jog forward to 200 steps

### Single measurement `$MS`

Do a single autocorrelation scan.

Parameters:
- Number of points
- Distance between points (in µm)

Returns:
- List of position & signal data

Examples:
- `$MS 10 0.5`

### Continuous measurement `$MC`

Continuously scan the autocorrelation signal back and forth.

Parameters:
- Number of points
- Distance between points (in µm)

Returns:
- List of position & signal data

Examples:
- `$MC 10 0.5`
