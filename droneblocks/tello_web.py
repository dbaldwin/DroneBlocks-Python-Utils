from bottle import route, run, template, TEMPLATE_PATH, view, static_file
import pkgutil
from droneblocks.DroneBlocksContextManager import DroneBlocksContextManager
import argparse
import time

web_root = None
web_stop_event = None

tello_state = {
    'height': 30,
    'web_root': "",
    'battery_level': 'Unknown',
    'command_status_message': '',
    'command_success': True

}

tello_reference = None

command_status_message = ""
command_success = False

def _refresh_tello_state():
    if tello_reference:
        bat = tello_reference.get_battery()
        tello_state['battery_level'] = bat

        temp = tello_reference.get_temperature()
        tello_state['temp'] = temp

    tello_state['command_status_message'] = command_status_message
    tello_state['command_success'] = command_success



@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=f"{web_root}/images")

@route('/')
@view('index')
def index():
    try:
        _refresh_tello_state()
    except:
        pass
    return dict(tello_state=tello_state)

@route('/move-up')
@view('index')
def move_up():
    global command_status_message, command_success
    try:
        if tello_reference:
            tello_reference.move_up(30)
        command_status_message='MoveUp completed'
        command_success = True
        print("Move Up")
    except:
        command_success = False
        command_status_message='MoveUp Command Failed'

    _refresh_tello_state()
    return dict(tello_state=tello_state)

@route('/move-down')
@view('index')
def move_down():
    global command_status_message,command_success
    try:
        if tello_reference:
            tello_reference.move_down(30)
        command_status_message='MoveDown completed'
        command_success = True
        print("Move Down")
    except:
        command_success = False
        command_status_message='MoveDown Command Failed'

    _refresh_tello_state()
    return dict(tello_state=tello_state)

@route('/motor-on')
@view('index')
def motor_on():
    global command_status_message,command_success
    try:
        if tello_reference:
            tello_reference.turn_motor_on()
        command_status_message='Motor On completed'
        command_success = True
        print("Motor On")
    except Exception as exc:
        command_success = False
        command_status_message='Motor On Command Failed'
        print(exc)

    _refresh_tello_state()
    return dict(tello_state=tello_state)

@route('/motor-off')
@view('index')
def motor_off():
    global command_status_message,command_success
    try:
        if tello_reference:
            tello_reference.turn_motor_off()
        command_status_message='Motor Off completed'
        command_success = True
        print("Motor Off")
    except:
        command_success = False
        command_status_message='Motor Off Command Failed'

    _refresh_tello_state()
    return dict(tello_state=tello_state)


@route('/land')
@view('landing')
def land():
    global command_status_message,command_success
    try:
        if web_stop_event is not None:
            print("stop event set")
            if tello_reference is not None and tello_reference.is_flying:
                tello_reference.land()
            web_stop_event.set()
            command_status_message = 'Land Initiated'
            command_success = True
    except Exception as exc:
        command_success = False
        command_status_message='Land Command Failed'
        print(f"stop event exception: {exc} ")

    _refresh_tello_state()
    return

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
    dry_run = True
    if dry_run:
        web_main(None)
    else:
        with DroneBlocksContextManager() as db_tello:
            web_main(db_tello)