import logging
from bottle import post, route, run, request, template, TEMPLATE_PATH, view, static_file
import pkgutil
from droneblocks.DroneBlocksTello import DroneBlocksTello
import argparse
import time

web_root = None
web_stop_event = None

tello_model = 'Tello'

default_distance = 30
default_speed = 30
default_brightness = 32
# when the web app first comes up, set the brightness so the
# ui and the device match.  There does not see to be a way to get
# the current brightness level so we will set it
initial_brightness_set = False

# maximum number of seconds to allow a send_rc_control command
# to execute before sending a stop.  This is a safe guard to ensure
# the drone does not get too out of control
default_max_rc_control_time = 3
current_rc_control_time = 0

# when mission pad is enabled, this will update for the detected mission pad
mission_pad_enabled = False

# is the drone a Tello ( i.e. SDK 2.x ) or a Robomaster Tello ( i.e. SDK 3.x )
is_rmtt_drone = None

# command history
# keep a list of commands so we can make sure everything is being executed
command_history = []

tello_state = {
    'height': 30,
    'web_root': "",
    'battery_level': 'Unknown',
    'command_status_message': '',
    'command_success': True,
    'temp': 'Unknown',
    'flight_time': 'Unknown',
    'tello_model': tello_model,
    'fly_distance': default_distance,
    'flying_speed': default_speed,
    'command_history': [],
    'detected_mission_pad': -2,
    'mission_pad_enabled': mission_pad_enabled,
    'is_rmtt_drone': False,
    'display_brightness': default_brightness

}

tello_reference = None

command_status_message = ""
command_success = False

friendly_command_name = {
    'move-up': 'Fly Up',
    'move-down': 'Fly Down',
    'move-right': 'Fly Right',
    'move-left': 'Fly Left',
    'cw': 'Rotate Clockwise',
    'ccw': 'Rotate Counter Clockwise',
    'move-forward': 'Fly Forward',
    'move-back': 'Fly Backwards',
    'motor-on': 'Turn Motor On',
    'motor-off': 'Turn Motor Off',
    'takeoff': 'TakeOff',
    'flip-left': 'Flip Left',
    'flip-right': 'Flip Right',
    'flip-forward': 'Flip Forward',
    'flip-back': 'Flip Backward'
}


# TODO work on this max fly time guard
def _max_rc_control_time_guard():
    global current_rc_control_time
    while True:
        # every second make sure that are not running rc control too
        # long
        time.sleep(1)
        try:
            if tello_reference is not None and tello_reference.is_flying:
                if current_rc_control_time > 0:
                    if current_rc_control_time + default_max_rc_control_time > time.time():
                        tello_reference.send_rc_control(0, 0, 0, 0)
                        current_rc_control_time = 0
            else:
                # else we have no tello reference so sleep a long time
                # we should not ever be here if there is no reference
                # but lets be certain
                time.sleep(10)
        except:
            time.sleep(1)


def _execute_command(request):
    global command_status_message, command_success
    try:
        command = request.query.command or None
        print(command)
        command_history.append(command)

        if tello_reference and not tello_reference.is_flying:
            if command == 'takeoff':
                tello_reference.takeoff()
            elif command == 'motor-on':
                tello_reference.turn_motor_on()
            elif command == 'motor-off':
                tello_reference.turn_motor_off()
        else:
            if tello_reference and tello_reference.is_flying:
                if command == 'move-up':
                    tello_reference.move_up(default_distance)
                elif command == 'move-down':
                    tello_reference.move_down(default_distance)
                elif command == 'move-right':
                    tello_reference.move_right(default_distance)
                elif command == 'move-left':
                    tello_reference.move_left(default_distance)
                elif command == 'cw':
                    tello_reference.rotate_clockwise(90)
                elif command == 'ccw':
                    tello_reference.rotate_counter_clockwise(90)
                elif command == 'move-forward':
                    tello_reference.move_forward(default_distance)
                elif command == 'move-back':
                    tello_reference.move_back(default_distance)
                elif command == 'flip-left':
                    tello_reference.flip_left()
                elif command == 'flip-right':
                    tello_reference.flip_right()
                elif command == 'flip-forward':
                    tello_reference.flip_forward()
                elif command == 'flip-back':
                    tello_reference.flip_back()

        command = friendly_command_name[command]
        command_status_message = f'{command} completed'
        command_success = True
        print(command)
    except:
        command_success = False
        command_status_message = f'{command} Command Failed'

    return dict(command_success=command_success, command_status_message=command_status_message)


def _execute_rc_command(request):
    global command_status_message, command_success, current_rc_control_time
    try:
        command = request.query.command or None
        print(command)
        command_history.append(command)

        lr_vel = 0
        fb_vel = 0
        ud_vel = 0
        yv = 0
        if tello_reference and tello_reference.is_flying:
            if command == 'move-up':
                ud_vel = default_speed
            elif command == 'move-down':
                ud_vel = -default_speed
            elif command == 'move-right':
                lr_vel = default_speed
            elif command == 'move-left':
                lr_vel = -default_speed
            elif command == 'cw':
                yv = default_speed
            elif command == 'ccw':
                yv = -default_speed
            elif command == 'move-forward':
                fb_vel = default_speed
            elif command == 'move-back':
                fb_vel = -default_speed

            current_rc_control_time = time.time()
            tello_reference.send_rc_control(lr_vel, fb_vel, ud_vel, yv)

        command = friendly_command_name[command]
        command_status_message = f'{command}'
        command_success = True
        print(command)
    except:
        command_success = False
        command_status_message = f'{command} Command Failed'

    return dict(command_success=command_success, command_status_message=command_status_message)


def _refresh_tello_state():
    """
    {'mid': -2, 'x': -200, 'y': -200, 'z': -200, 'mpry': '0,0,0', 'pitch': 0,
    'roll': 0, 'yaw': 0, 'vgx': 0, 'vgy': 0, 'vgz': 0, 'templ': 66,
    'temph': 69, 'tof': 10, 'h': 0, 'bat': 12, 'baro': 256.7,
    'time': 0, 'agx': 10.0, 'agy': 0.0, 'agz': -999.0}

    :return:
    :rtype:
    """
    global mission_pad_enabled, is_rmtt_drone, initial_brightness_set
    if tello_reference:
        current_tello_state = tello_reference.get_current_state()
        tello_state['battery_level'] = current_tello_state['bat']
        tello_state['temp'] = int((current_tello_state['temph'] + current_tello_state['templ']) / 2)
        tello_state['flight_time'] = current_tello_state['time']
        tello_state['height'] = current_tello_state['h']
        tello_state['current_x'] = current_tello_state['x'] if 'x' in current_tello_state else -1
        tello_state['current_y'] = current_tello_state['y'] if 'y' in current_tello_state else -1
        tello_state['current_z'] = current_tello_state['z'] if 'z' in current_tello_state else -1
        tello_state['detected_mission_pad'] = current_tello_state['mid'] if 'mid' in current_tello_state else -2
        if tello_state['detected_mission_pad'] != -2:
            # thenç the mission pads must have been enabled outside the web api
            mission_pad_enabled = True

        if is_rmtt_drone is None:
            try:
                tt_version = int(tello_reference.query_sdk_version())
                print(tt_version)
                if  tt_version >= 30:
                    is_rmtt_drone = True
                    tello_state['is_rmtt_drone'] = is_rmtt_drone
                else:
                    is_rmtt_drone = False
            except:
                is_rmtt_drone = None # leave it as None, and we can check again


        if not initial_brightness_set:
            initial_brightness_set = True
            tello_reference.set_display_brightness(default_brightness)

    tello_state['fly_distance'] = default_distance
    tello_state['tello_model'] = tello_model
    tello_state['command_status_message'] = command_status_message
    tello_state['command_success'] = command_success
    tello_state['flying_speed'] = default_speed
    tello_state['command_history'] = command_history
    tello_state['mission_pad_enabled'] = mission_pad_enabled



# route will retrieve static assets
@route('/static/<filepath:path>')
def server_static(filepath):
    path = f"{web_root}/static/"
    print(path)
    return static_file(filepath, root=path)


@route('/debug/command-history')
def db_command_history():
    print("-------------  Start Commands ----------")
    for c in command_history:
        print(c)
    print("-------------  End Commands ----------")


@route('/')
@view('index')
def index():
    try:
        _refresh_tello_state()
    except:
        pass
    return dict(tello_state=tello_state)


@route('/status-update')
def status_update():
    try:
        _refresh_tello_state()
    except:
        pass
    return dict(tello_state=tello_state)


@post('/update-brightness')
def update_brightness():
    global default_brightness
    global command_status_message, command_success

    try:
        if request.json:
            print(request.json)
            if 'brightnessvalue' in request.json:
                default_brightness = int(request.json['brightnessvalue'])
                if tello_reference:
                    tello_reference.set_display_brightness(default_brightness)

        command_status_message = "Display Brightness Updated"
        command_success = True
    except:
        command_status_message = "Could not update default Display Brightness"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)


@post('/update-flying-values')
def update_flying_values():
    global default_speed, default_distance
    global command_status_message, command_success

    try:
        if request.json:
            print(request.json)
            if 'speedvalue' in request.json:
                default_speed = int(request.json['speedvalue'])
            if 'distancevalue' in request.forms:
                default_distance = int(request.forms['distancevalue'])

        command_status_message = "Flying Values Updated"
        command_success = True
    except:
        command_status_message = "Could not update default Flying values"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)


@post('/set-top-led')
def set_top_led():
    global default_distance
    global command_status_message, command_success
    print("set top led")
    try:
        if request.json:
            r = int(request.json['red'])
            g = int(request.json['green'])
            b = int(request.json['blue'])
            r2 = int(request.json['red2'])
            g2 = int(request.json['green2'])
            b2 = int(request.json['blue2'])
            mode = request.json['mode']
            freq = int(request.json['freq'])

            if tello_reference:
                if mode == 'color':
                    tello_reference.set_top_led(r=r, g=g, b=b)
                elif mode == 'pulse':
                    tello_reference.pulse_top_led(r=r, g=g, b=b, freq=freq/10)
                elif mode == 'flash':
                    tello_reference.alternate_top_led(r1=r, g1=g, b1=b, r2=r2, g2=g2, b2=b2, freq=freq/10)
                else:
                    print(f"Invalid Top Led Mode: {mode}")
                    tello_reference.set_top_led(r=r, g=g, b=b)
    except:
        command_status_message = "Could not set top led"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)


@post('/display-image')
def display_image():
    global default_distance
    global command_status_message, command_success
    print("display image")
    try:
        if request.json:
            image_string = request.json['image_string']
            image_index = int(request.json['image_index'])
            display_color = request.json['display_color']
            if tello_reference:
                rtn = ''
                if image_index == 1:
                    print(image_string)
                    rtn = tello_reference.display_image(image_string)
                elif image_index == 2:
                    rtn = tello_reference.display_heart(display_color=display_color)
                elif image_index == 3:
                    rtn = tello_reference.display_smile(display_color=display_color)
                elif image_index == 4:
                    rtn = tello_reference.display_sad(display_color=display_color)
                elif image_index == 5:
                    rtn = tello_reference.clear_display()

                print(f"display image rtn: {rtn}")

    except Exception as exc:
        print(f"Display Image Exception: {exc}")
        command_status_message = "Could not display image string"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)


@post('/scroll-text')
def scroll_text():
    global default_distance
    global command_status_message, command_success
    print("scroll text")
    try:
        if request.json:
            scroll_string = request.json['scroll_text']
            scroll_dir = int(request.json['scroll_dir'])
            display_color = request.json['display_color']

            if tello_reference:
                if scroll_dir == 1:
                    tello_reference.scroll_string(scroll_string, scroll_dir=DroneBlocksTello.LEFT, display_color=display_color)
                elif scroll_dir == 2:
                    tello_reference.scroll_string(scroll_string, scroll_dir=DroneBlocksTello.UP, display_color=display_color)
    except:
        command_status_message = "Could not display image string"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)


@route('/execute')
def execute():
    return _execute_command(request)


@route('/execute-rc')
def execute_rc():
    return _execute_rc_command(request)


@route('/stop-flying')
def stop_flying():
    global command_status_message, command_success, current_rc_control_time
    try:
        print("stop flying")
        if tello_reference is not None and tello_reference.is_flying:
            current_rc_control_time = 0
            print("send stop command to tello.")
            tello_reference.send_rc_control(0, 0, 0, 0)
            # I want to be really sure if we need to stop we stop
            time.sleep(1)
            tello_reference.send_rc_control(0, 0, 0, 0)

        command_history.append('stop-flying')
        command_status_message = 'Hover'
        command_success = True
    except Exception as exc:
        time.sleep(1)
        try:
            tello_reference.send_rc_control(0, 0, 0, 0)
            command_history.append('stop-flying')
        except:
            # oh well... god speed....
            pass
        command_success = False
        command_status_message = 'Hover Failed'
        print(f"stop event exception: {exc} ")

    return dict(command_success=command_success, command_status_message=command_status_message)

@route('/enable-mission-pads')
def enable_mission_pads():
    global command_status_message, command_success, mission_pad_enabled
    try:
        print("enable mission pads")
        if tello_reference is not None:
            tello_reference.enable_mission_pads()  # default is direction 0, or down
            tello_reference.set_mission_pad_detection_direction(0)
            mission_pad_enabled = True
            command_history.append('enable mission pads')
        command_status_message = 'Enable Mission Pads'
        command_success = True
    except Exception as exc:
        command_success = False
        command_status_message = 'Enable Mission Pads Command Failed'
        print(f"exception: {exc} ")

    return dict(command_success=command_success, command_status_message=command_status_message)

@route('/disable-mission-pads')
def disable_mission_pads():
    global command_status_message, command_success, mission_pad_enabled
    try:
        print("enable mission pads")
        if tello_reference is not None:
            tello_reference.disable_mission_pads()  # default is direction 0, or down
            command_history.append('disable mission pads')
            mission_pad_enabled = False
        command_status_message = 'Disable Mission Pads'
        command_success = True
    except Exception as exc:
        command_success = False
        command_status_message = 'Disable Mission Pads Command Failed'
        print(f"exception: {exc} ")

    return dict(command_success=command_success, command_status_message=command_status_message)

@route('/land')
# @view('landing')
def land():
    global command_status_message, command_success
    try:
        print("LAND")
        if tello_reference is not None and tello_reference.is_flying:
            tello_reference.land()
            command_history.append('land')
        if web_stop_event is not None:
            print("web stop event set.....")
            web_stop_event.set()
        command_status_message = 'Land Initiated'
        command_success = True
    except Exception as exc:
        command_success = False
        command_status_message = 'Land Command Failed'
        print(f"stop event exception: {exc} ")
        if web_stop_event is not None:
            print("web stop event set.....")
            web_stop_event.set()

    return dict(command_success=command_success, command_status_message=command_status_message)


def web_main(tello, stop_event=None, port=8080, sdk_version=20):
    global tello_reference, web_root, web_stop_event, is_rmtt_drone
    web_stop_event = stop_event

    if sdk_version is not None:
        is_rmtt_drone = True if sdk_version >= 30 else False
        print(f"Starting Tello Web Server.....SDK: {sdk_version}, {is_rmtt_drone}")
    else:
        print(f"Starting Tello Web Server.....")


    tello_reference = tello
    droneblocks_package = pkgutil.get_loader("droneblocks")
    droneblocks_init_file_path = droneblocks_package.get_filename()
    # '/Users/patrickryan/Development/junk-projects/junk11/venv/lib/python3.8/site-packages/droneblocks/__init__.py'
    directory = droneblocks_init_file_path.replace("__init__.py", "web")
    tello_state['directory'] = directory
    print(directory)
    web_root = directory

    # start the thread that will monitor for long running rc_control commands
    # if tello is not None:
    #     p2 = threading.Thread(target=_max_rc_control_time_guard)
    #     p2.setDaemon(True)
    #     p2.start()

    TEMPLATE_PATH.append(directory)
    run(host='localhost', port=port)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action='store_true', help="Do not instantiate Tello reference")
    ap.add_argument("--web-port", required=False, default=8080, type=int,
                    help="Port to start web server on.  Default: 8080")

    args = vars(ap.parse_args())

    dry_run = args['dry_run']
    port = args['web_port']
    if dry_run:
        web_main(None, stop_event=None, port=port)
    else:
        try:
            db_tello = DroneBlocksTello()
            db_tello.LOGGER.setLevel(logging.ERROR)

            db_tello.connect()
            time.sleep(0.5)
            try:
                sdk_version = int(db_tello.query_sdk_version())
                print(f"SDK Version: {sdk_version}")
                print(f"Hardware: {db_tello.query_hardware()}")

            except Exception as exc:
                # Assume None
                sdk_version = None

            web_main(db_tello, stop_event=None, port=port, sdk_version=sdk_version)
        except Exception as exc:
            print("Exception in tello web: ")
            print(exc)
