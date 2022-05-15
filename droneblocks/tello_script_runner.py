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
from droneblocks import tello_keyboard_mapper as keymapper
from droneblocksutils.exceptions import LandException
from droneblocks.tello_web import web_main

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()

# Reference to the global Tello instance
tello = None

# If video sim is selected, this is the WebCam video stream
local_video_stream = None

# Global flag used to communiate is the user_script requested to land
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

TELLO_VIDEO_WINDOW_NAME = "User Tello Video"
ORIGINAL_VIDEO_WINDOW_NAME = "Raw Tello Video"
# TODO deprecate the keyboard cmd window
# KEYBOARD_CMD_WINDOW_NAME = "Keyboard Cmds"

ui_elements = []

# Global value holding the last key pressed.
# value will be key from the tello_keyboard_mapper.py file
g_key_press_value = None

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

# global reference to the stop event.  Used in
# signal handler for keyboard interrupts to
# alert script management to stop
g_stop_event = None


# function to handle keyboard interrupt
def signal_handler(sig, frame):
    shutdown_gracefully()

    sys.exit(-1)


def shutdown_gracefully():
    print("Tello Script Runner Shutdown.......")

    try:
        if g_stop_event is not None:
            g_stop_event.set()
            time.sleep(2)  # give the system a couple of seconds to respond
    except:
        pass

    if tello:
        try:
            print("Stop all Tello operations")
            tello.end()
            tello.turn_motor_off()
        except:
            pass

        try:
            # I tried to get the version but did not find a way
            # to do so.  Instead just call clear_everything and if
            # its a tello a exception will be thrown and we will
            # just eat it
            tello.clear_everything()
        except:
            pass

    if local_video_stream:
        try:
            print("Stop local webcam")
            local_video_stream.stop()
        except:
            pass

    print("Tello Script Runner Shutdown.......Complete")


tello_image = None


def _get_video_frame(frame_read, vid_sim):
    global IMAGE_HEIGHT
    f = None
    try:
        if frame_read:
            f = frame_read.frame
        elif vid_sim and local_video_stream:
            f = local_video_stream.read()

        if f is not None:
            f = imutils.resize(f, width=IMAGE_WIDTH)
            IMAGE_HEIGHT = f.shape[0]

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

            init_method(tello, params)

        frame_read = None
        if tello and video_queue:
            # tello.streamon()
            frame_read = tello.get_frame_read()

        if fly:
            tello.takeoff()
            # send command to go no where
            tello.send_rc_control(0, 0, 0, 0)

        if tello_video_sim and local_video_stream is None:
            local_video_stream = VideoStream(src=0).start()
            time.sleep(2)

        params = {}
        params['fly_flag'] = fly
        while not stop_event.isSet():
            if display_tello_video:
                frame = _get_video_frame(frame_read, tello_video_sim)
            else:
                frame = None
            params['last_key_pressed'] = g_key_press_value

            # if we have no frame, just call handler_method and re-loop
            # no need to process video frames
            if frame is None:
                # LOGGER.debug("Failed to read video frame")
                if handler_method:
                    handler_method(tello, frame, params)
                continue

            # if you get here, then you had a video frame
            # to process
            original_frame = frame.copy()

            if handler_method:
                rtn_frame = handler_method(tello, frame, params)
                if rtn_frame is not None:
                    frame = rtn_frame

            # send frame to other processes
            if video_queue and video_event.is_set():
                try:
                    if time.time() - last_show_video_queue_put_time > show_video_per_second:
                        last_show_video_queue_put_time = time.time()
                        video_queue.put_nowait([frame, original_frame])
                except:
                    pass

    except LandException:
        print(f"User script requested landing")
        user_script_requested_land = True
    except ModuleNotFoundError as exc:
        LOGGER.error(f"Could not find specified handler script: {exc.msg}")

    except Exception as exc:
        LOGGER.error(f"Exiting Tello Process with exception: {exc}")
        traceback.print_exc()
    finally:
        # then the user has requested that we land and we should not process this thread
        # any longer.
        # to be safe... stop all movement
        if handler_method is not None:
            if fly:
                tello.send_rc_control(0, 0, 0, 0)

            if stop_method:
                params = {}
                params['fly_flag'] = fly
                params['last_key_pressed'] = g_key_press_value

                try:
                    stop_method(tello, params)
                except:
                    # if the stop method throws an exception, make sure the rest of the
                    # tello shutdown still continues
                    pass

        if stop_event is not None:
            stop_event.set()

    LOGGER.info("Leaving User Script Processing Thread.....")


def main():
    global speed
    global tello
    global g_stop_event

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    ap = argparse.ArgumentParser()
    ap.add_argument("--test-install", action='store_true', help="Test the command can run, then exit and do nothing. ")
    ap.add_argument("--display-video", action='store_true', help="Display Drone video using OpenCV.")

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
    ap.add_argument("--tello-web", action='store_true',
                    help="Default: False. Start the Tello control web application at url:  http://localhost:8080")
    ap.add_argument("--web-port", required=False, default=8080, type=int,
                    help="Port to start web server on.  Default: 8080")

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

    web_port = args['web_port']
    start_tello_web = args['tello_web']
    show_original_frame = args['show_original_video']
    fly = args['fly']
    LOGGER.debug(f"Fly: {fly}")
    display_video = args['display_video']
    handler_file = args['handler']
    if handler_file:
        handler_file = handler_file.replace(".py", "")
        handler_module = importlib.import_module(handler_file)
        if handler_module is None:
            raise f"Could not locate handler file: {handler_file}"

    tello_video_sim = args['tello_video_sim']

    # if the user selected tello_video_sim, force the display video flag
    # but also do not show the raw/original Tello video, because we dont have
    # that in simulator mode
    if tello_video_sim:
        display_video = True
        show_original_frame = False

    # video queue to hold the frames from the Tello
    video_queue = None
    if display_video:
        video_queue = queue.Queue(maxsize=MAX_VIDEO_Q_DEPTH)

    try:
        TELLO_LOGGER = logging.getLogger('djitellopy')
        TELLO_LOGGER.setLevel(logging.ERROR)

        # TODO deprecate the keyboard cmd window
        # cv2.namedWindow(KEYBOARD_CMD_WINDOW_NAME, cv2.WINDOW_NORMAL)
        # cv2.setMouseCallback(KEYBOARD_CMD_WINDOW_NAME, _mouse_events)

        if display_video:
            cv2.namedWindow(TELLO_VIDEO_WINDOW_NAME, cv2.WINDOW_NORMAL)

        if show_original_frame:
            cv2.namedWindow(ORIGINAL_VIDEO_WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.moveWindow(ORIGINAL_VIDEO_WINDOW_NAME, 200, 100)
            # cv2.moveWindow(KEYBOARD_CMD_WINDOW_NAME, 450, 410)
            if display_video:
                cv2.moveWindow(TELLO_VIDEO_WINDOW_NAME, 200 + IMAGE_WIDTH, 100)
        else:
            if display_video:
                cv2.moveWindow(TELLO_VIDEO_WINDOW_NAME, 200, 100)
            # cv2.moveWindow(KEYBOARD_CMD_WINDOW_NAME, 200 + IMAGE_WIDTH, 100)

        # -----------------------  Initialize the Tello ----------------------
        tello = DroneBlocksTello()
        tello.connect()
        speed = tello.get_speed()
        time.sleep(0.5)
        try:
            sdk_version = int(tello.query_sdk_version())
        except Exception as exc:
            # assume regular tello
            sdk_version=20

        # If the user wants to see the Tello video from the handler
        # or the raw video from the Tello AND we are not simulating
        # the video with the webcam, then we can turn the video
        # streamon
        if (display_video or show_original_frame) and not tello_video_sim:
            tello.streamon()

        # -----------------------  DONE Initialize the Tello ----------------------

        # ---------------------------- Initialize background processing thread and script runner --------
        # if the user did not specify a handler function, do not create the background thread
        stop_event = threading.Event()
        g_stop_event = stop_event
        if handler_file is not None:
            ready_to_show_video_event = threading.Event()
            p1 = threading.Thread(target=process_tello_video_feed,
                                  args=(
                                      handler_file, video_queue, stop_event, ready_to_show_video_event, fly,
                                      tello_video_sim,
                                      display_video,))
            p1.setDaemon(True)
            p1.start()
        # ---------------------------- DONE Initialize background processing thread and script runner --------

        # -----------------------------------------------------------
        # ---------------------------- Initialize Web Server --------
        # -----------------------------------------------------------
        if start_tello_web:
            print(f"Starting Tello Web with SDK Version: {sdk_version}")

            p2 = threading.Thread(target=web_main,
                                  args=(tello, stop_event, web_port, sdk_version
                                        ))
            p2.setDaemon(True)
            p2.start()
        # -----------------------------------------------------------
        # ---------------------------- END Initialize Web Server --------
        # -----------------------------------------------------------

        # wait one second for the process thread to kick in
        time.sleep(1)
        frame_read = None
        # -----------------------------------------------------------
        # ---------------------------- PROCESSING LOOP --------------
        # -----------------------------------------------------------
        while True:
            # this can become a very tight loop
            # there are use cases where you might not want to do anything
            # but run the tello-web application.
            # to provide some breathing room, sleep this loop for a short time
            time.sleep(0.2)
            if frame_read is None and tello is not None and show_original_frame:
                try:
                    frame_read = tello.get_frame_read()
                except:
                    frame_read = None

            # key_status = _exception_safe_process_keyboard_commands(tello, fly)
            if user_script_requested_land == True:
                print("User Script Requested Land")
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

            if stop_event.isSet():
                print("Stop Event Is Set")
                ready_to_show_video_event.clear()
                # wait up to n seconds for the handler thread to exit
                # the handler thread will clear the stop_event when it
                # exits
                time.sleep(3)
                break

            ready_to_show_video_event.set()
            try:
                # LOGGER.debug(f"Q size: {video_queue.qsize()}")
                if video_queue is not None:
                    # frames[0] - frame returned from the script handler
                    # frames[1] - original frame read from tello/webcam
                    frames = video_queue.get(block=False)
                    frame = frames[0]
                else:
                    frame = None
                    frames = []
            except:
                frame = None
                frames = []

            if frame_read is not None and show_original_frame:
                # then we have created a frame reader
                # and the user wants to see the original video feed
                # so try to read a frame from the tello and just show that
                try:
                    orig_frame = _get_video_frame(frame_read, tello_video_sim)
                    cv2.imshow(ORIGINAL_VIDEO_WINDOW_NAME, orig_frame)
                    cv2.waitKey(1)
                except:
                    pass

            # check for video feed
            if display_video and frame is not None:
                try:
                    # display the frame to the screen
                    cv2.imshow(TELLO_VIDEO_WINDOW_NAME, frame)
                    # frames[1] was the frame before sending to user handler
                    # but instead of showing this frame, I am going to show the
                    # realtime video feed from the tello above.
                    # the only time I can think this might matter is if the user scripts
                    # takes a really long time to run, and the frame that the user script
                    # updates is really different than the current frame.
                    # if show_original_frame:
                    #     cv2.imshow(ORIGINAL_VIDEO_WINDOW_NAME, frames[1])
                    cv2.waitKey(1)
                except Exception as exc:
                    LOGGER.error(f"Display Queue Error: {exc}")

            # Give the user a chance to exit the script
            # if the user presses q or ESC set the stop_event and exit
            key_value = cv2.waitKey(2) & 0xFF
            if key_value == ord('q') or key_value == 27:
                stop_event.set()



    finally:
        LOGGER.debug("Complete...")
        if display_video:
            cv2.destroyWindow(TELLO_VIDEO_WINDOW_NAME)
        if show_original_frame:
            cv2.destroyWindow(ORIGINAL_VIDEO_WINDOW_NAME)
        # cv2.destroyWindow(KEYBOARD_CMD_WINDOW_NAME)
        cv2.destroyAllWindows()
        shutdown_gracefully()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print("An error occurred while trying to execute the tello script runner")
        print(f"Exception: {exc}")
