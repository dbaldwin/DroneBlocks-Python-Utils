from djitellopy import Tello


class DroneBlocksTello(Tello):
    UP = 'u'
    LEFT = 'l'
    DOWN = 'd'
    RIGHT = 'r'

    PURPLE = 'p'
    BLUE = 'b'
    RED = 'r'

    sad_image = "0000000000b00b0000000000000bb000000bb000000000000bbbbbb0b000000b"
    smile_image = "0000000000b00b0000000000000bb000b00bb00bb000000b0b0000b000bbbb00"
    up_arrow_image = "000bb00000bbbb000bbbbbb0000bb000000bb000000bb000000bb00000000000"
    down_arrow_image = "00000000000bb000000bb000000bb000000bb0000bbbbbb000bbbb00000bb000"
    left_arrow_image = "0000000000b000000bb00000bbbbbbb0bbbbbbb00bb0000000b0000000000000"
    right_arrow_image = "0000000000000b0000000bb00bbbbbbb0bbbbbbb00000bb000000b0000000000"
    question_mark = "000bb00000b00b0000b00b0000000b000000b0000000b000000000000000b000"

    def __init__(self):
        super().__init__()
        self.last_speed_value = 0

    @classmethod
    def get_blank_display_matrix(cls):
        return "0000000000000000000000000000000000000000000000000000000000000000"

    def _display_pattern(self, flattened_matrix: str) -> str:
        return self.send_command_with_return(f"EXT mled g {flattened_matrix}")

    def get_speed(self) -> int:
        """Query speed setting (cm/s)
        This method is in the DroneBlocksTello class because the Tello class
        uses a different command that no longer seems supported.
        Returns:
            int: 1-100
        """
        speed_value = self.send_read_command('speed?')
        try:
            speed_value = int(float(speed_value))
            self.last_speed_value = speed_value
        except:
            speed_value = self.last_speed_value

        return speed_value

    def pulse_top_led(self, r: int, g: int, b: int, freq: float = 2.5) -> str:
        """
        The top LED displays the pulse effect according to the max pulse brightness (r, g, b) and pulse frequency t.
        The cycle from dimmest to brightest to dimmest again is counted as one pulse.
            r, g, b: 0~255
            freq: 0.1-2.5Hz
        :return: OK/ERROR
        """
        freq = max(min(freq, 2.5), 0.1)

        if 0.1 <= freq <= 2.5 and 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            return self.send_command_with_return(f"EXT led br {freq} {r} {g} {b}")
        else:
            return f"ERROR: Invalid input parameters"

    def set_top_led(self, r: int, g: int, b: int) -> str:
        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            return self.send_command_with_return(f"EXT led {r} {g} {b}")
        else:
            return "error"

    def alternate_top_led(self, r1: int, g1: int, b1: int, r2: int = 0, g2: int = 0, b2: int = 0,
                          freq: float = 2.5) -> str:
        freq = max(min(freq, 2.5), 0.1)

        return self.send_command_with_return(f"EXT led bl {freq} {r1} {g1} {b1} {r2} {g2} {b2}")

    def change_image_color(self, image_string: str, from_color: str, to_color: str) -> str:
        new_str = image_string.replace(from_color, to_color)
        return new_str

    def display_image(self, display_string: str) -> str:
        return self._display_pattern(display_string)

    def clear_display(self) -> str:
        display = DroneBlocksTello.get_blank_display_matrix()
        return self._display_pattern(display)

    def set_display_brightness(self, level: int) -> str:
        if 0 <= level <= 255:
            return self.send_command_with_return(f"EXT mled sl {level}")
        return 'Invalid level value'

    def clear_everything(self):
        self.clear_display()
        self.set_top_led(r=0, g=0, b=0)

    def display_heart(self, display_color: str = PURPLE) -> str:
        return self.send_command_with_return(f"EXT mled s {display_color} heart")

    def display_character(self, single_character: str, display_color: str = PURPLE) -> str:
        return self.send_command_with_return(f"EXT mled s {display_color} {single_character}")

    def display_smile(self, display_color: str = PURPLE) -> str:
        smile = self.change_image_color(DroneBlocksTello.smile_image, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(smile)

    def display_sad(self, display_color: str = PURPLE) -> str:
        sad = self.change_image_color(DroneBlocksTello.sad_image, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(sad)

    def display_up_arrow(self, display_color: str = BLUE) -> str:
        up = self.change_image_color(DroneBlocksTello.up_arrow_image, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(up)

    def display_down_arrow(self, display_color: str = BLUE) -> str:
        down = self.change_image_color(DroneBlocksTello.down_arrow_image, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(down)

    def display_left_arrow(self, display_color: str = BLUE) -> str:
        left = self.change_image_color(DroneBlocksTello.left_arrow_image, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(left)

    def display_right_arrow(self, display_color: str = BLUE) -> str:
        right = self.change_image_color(DroneBlocksTello.right_arrow_image, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(right)

    def display_question_mark(self, display_color: str = BLUE) -> str:
        question = self.change_image_color(DroneBlocksTello.question_mark, DroneBlocksTello.BLUE, display_color)
        return self._display_pattern(question)

    def scroll_image(self, image_string: str, scroll_dir: str, rate: float = 2.5) -> str:
        return self.send_command_with_return(f"EXT mled {scroll_dir} g {rate} {image_string}")

    def scroll_string(self, message: str, scroll_dir: str = LEFT, display_color: str = PURPLE,
                      rate: float = 2.5) -> str:
        rate = max(min(rate, 2.5), 0.1)
        if len(message) > 70:
            message = message[0:70]

        return self.send_command_with_return(f"EXT mled {scroll_dir} {display_color} {rate} {message}")

    # it appears that the EXT tof? command returns: unknown command: keepalive
    # along with the value.  Seems like a tello bug.
    # to compensate for this bug I am going to return the last known good
    # value that was read from the tello.
    def get_controller_tof(self) -> str:
        global last_known_good_tof
        mm_value = self.send_command_with_return("EXT tof?")
        if mm_value is not None and mm_value == "unknown command: keepalive":
            mm_value = self.send_command_with_return("EXT tof?")
        # 10 mm = 1 cm
        print(f"send_command_with_return Rtn Value: {mm_value}")

        try:
            mm_value = mm_value.replace("tof ", '')
            cm_value = int(int(mm_value)/10)
        except:
            cm_value = -1

        return cm_value

    # ----------------  fly_xyz api to match the droneblocks simulator tello
    def _inches_to_cm(self, inch_value):
        return inch_value * 2.54

    def fly_up(self, x, units):
        if units == 'in':
            x = self._inches_to_cm(x)
        self.move_up(x)

    def fly_down(self, x, units):
        if units == 'in':
            x = self._inches_to_cm(x)
        self.move_down(x)

    def fly_left(self, x, units):
        if units == 'in':
            x = self._inches_to_cm(x)
        self.move_left(x)

    def fly_right(self, x, units):
        if units == 'in':
            x = self._inches_to_cm(x)
        self.move_right(x)

    def fly_forward(self, x, units):
        if units == 'in':
            x = self._inches_to_cm(x)
        self.move_forward(x)

    def fly_backward(self, x, units):
        if units == 'in':
            x = self._inches_to_cm(x)
        self.move_back(x)

    def fly_to_xyz(self, x, y,z, units):
        if units == 'in':
            x = self._inches_to_cm(x)
            y = self._inches_to_cm(y)
            z = self._inches_to_cm(z)

        self.go_xyz_speed(x, y, z, 50)

    def fly_curve(self, x1, y1, z1, x2, y2, z2, units):
        if units == 'in':
            x1 = self._inches_to_cm(x1)
            y1 = self._inches_to_cm(y1)
            z1 = self._inches_to_cm(z1)

            x2 = self._inches_to_cm(x2)
            y2 = self._inches_to_cm(y2)
            z2 = self._inches_to_cm(z2)

        self.curve_xyz_speed(x1, y1, z1, x2, y2, z2, 50)
if __name__ == '__main__':
    import time

    test_drone = DroneBlocksTello()
    test_drone.connect()

    test_matrix = test_drone.get_blank_display_matrix()

    smile = test_drone.get_smile()
    test_drone.display_image(smile)

    time.sleep(2)

    test_drone.display_image("b000000r0b0000r000b00r00b00br00pb00rp00p00r00p000r0000p0r000000p")
    # up = test_drone.up_arrow_matrix()
    # print(up)
    #
    # down = np.flipud(up)
    # print(down)
    #
    # left = np.rot90(up)
    # print(left)
    #
    # right = np.fliplr(left)
    # print(right)
