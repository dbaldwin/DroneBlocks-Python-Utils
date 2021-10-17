from djitellopy import Tello
import numpy as np


class DroneBlocksTello(Tello):
    UP = 'u'
    LEFT = 'l'
    DOWN = 'd'
    RIGHT = 'r'

    PURPLE = 'p'
    BLUE = 'b'
    RED = 'r'

    def __init__(self):
        super().__init__()

    @classmethod
    def get_blank_display_matrix(cls):
        return np.full((8,8), '0', dtype=str)

    def _up_arrow_matrix(self, display_color=PURPLE):
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

    def _display_pattern(self, pattern_matrix):
        pattern = ''.join(pattern_matrix.flatten().tolist())
        return self.send_command_with_return(f"EXT mled g {pattern}")

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


    def get_up_arrow(self, display_color=PURPLE):
        up = self._up_arrow_matrix(display_color)
        return up

    def get_down_arrow(self, display_color=PURPLE):
        up = self._up_arrow_matrix(display_color)
        down = np.flipud(up)
        return down

    def get_left_arrow(self, display_color=PURPLE):
        
        up = self._up_arrow_matrix(display_color)
        left = np.rot90(up)
        return left

    def get_right_arrow(self, display_color=PURPLE):
        
        up = self._up_arrow_matrix(display_color)
        left = np.rot90(up)
        right = np.fliplr(left)
        return right

    def display_image(self, image_matrix):
        return self._display_pattern(image_matrix)

    def clear_display(self) -> str:
        display = DroneBlocksTello.get_blank_display_matrix()
        return self._display_pattern(display)

    def display_heart(self, display_color=PURPLE):
        return self.send_command_with_return(f"EXT mled s {display_color} heart")

    def display_character(self, single_character, display_color=PURPLE):
        return self.send_command_with_return(f"EXT mled s {display_color} {single_character}")

    def get_smile(self, display_color=PURPLE):
        
        smile = DroneBlocksTello.get_blank_display_matrix()
        smile[0, 2] = display_color
        smile[0, 5] = display_color
        smile[2, 3:5] = display_color
        smile[3, 3:5] = display_color
        smile[4, 1] = display_color
        smile[4, 6] = display_color
        smile[5, 1] = display_color
        smile[5, 6] = display_color
        smile[6, 2] = display_color
        smile[6, 5] = display_color
        smile[7, 3:5] = display_color
        return smile

    def scroll_image(self, image,  scroll_dir, rate=2.5):
        pattern = ''.join(image.flatten().tolist())

        return self.send_command_with_return(f"EXT mled {scroll_dir} g {rate} {pattern}")

    def scroll_string(self, message,  scroll_dir, display_color=PURPLE, rate=2.5):
        if len(message) > 70:
            message = message[0:70]

        return self.send_command_with_return(f"EXT mled {scroll_dir} {display_color} {rate} {message}")



if __name__ == '__main__':
    test_drone = DroneBlocksTello()
    test_drone.connect()

    test_matrix = test_drone.get_blank_display_matrix()

    smile = test_drone.get_smile()
    test_drone.display_image(smile)

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
