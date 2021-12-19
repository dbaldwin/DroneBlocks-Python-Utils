import time
from droneblocks.DroneBlocksTello import DroneBlocksTello
import logging
from droneblocks.tello_web import web_main
import threading


class DroneBlocksContextManager():

    def __init__(self, motor_on=False, start_tello_web=False, log_level=logging.ERROR):
        self.motor_on = motor_on
        self.db_tello = None
        self.log_level = log_level
        self.start_tello_web = start_tello_web

    def __enter__(self):
        self.db_tello = DroneBlocksTello()
        self.db_tello.LOGGER.setLevel(self.log_level)

        self.db_tello.connect()
        if self.motor_on:
            self.db_tello.turn_motor_on()

        if self.start_tello_web:
            p2 = threading.Thread(target=web_main,
                                  args=(self.db_tello,))
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
            self.db_tello.turn_motor_off()

        self.db_tello.end()


if __name__ == '__main__':
    # example usage turning cooling motor on
    with DroneBlocksContextManager(motor_on=True) as db_tello:
        db_tello.set_top_led(r=255, g=0, b=0)
        time.sleep(2)
        db_tello.clear_everything()
