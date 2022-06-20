import time
from droneblocks.DroneBlocksTello import DroneBlocksTello
import logging
from droneblocks.tello_web import web_main
import threading


class DroneBlocksContextManager():

    def __init__(self, motor_on=False, start_tello_web=False, log_level=logging.ERROR, ignore_tello_talent_methods=False):
        self.motor_on = motor_on
        self.db_tello = None
        self.log_level = log_level
        self.start_tello_web = start_tello_web
        self.ignore_tello_talent_methods = ignore_tello_talent_methods

    def __enter__(self):
        self.db_tello = DroneBlocksTello(ignore_tello_talent_methods=self.ignore_tello_talent_methods)
        self.db_tello.LOGGER.setLevel(self.log_level)

        self.db_tello.connect()
        if self.motor_on:
            self.db_tello.turn_motor_on()

        if self.start_tello_web:
            sdk_version = None # the context manager does not determine the sdk version
            p2 = threading.Thread(target=web_main,
                                  args=(self.db_tello,None,8080,sdk_version))
            p2.setDaemon(True)
            p2.start()

        return self.db_tello

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"Exception Type: {exc_type}")
        if exc_val:
            print(f"Exception Value: {exc_val}")

        if exc_tb:
            print(f"Exception Traceback: {exc_tb}")

        if self.motor_on:
            try:
                self.db_tello.turn_motor_off()
            except:
                # guard against the motor off command failing
                # if this happens let the 'end' method handle it.
                print("WARN: turn motors off failed")


        try:
            self.db_tello.end()
        except:
            print("WARN: 'end' failed to complete")

if __name__ == '__main__':
    # example usage turning cooling motor on
    with DroneBlocksContextManager(motor_on=True) as db_tello:
        db_tello.set_top_led(r=255, g=0, b=0)
        time.sleep(2)
        db_tello.clear_everything()
