import cv2
from droneblocks.DroneBlocksTello import DroneBlocksTello
import signal
import sys
import time
import argparse
import importlib
import logging
from imutils.video import VideoStream
import imutils
import threading
import queue
import traceback
import pkgutil
from droneblocks import tello_keyboard_mapper as keymapper
from droneblocksutils.exceptions import LandException
from droneblocks.uielements import RectButton

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()

tello = None
local_video_stream = None
user_script_requested_land = False

# maximum number of
MAX_VIDEO_Q_DEPTH = 10

# add a little delay to throttle the number of video frames
# put into the video queue
show_video_per_second = 0.3

# This is hard coded because if the image gets too big then
# the lag in the video stream gets very pronounced.  This is
# parameter that will be system configured and the user will
# not be allowed change it at run time
IMAGE_WIDTH = 600
IMAGE_HEIGHT = None

TELLO_VIDEO_WINDOW_NAME = "Tello Video"
ORIGINAL_VIDEO_WINDOW_NAME = "Original"
KEYBOARD_CMD_WINDOW_NAME = "Keyboard Cmds"

ui_elements=[]

# True - write to the console the key value that was pressed
# False - do not write to the console
# useful to debug to get the actual key value for specific keyboards.
LOG_KEY_PRESS_VALUES = False

# Global value holding the last key pressed.
# value will be key from the tello_keyboard_mapper.py file
g_key_press_value=None

# Global state of Tello, last read or set values
battery_update_timestamp = 0
battery_left = "--"
last_command_timestamp = 0
last_command = ""
speed = 0
speed_x = 0
speed_y = 0
speed_z = 0
height = 0

DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS = 30
DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS = 90

# function to handle keyboard interrupt
def signal_handler(sig, frame):
    shutdown_gracefully()

    sys.exit(-1)


def shutdown_gracefully():
    if tello:
        try:
            tello.end()
        except:
            pass

    if local_video_stream:
        try:
            local_video_stream.stop()
        except:
            pass


tello_image = None

def _up_button_handler():
    print("up")
    if tello:
        tello.move_up(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

def _down_button_handler():
    print("down")
    if tello:
        tello.move_down(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

def _left_button_handler():
    print("left")
    if tello:
        tello.move_left(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)
def _right_button_handler():
    print("right")
    if tello:
        tello.move_right(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)
def _fwd_button_handler():
    print("fwd")
    if tello:
        tello.move_forward(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)
def _bkwd_button_handler():
    print("bkwd")
    if tello:
        tello.move_back(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)
def _cw_button_handler():
    print("cw")
    if tello:
        tello.rotate_clockwise(DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS)
def _ccw_button_handler():
    print("ccw")
    if tello:
        tello.rotate_counter_clockwise(DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS)
def _land_button_handler():
    global user_script_requested_land
    print("land")
    if tello:
        tello.land()
        user_script_requested_land = True


def _mouse_events(event, x, y,
                 flags, param):
    for ui_element in ui_elements:
        ui_element.process_point(x, y, tello_image, event)
        ui_element.draw(tello_image)


def _display_text(image, text, bat_left, speed_param, speed_x_param, speed_y_param, speed_z_param, height_param):
    key = -666 # set to a non-existent key
    if image is not None:
        cv2.putText(image, text, (90, int(image.shape[0] * 0.95)), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)  #

        cv2.putText(image, f"Battery: {bat_left}%", (int(image.shape[1] * 0.55), 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"Speed: {speed_param}", (int(image.shape[1] * 0.55), 80), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"X: {speed_x_param}", (int(image.shape[1] * 0.75), 120), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"Y: {speed_y_param}", (int(image.shape[1] * 0.75), 160), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"Z: {speed_z_param}", (int(image.shape[1] * 0.75), 200), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"H: {height_param}", (int(image.shape[1] * 0.75), 240), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)


        cv2.imshow(KEYBOARD_CMD_WINDOW_NAME, image)
        key = cv2.waitKey(150) & 0xff

    return key


def _exception_safe_process_keyboard_commands(tello, fly):
    try:
        return _process_keyboard_commands(tello, fly)
    except Exception as exc:
        LOGGER.error("Error processing keyboard command")
        LOGGER.error(f"{exc}")
        return 1, None


def _process_keyboard_commands(tello, fly):
    """
    Process keyboard commands via OpenCV.
    :param tello:
    :type tello:
    :param fly: Flag indicating if the Tello is set to fly
    :type bool:
    :return: 0 - Exit, 1 - continue processing, 2 - suspend processing handler
    :rtype:
    """
    global tello_image, battery_update_timestamp, battery_left, last_command, last_command_timestamp
    global speed
    global speed_x
    global speed_y
    global speed_z
    global g_key_press_value
    global height

    if tello_image is None:
        tello_image = cv2.imread("./media/tello_drone_image2.png")
        if tello_image is not None:
            tello_image = imutils.resize(tello_image, width=IMAGE_WIDTH)
        else:
            # we may have pip installed this library and we need to look in the installed package
            # directory structure
            droneblocks_package = pkgutil.get_loader("droneblocks")
            droneblocks_init_file_path = droneblocks_package.get_filename()
            # '/Users/patrickryan/Development/junk-projects/junk11/venv/lib/python3.8/site-packages/droneblocks/__init__.py'
            package_image_path = droneblocks_init_file_path.replace("__init__.py", "media/tello_drone_image2.png")
            tello_image = cv2.imread(package_image_path)
            if tello_image is not None:
                tello_image = imutils.resize(tello_image, width=IMAGE_WIDTH)
            else:
                print("Could not ready file media/tello_drone_image2.png")

        # add buttons to Tello Command Window
        btn = RectButton(int(tello_image.shape[1] * 0.01), int(tello_image.shape[0] * .01), "Up", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_up_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "Down", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_down_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "Left", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_left_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "Right", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_right_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "Fwd", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_fwd_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "Bwd", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_bkwd_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)


        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "CW", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_cw_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(btn.anchor_x), int(btn.anchor_y+btn.height+5), "CCW", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_ccw_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)

        btn = RectButton(int(tello_image.shape[1] * 0.8), int(tello_image.shape[0] * .85), "LAND", (255, 0, 0), (0, 0, 255),
                             (64, 64, 64))
        btn.set_click_callback(_land_button_handler)
        btn.draw(tello_image)
        ui_elements.append(btn)


    # update battery every 10 seconds
    if tello and time.time() - battery_update_timestamp > 10:
        battery_update_timestamp = time.time()
        battery_left = tello.get_battery()

    # update other values every 2 seconds
    if time.time() - last_command_timestamp > 2:
        last_command_timestamp = time.time()
        last_command = ""
        g_key_press_value = None
        if tello:
            speed = tello.get_speed()
            speed_x = tello.get_speed_x()
            speed_y = tello.get_speed_y()
            speed_z = tello.get_speed_z()
            height = tello.get_height()

    exit_flag = 1
    if tello_image is None:
        return exit_flag

    cmd_tello_image = tello_image.copy()
    key = _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )

    # because getting keyboard input is a polling process, someone might
    # hold down a key to get the command to register. To avoid getting
    # multiple keyboard commands only look for new commands once the
    # last_command string is empty

    if last_command != "":
        return exit_flag

    if key != 255 and LOG_KEY_PRESS_VALUES:
        LOGGER.debug(f"key: {key}")

    # always save the numeric value of the key pressed in case it is
    # a key the user script will act on
    g_key_press_value = key

    if key == keymapper.mapping[keymapper.LAND1]:
        g_key_press_value=keymapper.LAND1
        last_command = "Land"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        exit_flag = 0

    elif key == keymapper.mapping[keymapper.FORWARD]:
        g_key_press_value=keymapper.FORWARD
        last_command = "Forward"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.move_forward(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.BACKWARD]:
        g_key_press_value=keymapper.BACKWARD
        last_command = "Backward"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.move_back(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.LEFT]:
        g_key_press_value=keymapper.LEFT
        last_command = "Left"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.move_left(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.RIGHT]:
        g_key_press_value=keymapper.RIGHT
        last_command = "Right"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.move_right(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.CLOCKWISE]:
        g_key_press_value=keymapper.CLOCKWISE
        last_command = "Clockwise"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.rotate_clockwise(DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.COUNTER_CLOCKWISE]:
        g_key_press_value=keymapper.COUNTER_CLOCKWISE
        last_command = "Counter Clockwise"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.rotate_counter_clockwise(DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.UP]:
        g_key_press_value=keymapper.UP
        last_command = "Up"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.move_up(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.DOWN]:
        g_key_press_value=keymapper.DOWN
        last_command = "Down"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.move_down(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.LAND2]:
        g_key_press_value=keymapper.LAND2
        last_command = "Land"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        exit_flag = 0

    elif key == keymapper.mapping[keymapper.HOVER]:
        g_key_press_value=keymapper.HOVER
        last_command = "Hover"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        if fly:
            tello.send_rc_control(0, 0, 0, 0)

    elif key == keymapper.mapping[keymapper.EMERGENCY]:
        g_key_press_value=keymapper.EMERGENCY
        last_command = "Emergency"
        tello.emergency()
        exit_flag = 0  # stop processing the handler function but continue to fly and see video

    elif key == keymapper.mapping[keymapper.SPEED_INC]:
        g_key_press_value=keymapper.SPEED_INC
        last_command = "Increase Speed"
        speed = speed + 5
        if speed > 100:
            speed = 100
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        tello.set_speed(speed)

    elif key == keymapper.mapping[keymapper.SPEED_DEC]:
        g_key_press_value=keymapper.SPEED_DEC
        last_command = "Decrease Speed"
        speed = speed - 5
        if speed < 20:
            speed = 20
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z, height )
        tello.set_speed(speed)

    elif LOG_KEY_PRESS_VALUES and key != 255:
        last_command = None
        _display_text(cmd_tello_image, f"Key Value: {key}", battery_left, speed, speed_x, speed_y, speed_z, height )
        time.sleep(1)

    # LOGGER.debug(f"Exit Flag: {exit_flag}")
    return exit_flag


def _get_video_frame(frame_read, vid_sim):
    f = None
    try:
        if frame_read:
            f = frame_read.frame
        elif vid_sim and local_video_stream:
            f = local_video_stream.read()

        if f is not None:
            f = imutils.resize(f, width=IMAGE_WIDTH)

    except Exception as exc:
        LOGGER.error("Exception getting video frame")
        LOGGER.error(f"{exc}")

    return f


def process_tello_video_feed(handler_file, video_queue, stop_event, video_event, fly=False, tello_video_sim=False,
                             display_tello_video=False):
    """

    :param exit_event: Multiprocessing Event.  When set, this event indicates that the process should stop.
    :type exit_event:
    :param video_queue: Thread Queue to send the video frame to
    :type video_queue: threading.Queue
    :param stop_event: Thread Event to indicate if this thread function should stop
    :type stop_event: threading.Event
    :param video_event: threading.Event to indicate when the main loop is ready for video
    :type video_event: threading.Event
    :param fly: Flag used to indicate whether the drone should fly.  False is useful when you just want see the video stream.
    :type fly: bool
    :param max_speed_limit: Maximum speed_param that the drone will send as a command.
    :type max_speed_limit: int
    :return: None
    :rtype:
    """
    global tello, local_video_stream, speed, user_script_requested_land
    last_show_video_queue_put_time = 0
    handler_method = None
    stop_method = None

    try:
        tello = DroneBlocksTello()
        rtn = tello.connect()
        if fly or (not tello_video_sim and display_tello_video):
            LOGGER.debug(f"Connect Return: {rtn}")
            speed = tello.get_speed()

        if handler_file:
            handler_file = handler_file.replace(".py", "")
            handler_module = importlib.import_module(handler_file)
            if handler_module is None:
                raise f"Could not locate handler file: {handler_file}"

            init_method = getattr(handler_module, 'init')
            handler_method = getattr(handler_module, 'handler')
            stop_method = getattr(handler_module, 'stop', None)

            params = {}
            params['fly_flag'] = fly
            params['last_key_pressed'] = g_key_press_value

            new_key_map = init_method(tello, params)
            if new_key_map is not None:
                for k,v in new_key_map.items():
                    keymapper.mapping[k] = v

        frame_read = None
        if tello and video_queue:
            tello.streamon()
            frame_read = tello.get_frame_read()

        if fly:
            tello.takeoff()
            # send command to go no where
            tello.send_rc_control(0, 0, 0, 0)

        if tello_video_sim and local_video_stream is None:
            local_video_stream = VideoStream(src=0).start()
            time.sleep(2)

        params = {}
        while not stop_event.isSet():
            frame = _get_video_frame(frame_read, tello_video_sim)

            if frame is None:
                # LOGGER.debug("Failed to read video frame")
                if handler_method:
                    params['fly_flag']=fly
                    params['last_key_pressed']=g_key_press_value
                    handler_method(tello, frame, params)
                # else:
                #     # stop let keyboard commands take over
                #     if fly:
                #         tello.send_rc_control(0, 0, 0, 0)
                continue

            original_frame = frame.copy()

            if handler_method:
                rtn_frame = handler_method(tello, frame, fly)
                if rtn_frame is not None:
                    frame = rtn_frame

            # else:
            #     # stop let keyboard commands take over
            #     if fly:
            #         tello.send_rc_control(0, 0, 0, 0)

            # send frame to other processes
            if video_queue and video_event.is_set():
                try:
                    if time.time() - last_show_video_queue_put_time > show_video_per_second:
                        last_show_video_queue_put_time = time.time()
                        video_queue.put_nowait([frame, original_frame])
                except:
                    pass

    except LandException:
        LOGGER.debug(f"User script requested landing")
        user_script_requested_land = True
    except Exception as exc:
        LOGGER.error(f"Exiting Tello Process with exception: {exc}")
        traceback.print_exc()
    finally:
        # then the user has requested that we land and we should not process this thread
        # any longer.
        # to be safe... stop all movement
        if fly:
            tello.send_rc_control(0, 0, 0, 0)

        if stop_method:
            params = {}
            params['fly_flag'] = fly
            params['last_key_pressed'] = g_key_press_value

            stop_method(tello, params)

        stop_event.clear()

    LOGGER.info("Leaving User Script Processing Thread.....")


def main():
    global LOG_KEY_PRESS_VALUES, DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS, DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    ap = argparse.ArgumentParser()
    ap.add_argument("--test-install", action='store_true', help="Test the command can run, then exit and do nothing. ")
    ap.add_argument("--display-video", action='store_true', help="Display Drone video using OpenCV.")
    ap.add_argument("--display-unknown-keyvalue", action='store_true', help="Display value of unknown keyboard values.")
    ap.add_argument("--keyboard-flying-distance", type=int, default=30, help="When using keyboard to fly, this is the default distance in cm to fly. Default=30")
    ap.add_argument("--keyboard-flying-rotation", type=int, default=90, help="When using keyboard to fly, this is the default rotation in degrees to rotate. Default=90")

    ap.add_argument("--handler", type=str, required=False, default="",
                    help="Name of the python file with an init and handler method.  Do not include the .py extension and it has to be in the same folder as this main driver")
    output_group = ap.add_mutually_exclusive_group()
    output_group.add_argument('-v', '--verbose', action='store_true', help='Be loud')
    output_group.add_argument('-i', '--info', action='store_true', help='Show only important information')
    fly_sim_group = ap.add_mutually_exclusive_group()
    fly_sim_group.add_argument("--fly", action='store_true',
                               help="Flag to control whether the drone should take flight.  Default: False")
    fly_sim_group.add_argument("--tello-video-sim", action='store_true',
                               help="Flag to control whether to use the computer webcam as a simulated Tello video feed. Default: False")
    ap.add_argument("--show-original-video", action='store_true',
                    help="Flag to control whether to show the original video frame from the Tello along with frame processed by the handler function. Default: False")

    args = vars(ap.parse_args())
    if args['test_install']:
        print("Install worked and the Tello Script Runner can be executed")
        import os
        dir_path = os.path.dirname(os.path.realpath(__file__))
        print(dir_path)
        sys.exit(0)

    LOGGER.setLevel(logging.ERROR)
    if args["verbose"]:
        LOGGER.setLevel(logging.NOTSET)
    if args["info"]:
        LOGGER.setLevel(logging.INFO)

    LOGGER.debug(args.items())

    show_original_frame = args['show_original_video']
    fly = args['fly']
    LOGGER.debug(f"Fly: {fly}")
    display_video = args['display_video']
    handler_file = args['handler']
    tello_video_sim = args['tello_video_sim']

    # if the user selected tello_video_sim, force the display video flag
    if tello_video_sim:
        display_video = True

    # display unknown keyboard key values in Cmd window and in console
    if args['display_unknown_keyvalue']:
        LOG_KEY_PRESS_VALUES = True

    DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS = args['keyboard_flying_distance']
    DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS = args['keyboard_flying_rotation']

    # video queue to hold the frames from the Tello
    video_queue = None
    if display_video:
        video_queue = queue.Queue(maxsize=MAX_VIDEO_Q_DEPTH)

    try:
        TELLO_LOGGER = logging.getLogger('djitellopy')
        TELLO_LOGGER.setLevel(logging.ERROR)

        cv2.namedWindow(TELLO_VIDEO_WINDOW_NAME, cv2.WINDOW_NORMAL)
        # cv2.resizeWindow(TELLO_VIDEO_WINDOW_NAME, 600, 600)
        cv2.namedWindow(KEYBOARD_CMD_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(KEYBOARD_CMD_WINDOW_NAME, _mouse_events)

        if show_original_frame:
            cv2.namedWindow(ORIGINAL_VIDEO_WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.moveWindow(KEYBOARD_CMD_WINDOW_NAME, 450, 410)
            cv2.moveWindow(TELLO_VIDEO_WINDOW_NAME, 200+IMAGE_WIDTH, 100)
            cv2.moveWindow(ORIGINAL_VIDEO_WINDOW_NAME, 200, 100)
        else:
            cv2.moveWindow(TELLO_VIDEO_WINDOW_NAME, 200, 100)
            cv2.moveWindow(KEYBOARD_CMD_WINDOW_NAME, 200+IMAGE_WIDTH, 100)

        stop_event = threading.Event()
        ready_to_show_video_event = threading.Event()
        p1 = threading.Thread(target=process_tello_video_feed,
                              args=(
                              handler_file, video_queue, stop_event, ready_to_show_video_event, fly, tello_video_sim,
                              display_video,))
        p1.setDaemon(True)
        p1.start()

        while True:
            key_status = _exception_safe_process_keyboard_commands(tello, fly)
            if key_status == 0 or user_script_requested_land == True:
                stop_event.set()
                ready_to_show_video_event.clear()
                # wait up to 5 seconds for the handler thread to exit
                # the handler thread will clear the stop_event when it
                # exits
                for _ in range(5):
                    if stop_event.isSet():
                        time.sleep(1)
                    else:
                        break
                break

            ready_to_show_video_event.set()
            try:
                # LOGGER.debug(f"Q size: {video_queue.qsize()}")
                if video_queue is not None:
                    frames = video_queue.get(block=False)
                    frame = frames[0]
                else:
                    frame = None
                    frames = []
            except:
                frame = None
                frames = []

            # check for video feed
            if display_video and frame is not None:
                try:
                    # display the frame to the screen
                    cv2.imshow(TELLO_VIDEO_WINDOW_NAME, frame)
                    if show_original_frame:
                        cv2.imshow(ORIGINAL_VIDEO_WINDOW_NAME, frames[1])
                    cv2.waitKey(1)
                except Exception as exc:
                    LOGGER.error(f"Display Queue Error: {exc}")

    finally:
        LOGGER.debug("Complete...")

        cv2.destroyWindow(TELLO_VIDEO_WINDOW_NAME)
        cv2.destroyWindow(KEYBOARD_CMD_WINDOW_NAME)
        cv2.destroyAllWindows()
        shutdown_gracefully()


if __name__ == '__main__':
    main()
