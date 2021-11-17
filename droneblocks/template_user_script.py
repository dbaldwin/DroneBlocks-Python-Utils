# User Configuration5
SAMPLE_CONFIG_ITEM = 42

def init(tello, params):
    """

    :param tello: Reference to the DJITelloPy Tello object.
    :type tello: Tello
    :param fly_flag: True - the fly flag was specified and the Tello will take off. False - the Tello will NOT
                        be instructed to take off
    :type fly_flag:  bool
    :return: None
    :rtype:
    """
    fly_flag = params['fly_flag']
    print(f"Inside init method.  fly_flag: {fly_flag}, sample config item: {SAMPLE_CONFIG_ITEM}")
    return None

def handler(tello, frame, params):
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
    fly_flag = None
    last_key = None
    if params:
        fly_flag = params.get('fly_flag', False)
        last_key = params.get('last_key_pressed', None)

    print(f"Inside handler method.  fly_flag: {fly_flag}, sample config item: {SAMPLE_CONFIG_ITEM}")
    return

def stop(tello, params):
    pass