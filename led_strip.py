from neopixel import Neopixel
from LEDArray import LEDArray, ColorPalette, PaletteRoll, Sparkle

NUM_PIXELS = 52
PORT = 28
STATE_MACHINE = 0
DELAY = 0.001
MODE = "GRB"
BRIGHTNESS = 20

strip = Neopixel(NUM_PIXELS, STATE_MACHINE, PORT, MODE, DELAY)
strip.brightness(BRIGHTNESS)

led_array = LEDArray(strip)
strip.clear()

from palettes import fire, white_to_black, halloween_full, halloween_purple_fire

fire_palette = ColorPalette(fire, NUM_PIXELS)
halloween_palette = ColorPalette(halloween_purple_fire, NUM_PIXELS)
sparkle_palette = ColorPalette(white_to_black, 512)

trans_palette_roll = PaletteRoll(led_array, halloween_purple_fire, 1)
trans_sparkle = Sparkle(led_array, sparkle_palette, 1)

transforms = [
    trans_palette_roll,
    trans_sparkle
]

led_array.assign_transforms(transforms)

while True:
    # led_array.update_array()
    # led_array.fill_from_palette(halloween_purple_fire)
    led_array.update_array()

