# from neopixel import Neopixel
import array
from color_conversion import hsl_to_rgb
import time
import math

def linspace(start, stop, n):
    if n == 1:
        yield stop
        return
    h = (stop - start) / (n - 1)
    for i in range(n):
        yield start + h * i

def is_iterable(element):
    try:
        iter(element)
    except TypeError:
        return 0
    else:
        return 1

def interpolate_indexed_color_linear(color0, color1, resolution):

    i_0, x0_0, x1_0, x2_0 = color0
    i_1, x0_1, x1_1, x2_1 = color1

    di = min((i_1 - i_0, 1))

    dx0di = (x0_1 - x0_0) / di
    dx1di = (x1_1 - x1_0) / di
    dx2di = (x2_1 - x2_0) / di

    color_table = []

    for i in linspace(0, di, math.ceil(resolution)):
        x0_i = x0_0 + dx0di * i
        x1_i = x1_0 + dx1di * i
        x2_i = x2_0 + dx2di * i
        color_table.append((i_0 + i, x0_i, x1_i, x2_i))

    return color_table


class Color:
    def __init__(self, *args):
        self.params = args

    def __add__(self, delta_color):
        return Color(param + delta for param, delta in zip(self.params, delta_color))

    def __iter__(self):
        return iter(self.params)

class CRGB(Color):
    @property
    def R(self):
        return self.params[0]
    @property
    def G(self):
        return self.params[1]
    @property
    def B(self):
        return self.params[2]

class CHSL(Color):
    @property
    def H(self):
        return self.params[0]
    @property
    def S(self):
        return self.params[1]
    @property
    def L(self):
        return self.params[2]

class ColorPalette:

    def __init__(self, colors: tuple[tuple[int]], resolution) -> None:
        self.palette = []
        max_idx = colors[-1][0]
        for color_idx in range(len(colors)-1):
            color0 = colors[color_idx]
            color1 = colors[color_idx+1]
            idx0 = color0[0]
            idx1 = color1[0]
            resolution_segment = resolution*(idx1-idx0)/max_idx
            self.palette.extend(interpolate_indexed_color_linear(color0, color1, resolution_segment)[:-1])
        self.palette.extend([colors[-1]])

    def __iter__(self):
        return iter(self.palette)
    
    def __getitem__(self, idx):
        return self.palette[idx]

    def __len__(self):
        return len(self.palette)

    def colors(self):
        return tuple(color[1:] for color in self.palette)

class LEDArray:

    def __init__(self, strip, transforms:list = None):

        self.strip = strip
        self.num_leds = self.strip.num_leds

        n_leds = self.num_leds
        self.R = array.array("I", [0] * n_leds) # red
        self.G = array.array("I", [0] * n_leds) # green
        self.B = array.array("I", [0] * n_leds) # blue
        self.W = array.array("I", [0] * n_leds) # white
        self.Br = array.array("I", [0] * n_leds) # brightness
        self.transforms = []
        if transforms:
            self.assign_transforms(transforms)

    def assign_transforms(self, transforms):
        if is_iterable(transforms):
            self.transforms.extend(transforms)
        else:
            self.transforms.append(transforms)

    def get_states(self):
        return (self.R, self.G, self.B, self.W, self.Br)

    def get_state_at_led(self, idx):
        return tuple(col[idx] for col in zip(self.R, self.G, self.B, self.W, self.Br))


    def set_state_at_led(self, idx:int, state):
        idx = math.ceil(idx)
        R, G, B, W, Br = state
        self.R[idx] = int(R)
        self.G[idx] = int(G)
        self.B[idx] = int(B)
        self.W[idx] = int(W)
        self.Br[idx] =int(Br)

    def fill_from_palette(self, palette):
        brightness = self.strip.brightness()
        if type(palette) != ColorPalette:
            palette = ColorPalette(palette, self.num_leds).colors()
        else:
            palette = palette.colors()
        for i in range(len(palette)):
            new_color = palette[i]
            new_state =  new_color + (0, brightness)
            self.strip.set_pixel(i, new_color)
            self.set_state_at_led(i, new_state)

    def update_array(self):
        for transform in self.transforms:
            state = transform.next_state()
            for i in range(self.num_leds):
                self.strip.set_pixel(i, state[i][:4], state[i][-1])
                self.set_state_at_led(i, state[i])
        self.show()

    def show(self):
        self.strip.show()


class LEDArray2D(LEDArray):
    
    def __init__(self, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = width
        self.height = height

    def vertical_fill(self, row1, row2, left_rgb_w, right_rgb_w, how_bright=None, with_white=False):
        """
        Create a gradient with two RGB colors between "row1" and "row2" (inclusive)

        :param row1: Index of starting row (inclusive)
        :param row2: Index of ending row (inclusive)
        :param left_rgb_w: Tuple of form (r, g, b) or (r, g, b, w) representing starting color
        :param right_rgb_w: Tuple of form (r, g, b) or (r, g, b, w) representing ending color
        :param how_bright: [default: None] Brightness of current interval. If None, use global brightness value
        :return: None
        """
        width = self.width
        strip = self.strip

        if row2 - row1 == 0:
            return
        top_row = max(row1, row2)
        bottom_row = min(row1, row2)

        r_diff = right_rgb_w[0] - left_rgb_w[0]
        g_diff = right_rgb_w[1] - left_rgb_w[1]
        b_diff = right_rgb_w[2] - left_rgb_w[2]

        for i in range(top_row - bottom_row + 1):
            fraction = i / (top_row - bottom_row)
            red = round(r_diff * fraction + left_rgb_w[0])
            green = round(g_diff * fraction + left_rgb_w[1])
            blue = round(b_diff * fraction + left_rgb_w[2])
            # if it's (r, g, b, w)
            if len(left_rgb_w) == 4 and with_white:
                white = round((right_rgb_w[3] - left_rgb_w[3]) * fraction + left_rgb_w[3])
                strip.set_pixel_line(i * width, (i+1) * width, (red, green, blue, white), how_bright)
            else:
                strip.set_pixel_line(i * width, (i+1) * width, (red, green, blue), how_bright)




class LEDTransform:
    def __init__(self, led_array:LEDArray) -> None:
        self.led_array = led_array
        self.num_pixels = led_array.strip.num_leds

    def get_blank_state(self):
        n_pixels = self.num_pixels
        R = array.array("I", [0] * n_pixels) # red
        G = array.array("I", [0] * n_pixels) # green
        B = array.array("I", [0] * n_pixels) # blue
        W = array.array("I", [0] * n_pixels) # white
        Br = array.array("I", [0] * n_pixels) # brightness
        return list(zip(R, G, B, W, Br))


class SineRoll(LEDTransform):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class PaletteRoll(LEDTransform):

    def __init__(self, led_array: LEDArray, palette:ColorPalette, roll_speed=1, *args, **kwargs):

        super().__init__(led_array, *args, **kwargs)
        self.led_array.fill_from_palette(palette)
        self.roll_speed = roll_speed
        

    def next_state(self):
        R, G, B, W, Br = self.led_array.get_states()
        R_new = R[self.roll_speed:] + R[:self.roll_speed]
        G_new = G[self.roll_speed:] + G[:self.roll_speed]
        B_new = B[self.roll_speed:] + B[:self.roll_speed]
        W_new = W[self.roll_speed:] + W[:self.roll_speed]
        Br_new = Br[self.roll_speed:] + Br[:self.roll_speed]
        return tuple(zip(R_new, G_new, B_new, W_new, Br_new))


class Sparkle(LEDTransform):

    def __init__(self, led_array: LEDArray, palette:ColorPalette, fade_speed=1, *args, **kwargs):
        super().__init__(led_array, *args, **kwargs)
        self.fade_speed = fade_speed
        self.palette = palette.colors()
        self.idx=0
        self.led = 10
        self.brightness = self.led_array.strip.brightness()


    def next_state(self):
        new_state = self.get_blank_state()
        idx = int(self.idx + self.fade_speed)
        num_colors = len(self.palette)
        if idx > num_colors:
            idx %= num_colors
        new_state[self.led] = self.palette[idx] + (0, self.brightness)
        self.idx= idx
        return new_state


class HSVRoll(LEDTransform):

    def __init__(self, color1:tuple, color2:tuple, increment=None, delay=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color1 = Color(*color1)
        self.color2 = Color(*color2)
        self.increment = increment or (0, 0, 0)
        self.delay = delay or 0

    def next_state(self, led_array: LEDArray):
        strip = led_array.strip
        n_pixels = strip.num_leds
        self.color1 = self.color1 + self.increment
        self.color2 = self.color2 + self.increment
        strip.set_pixel_line_gradient(0, n_pixels-1, strip.colorHSV(*self.color1), strip.colorHSV(*self.color2))
        strip.show()
        for _ in range(strip.num_leds):
            
            strip.show()
            time.sleep(self.delay)



def main():
    NUM_PIXELS = 100
    from palettes import fire
    fire_palette = ColorPalette(fire, NUM_PIXELS)


if __name__ == "__main__":
    main()