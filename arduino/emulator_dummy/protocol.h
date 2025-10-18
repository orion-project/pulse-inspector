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
#define CMD_PARAM "$P"
#define CMD_PARAM_DURATION 100
#define CMD_ERROR "$DE"

#define SCAN_POINT_HALF_COUNT 100
#define SCAN_POINT_COUNT (2*SCAN_POINT_HALF_COUNT + 1)
#define SCAN_POINT_DISTANCE 0.1
#define SCAN_POINT_DURATION 10
#define SCAN_HALF_RANGE (SCAN_POINT_DISTANCE * SCAN_POINT_HALF_COUNT)
#define SCAN_PROFILE_AMPLITUDE 1000
#define SCAN_PROFILE_NOISE 0.05
#define SCAN_PROFILE_WIDTH (SCAN_HALF_RANGE / 5.0)

#define ANS_OK "OK"
#define ANS_ERR "ERR"
#define ERR_OK 0
#define ERR_UNKNOWN 100 // Unknown error
#define ERR_CMD_UNKNOWN 101 // Unknown command
#define ERR_CMD_RUNNIG 102 // Another command is already running
#define ERR_CMD_FOOLISH 103 // Command is not applicable
#define ERR_POS_LOST 104 // Position lost, homing required
#define ERR_CMD_BAD_ARG 105 // Invalid command parameter
#define ERR_CMD_CANCEL 106 // Command canceled

#define BAUD_RATE 115200
