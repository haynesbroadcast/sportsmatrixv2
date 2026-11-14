#!/usr/bin/env python3
"""Direct HUB75 pixel-clarity patterns (no ESPN, Pillow font, or logo scaling)."""
import time

from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

WIDTH, HEIGHT = 128, 64
HOLD_SECONDS = 7


def patterns():
    # Every other x: isolated 1-pixel vertical columns test horizontal clarity.
    vertical = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    for x in range(0, WIDTH, 2):
        for y in range(HEIGHT):
            vertical.putpixel((x, y), (255, 255, 255))
    yield "VERTICAL 1px stripes: are left/right edges sharp?", vertical

    # Every other y: isolated 1-pixel horizontal rows test vertical clarity.
    horizontal = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    for y in range(0, HEIGHT, 2):
        for x in range(WIDTH):
            horizontal.putpixel((x, y), (255, 255, 255))
    yield "HORIZONTAL 1px stripes: are top/bottom edges sharp?", horizontal

    checker = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if (x + y) % 2 == 0:
                checker.putpixel((x, y), (255, 255, 255))
    yield "CHECKERBOARD 1px: any sideways bleed or ghosts?", checker

    edges = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    for x, color in ((8, (255, 0, 0)), (32, (0, 255, 0)),
                     (56, (0, 0, 255)), (80, (255, 255, 255))):
        for y in range(8, 56):
            edges.putpixel((x, y), color)
    yield "ISOLATED RGB/white lines against black: any horizontal halos?", edges


def main():
    options = RGBMatrixOptions()
    options.rows, options.cols = HEIGHT, WIDTH
    options.chain_length = options.parallel = 1
    options.hardware_mapping = "adafruit-hat"
    options.led_rgb_sequence = "BGR"
    options.gpio_slowdown = 4
    options.brightness = 20
    options.drop_privileges = False
    matrix = RGBMatrix(options=options)
    try:
        for label, frame in patterns():
            print(label, flush=True)
            matrix.SetImage(frame)
            time.sleep(HOLD_SECONDS)
    finally:
        matrix.Clear()
        print("Diagnostic display cleared.", flush=True)


if __name__ == "__main__":
    main()
