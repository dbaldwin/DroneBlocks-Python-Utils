# User Configuration5
SAMPLE_CONFIG_ITEM = 42
import time
import droneblocks.tello_keyboard_mapper as kmap

def init(tello, fly_flag=False):
    """

    :param tello: Reference to the DJITelloPy Tello object.
    :type tello: Tello
    :param fly_flag: True - the fly flag was specified and the Tello will take off. False - the Tello will NOT
                        be instructed to take off
    :type fly_flag:  bool
    :return: None
    :rtype:
    """

    # Create a key mapping for the Apple Keypad5
    new_key_map = {
        kmap.FORWARD: 56,
        kmap.BACKWARD: 50,
        kmap.HOVER: 53,
        kmap.LEFT: 52,
        kmap.RIGHT: 54,
        kmap.COUNTER_CLOCKWISE: 55,
        kmap.CLOCKWISE: 57,
        kmap.SPEED_INC: 43,
        kmap.SPEED_DEC: 45,
        kmap.LAND2: 3,
        kmap.EMERGENCY: 46
    }
    print(f"Inside init method.  fly_flag: {fly_flag}, sample config item: {SAMPLE_CONFIG_ITEM}")
    return new_key_map

def handler(tello, frame, fly_flag=False):
    """

    :param tello: Reference to the DJITelloPy Tello object.
    :type tello: Tello
    :param frame: image
    :type frame:
    :param fly_flag: True - the fly flag was specified and the Tello will take off. False - the Tello will NOT
                        be instructed to take off
    :type fly_flag:  bool
    :return: None
    :rtype:
    """

    # print(f"Inside handler method.  fly_flag: {fly_flag}, sample config item: {SAMPLE_CONFIG_ITEM}")
    return