import cv2
from droneblocks.DroneBlocksTello import DroneBlocksTello
import signal
import sys
import time
from datetime import datetime
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

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()

tello = None
local_video_stream = None

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

# True - write to the console the key value that was pressed
# False - do not write to the console
# useful to debug to get the actual key value for specific keyboards.
LOG_KEY_PRESS_VALUES = False

# Global state of Tello, last read or set values
battery_update_timestamp = 0
battery_left = "--"
last_command_timestamp = 0
last_command = ""
speed = 0
speed_x = 0
speed_y = 0
speed_z = 0

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


def _display_text(image, text, bat_left, speed, speed_x, speed_y, speed_z ):
    key = -666 # set to a non-existent key
    if image is not None:
        cv2.putText(image, text, (50, int(image.shape[0] * 0.90)), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)  #

        cv2.putText(image, f"Battery: {bat_left}%", (int(image.shape[1] * 0.55), 40), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"Speed: {speed}", (int(image.shape[1] * 0.55), 80), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"X: {speed_x}", (int(image.shape[1] * 0.75), 120), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"Y: {speed_y}", (int(image.shape[1] * 0.75), 160), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 0), 2, cv2.LINE_AA)

        cv2.putText(image, f"Z: {speed_z}", (int(image.shape[1] * 0.75), 200), cv2.FONT_HERSHEY_SIMPLEX, 1,
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
        return 1


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

    if tello and time.time() - battery_update_timestamp > 10:
        battery_update_timestamp = time.time()
        battery_left = tello.get_battery()
        speed = tello.query_speed
        speed_x = tello.get_speed_x()
        speed_y = tello.get_speed_y()
        speed_z = tello.get_speed_z()

    if time.time() - last_command_timestamp > 2:
        last_command_timestamp = time.time()
        last_command = ""

    exit_flag = 1
    cmd_tello_image = tello_image.copy()
    key = _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )

    # because getting keyboard input is a polling process, someone might
    # hold down a key to get the command to register. To avoid getting
    # multiple keyboard commands only look for new commands once the
    # last_command string is empty

    if last_command != "":
        return exit_flag

    if key != 255 and LOG_KEY_PRESS_VALUES:
        LOGGER.debug(f"key: {key}")

    if key == keymapper.mapping[keymapper.LAND1]:
        last_command = "Land"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        exit_flag = 0

    elif key == keymapper.mapping[keymapper.FORWARD]:
        last_command = "Forward"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.move_forward(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.BACKWARD]:
        last_command = "Backward"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.move_back(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.LEFT]:
        last_command = "Left"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.move_left(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.RIGHT]:
        last_command = "Right"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.move_right(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.CLOCKWISE]:
        last_command = "Clockwise"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.rotate_clockwise(DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.COUNTER_CLOCKWISE]:
        last_command = "Counter Clockwise"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.rotate_counter_clockwise(DEFAULT_YAW_ROTATION_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.UP]:
        last_command = "Up"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.move_up(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.DOWN]:
        last_command = "Down"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.move_down(DEFAULT_DISTANCE_FOR_KEYBOARD_COMMANDS)

    elif key == keymapper.mapping[keymapper.LAND2]:
        last_command = "Land"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        exit_flag = 0

    elif key == keymapper.mapping[keymapper.HOVER]:
        last_command = "Hover"
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        if fly:
            tello.send_rc_control(0, 0, 0, 0)

    elif key == keymapper.mapping[keymapper.EMERGENCY]:
        last_command = "Emergency"
        tello.emergency()
        exit_flag = 0  # stop processing the handler function but continue to fly and see video

    elif key == keymapper.mapping[keymapper.SPEED_INC]:
        last_command = "Increase Speed"
        speed = speed + 5
        if speed > 100:
            speed = 100
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        tello.set_speed(speed)

    elif key == keymapper.mapping[keymapper.SPEED_DEC]:
        last_command = "Decrease Speed"
        speed = speed - 5
        if speed < 20:
            speed = 20
        _display_text(cmd_tello_image, last_command, battery_left, speed, speed_x, speed_y, speed_z )
        tello.set_speed(speed)

    elif LOG_KEY_PRESS_VALUES and key != 255:
        last_command = None
        _display_text(cmd_tello_image, f"Key Value: {key}", battery_left, speed, speed_x, speed_y, speed_z )
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
    :param max_speed_limit: Maximum speed that the drone will send as a command.
    :type max_speed_limit: int
    :return: None
    :rtype:
    """
    global tello, local_video_stream, speed
    last_show_video_queue_put_time = 0
    handler_method = None

    try:
        if fly or (not tello_video_sim and display_tello_video):
            tello = DroneBlocksTello()
            rtn = tello.connect()
            LOGGER.debug(f"Connect Return: {rtn}")
            speed = tello.get_speed()

        if handler_file:
            handler_file = handler_file.replace(".py", "")
            handler_module = importlib.import_module(handler_file)
            init_method = getattr(handler_module, 'init')
            handler_method = getattr(handler_module, 'handler')

            new_key_map = init_method(tello, fly_flag=fly)
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

        while not stop_event.isSet():
            frame = _get_video_frame(frame_read, tello_video_sim)

            if frame is None:
                # LOGGER.debug("Failed to read video frame")
                if handler_method:
                    handler_method(tello, frame, fly)
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


    except Exception as exc:
        LOGGER.error(f"Exiting Tello Process with exception: {exc}")
        traceback.print_exc()
    finally:
        # then the user has requested that we land and we should not process this thread
        # any longer.
        # to be safe... stop all movement
        if fly:
            tello.send_rc_control(0, 0, 0, 0)

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
    video_queue = queue.Queue(maxsize=MAX_VIDEO_Q_DEPTH)

    try:
        # TELLO_LOGGER = logging.getLogger('djitellopy')
        # TELLO_LOGGER.setLevel(logging.ERROR)

        cv2.namedWindow(TELLO_VIDEO_WINDOW_NAME, cv2.WINDOW_NORMAL)
        # cv2.resizeWindow(TELLO_VIDEO_WINDOW_NAME, 600, 600)
        cv2.namedWindow(KEYBOARD_CMD_WINDOW_NAME, cv2.WINDOW_NORMAL)

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
            if key_status == 0:
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
                frames = video_queue.get(block=False)
                frame = frames[0]
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

        cv2.destroyWindow("Tello Video")
        cv2.destroyWindow("Keyboard Cmds")
        cv2.destroyAllWindows()
        shutdown_gracefully()


if __name__ == '__main__':
    main()
