from bottle import post, route, run, request, template, TEMPLATE_PATH, view, static_file
import pkgutil
from droneblocks.DroneBlocksContextManager import DroneBlocksContextManager
import argparse
import time

web_root = None
web_stop_event = None

tello_model = 'Tello'

default_distance=30

tello_state = {
    'height': 30,
    'web_root': "",
    'battery_level': 'Unknown',
    'command_status_message': '',
    'command_success': True,
    'temp': 'Unknown',
    'flight_time': 'Unknown',
    'tello_model': tello_model,
    'fly_distance': default_distance

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
}

def _execute_command(request):
    global command_status_message, command_success
    try:
        command = request.query.command or None
        print(command)
        if tello_reference:
            if command == 'move-up':
                tello_reference.move_up(default_distance)
            elif command == 'move-down':
                tello_reference.move_down(default_distance)
            elif command == 'move-right':
                tello_reference.move_right(default_distance)
            elif command == 'move-left':
                tello_reference.move_left(default_distance)
            elif command == 'takeoff':
                tello_reference.takeoff()
            elif command == 'cw':
                tello_reference.rotate_clockwise(90)
            elif command == 'ccw':
                tello_reference.rotate_counter_clockwise(90)
            elif command == 'move-forward':
                tello_reference.move_forward(default_distance)
            elif command == 'move-back':
                tello_reference.move_back(default_distance)
            elif command == 'motor-on':
                tello_reference.turn_motor_on()
            elif command == 'motor-off':
                tello_reference.turn_motor_off()

        command = friendly_command_name[command]
        command_status_message=f'{command} completed'
        command_success = True
        print(command)
    except:
        command_success = False
        command_status_message=f'{command} Command Failed'

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
    if tello_reference:
        current_tello_state = tello_reference.get_current_state()
        if tello_state:
            tello_state['battery_level'] = current_tello_state['bat']
            tello_state['temp'] = int((current_tello_state['temph']+current_tello_state['templ'])/2)
            tello_state['flight_time'] = current_tello_state['time']
            tello_state['height'] = current_tello_state['h']

    tello_state['fly_distance'] = default_distance
    tello_state['tello_model'] = tello_model
    tello_state['command_status_message'] = command_status_message
    tello_state['command_success'] = command_success


# route will retrieve static assets
@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=f"{web_root}/static/")

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

@post('/update-distance' )
@view('index')
def update_distance():
    global default_distance
    global command_status_message,command_success

    try:
        if request.forms:
            if 'distancevalue' in request.forms:
                default_distance = int(request.forms['distancevalue'])
        _refresh_tello_state()
    except:
        command_status_message = "Could not update default Flying distance"
        command_success = False

    return dict(tello_state=tello_state)

@post('/set-top-led')
def set_top_led():
    global default_distance
    global command_status_message,command_success
    print("set top led")
    try:
        if request.json:
            r = int(request.json['red'])
            g = int(request.json['green'])
            b = int(request.json['blue'])
            print(r,g,b)
            if tello_reference:
                tello_reference.set_top_led(r=r, g=g, b=b)
    except:
        command_status_message = "Could not set top led"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)

@post('/display-image')
def display_image():
    global default_distance
    global command_status_message,command_success
    print("display image")
    try:
        if request.json:
            image_string = request.json['image_string']
            if tello_reference:
                print(image_string)
                tello_reference.display_image(image_string)
    except:
        command_status_message = "Could not display image string"
        command_success = False

    return dict(command_success=command_success, command_status_message=command_status_message)

@route('/toggle-model')
@view('index')
def toggle_model():
    global tello_model
    if tello_model == 'Tello':
        tello_model = 'Tello Talent'
    else:
        tello_model = 'Tello'

    _refresh_tello_state()
    return dict(tello_state=tello_state)


@route('/execute')
def execute():
    return _execute_command(request)

@route('/land')
# @view('landing')
def land():
    global command_status_message,command_success
    try:
        print("stop event set")
        if tello_reference is not None and tello_reference.is_flying:
            tello_reference.land()
        if web_stop_event is not None:
            web_stop_event.set()
        command_status_message = 'Land Initiated'
        command_success = True
    except Exception as exc:
        command_success = False
        command_status_message='Land Command Failed'
        print(f"stop event exception: {exc} ")

    return dict(command_success=command_success, command_status_message=command_status_message)

def web_main(tello, stop_event=None):
    global tello_reference, web_root, web_stop_event
    web_stop_event = stop_event

    print("Starting Tello Web Server.....")

    tello_reference = tello
    droneblocks_package = pkgutil.get_loader("droneblocks")
    droneblocks_init_file_path = droneblocks_package.get_filename()
    # '/Users/patrickryan/Development/junk-projects/junk11/venv/lib/python3.8/site-packages/droneblocks/__init__.py'
    directory = droneblocks_init_file_path.replace("__init__.py", "web")
    tello_state['directory'] = directory
    print(directory)
    web_root = directory

    TEMPLATE_PATH.append(directory)
    run(host='localhost', port=8080)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action='store_true', help="Do not instantiate Tello reference")

    args = vars(ap.parse_args())

    dry_run = args['dry_run']
    if dry_run:
        web_main(None)
    else:
        with DroneBlocksContextManager() as db_tello:
            web_main(db_tello)