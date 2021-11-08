from djitellopy import Tello


class DroneBlocksTello(Tello):
    UP      = 'u'
    LEFT    = 'l'
    DOWN    = 'd'
    RIGHT   = 'r'

    PURPLE  = 'p'
    BLUE    = 'b'
    RED     = 'r'

    def __init__(self):
        super().__init__()

    @classmethod
    def get_blank_display_matrix(cls):
        return "0000000000000000000000000000000000000000000000000000000000000000"

    def _up_arrow_matrix(self, display_color:str=PURPLE) -> str:
        up = DroneBlocksTello.get_blank_display_matrix()
        up[0, 3:5] = display_color
        up[1, 2:6] = display_color
        up[2, 1:7] = display_color
        up[3, 0:8] = display_color
        up[4, 3:5] = display_color
        up[5, 3:5] = display_color
        up[6, 3:5] = display_color
        up[7, 3:5] = display_color
        return up

    def _display_pattern(self, flattened_matrix:str ) -> str:
        return self.send_command_with_return(f"EXT mled g {flattened_matrix}")

    def get_speed(self) -> int:
        """Query speed setting (cm/s)
        Returns:
            int: 1-100
        """
        speed_value = self.send_read_command('speed?')
        return int(float(speed_value))


    def pulse_top_led(self, r: int, g: int, b: int, freq: float = 2.5) -> str:
        """
        The top LED displays the pulse effect according to the max pulse brightness (r, g, b) and pulse frequency t.
        The cycle from dimmest to brightest to dimmest again is counted as one pulse.
            r, g, b: 0~255
            freq: 0.1-2.5Hz
        :return: OK/ERROR
        """
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
        return self.send_command_with_return(f"EXT led bl {freq} {r1} {g1} {b1} {r2} {g2} {b2}")

    def change_image_color(self, image_string, from_color, to_color):
        image_string.replace(DroneBlocksTello.BLUE, DroneBlocksTello.PURPLE)
        return image_string

    def get_up_arrow(self, display_color:str=BLUE) -> str:
        up = "000bb00000bbbb000bbbbbb0000bb000000bb000000bb000000bb000000bb000"
        up = self.change_image_color(up, DroneBlocksTello.BLUE, display_color)
        return up

    def get_down_arrow(self, display_color:str=BLUE) -> str:
        down = "000bb000000bb000000bb000000bb000000bb0000bbbbbb000bbbb00000bb000"
        down = self.change_image_color(down, DroneBlocksTello.BLUE, display_color)
        return down

    def get_left_arrow(self, display_color:str=BLUE) -> str:
        left = "0000000000b000000bb00000bbbbbbbbbbbbbbbb0bb0000000b0000000000000"
        left = self.change_image_color(left, DroneBlocksTello.BLUE, display_color)
        return left

    def get_right_arrow(self, display_color:str=BLUE) -> str:
        right = "0000000000000b0000000bb0bbbbbbbbbbbbbbbb00000bb000000b0000000000"
        right = self.change_image_color(right, DroneBlocksTello.BLUE, display_color)
        return right

    def display_image(self, display_string:str) -> str:
        return self._display_pattern(display_string)

    def clear_display(self) -> str:
        display = DroneBlocksTello.get_blank_display_matrix()
        return self._display_pattern(display)

    def clear_everything(self):
        self.clear_display()
        self.set_top_led(r=0, g=0, b=0)

    def display_heart(self, display_color:str=PURPLE) -> str:
        return self.send_command_with_return(f"EXT mled s {display_color} heart")

    def display_character(self, single_character:str, display_color:str=PURPLE) -> str:
        return self.send_command_with_return(f"EXT mled s {display_color} {single_character}")

    def get_smile(self, display_color:str=PURPLE) -> str:
        smile_image = "0000000000b00b0000000000000bb000b00bb00bb000000b0b0000b000bbbb00"
        smile_image = self.change_image_color(smile_image, DroneBlocksTello.BLUE, display_color)
        return smile_image

    def get_sad(self, display_color:str=PURPLE) -> str:
        sad_image = "0000000000b00b0000000000000bb000000bb000000000000bbbbbb0b000000b"
        sad_image = self.change_image_color(sad_image, DroneBlocksTello.BLUE, display_color)
        return sad_image

    def scroll_image(self, display_string:str,  scroll_dir:str, rate:float=2.5)->str:
        return self.send_command_with_return(f"EXT mled {scroll_dir} g {rate} {display_string}")

    def scroll_string(self, message:str,  scroll_dir:str, display_color:str=PURPLE, rate:float=2.5)->str:
        if len(message) > 70:
            message = message[0:70]

        return self.send_command_with_return(f"EXT mled {scroll_dir} {display_color} {rate} {message}")



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
