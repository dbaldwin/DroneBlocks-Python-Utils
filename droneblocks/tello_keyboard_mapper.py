'''
This file will control the keyboard mapping to flying commands.

The init routine will setup the default values, however, the api supports the ability to update
the value for any of the flying commands.
'''

LAND1 = "LAND1"
FORWARD = "FORWARD"
BACKWARD = "BACKWARD"
LEFT = "LEFT"
RIGHT = "RIGHT"
CLOCKWISE = "CLOCKWISE"
COUNTER_CLOCKWISE = "COUNTER_CLOCKWISE"
UP = "UP"
DOWN = "DOWN"
LAND2 = "LAND2"
HOVER = "HOVER"
EMERGENCY = "EMERGENCY"
SPEED_INC = "SPEED_INC"
SPEED_DEC = "SPEED_DEC"

mapping = {
    LAND1: 27, # ESC
    FORWARD: ord('w'),
    BACKWARD: ord('s'),
    LEFT: ord('a'),
    RIGHT: ord('d'),
    CLOCKWISE: ord('e'),
    COUNTER_CLOCKWISE: ord('q'),
    UP: ord('r'),
    DOWN: ord('f'),
    LAND2: ord('l'),
    HOVER: ord('h'),
    EMERGENCY: ord('x'),
    SPEED_INC: ord('+'),
    SPEED_DEC: ord('-')


}
