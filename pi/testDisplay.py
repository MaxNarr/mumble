#!/usr/bin/env python3

import time
from PIL import Image, ImageDraw, ImageFont
import st7735

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                   ST7735 DISPLAY INITIALIZATION               │
#  └────────────────────────────────────────────────────────────────┘

disp = st7735.ST7735(
    port=0,
    cs=st7735.BG_SPI_CS_BACK,
    dc="GPIO24",
    backlight="GPIO22",
    rst="GPIO25",
    rotation=90,
    invert=False,
    spi_speed_hz=4000000
)

disp.begin()

WIDTH = disp.width
HEIGHT = disp.height

# Choose a TTF font (adjust path/size if needed)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                       HELPER FUNCTIONS                        │
#  └────────────────────────────────────────────────────────────────┘

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` 
    using an older Pillow fallback via getmask().
    """
    mask = font.getmask(text)
    return mask.size

def draw_centered_text(draw_obj, x, y, w, h, text, font, color=(255,255,255)):
    """
    Draws `text` centered in a rectangle (x, y, w, h).
    """
    text_w, text_h = get_text_dimensions(text, font)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                   VERSION 1: 4-TILE LAYOUT                    │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
    """
    Draws 4 tiles on the ST7735 display:
    
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      | (0,0)    |          |
      +----------+----------+
      |  Tile 2  |  Tile 3  |
      |          |          |
      +----------+----------+
    
    tile_colors: list of 4 (R,G,B) tuples. Defaults to black.
    label:       text in each tile.
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 4  # all black

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 2

    # Coordinates for the 4 tiles
    tile_coords = [
        (0,       0),       # Tile 0
        (tile_w,  0),       # Tile 1
        (0,       tile_h),  # Tile 2
        (tile_w,  tile_h)   # Tile 3
    ]

    for i, (tx, ty) in enumerate(tile_coords):
        color = tile_colors[i]
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT, (255,255,255))

    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │               VERSION 2: 2-TILE LAYOUT (VERTICAL)             │
#  └────────────────────────────────────────────────────────────────┘

def display_two_tiles(tile_colors=None, label="Channel"):
    """
    Draws 2 tiles (top + bottom).
    
      +----------+
      |  Tile 0  |
      +----------+
      |  Tile 1  |
      +----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 2

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH
    tile_h = HEIGHT // 2

    coords = [(0, 0), (0, tile_h)]

    for i, (tx, ty) in enumerate(coords):
        color = tile_colors[i]
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT, (255,255,255))

    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │            OPTIONAL: 2-TILE LAYOUT (HORIZONTAL)               │
#  └────────────────────────────────────────────────────────────────┘

def display_two_tiles_side_by_side(tile_colors=None, label="Channel"):
    """
    Draws 2 tiles (left + right).
    
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      +----------+----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0), (0,0,0)]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT

    # Left tile
    left_color = tile_colors[0]
    draw.rectangle((0, 0, tile_w, tile_h), fill=left_color)
    draw_centered_text(draw, 0, 0, tile_w, tile_h, label, FONT, (255,255,255))

    # Right tile
    right_color = tile_colors[1]
    draw.rectangle((tile_w, 0, WIDTH, tile_h), fill=right_color)
    draw_centered_text(draw, tile_w, 0, tile_w, tile_h, label, FONT, (255,255,255))

    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                            DEMO MAIN                          │
#  └────────────────────────────────────────────────────────────────┘

if __name__ == "__main__":
    print("Displaying 4 tiles...")
    colors_4 = [
        (0, 0, 0),       # black
        (0, 0, 255),     # blue
        (255, 255, 255), # white
        (255, 0, 0)      # red
    ]
    display_four_tiles(colors_4, label="Channel")
    time.sleep(3)

    print("Displaying 2 tiles vertically...")
    colors_2_vertical = [
        (255, 255, 0),   # yellow top
        (0, 255, 0)      # green bottom
    ]
    display_two_tiles(colors_2_vertical, label="Channel")
    time.sleep(3)

    print("Displaying 2 tiles horizontally...")
    colors_2_horizontal = [
        (255, 0, 255),   # magenta left
        (0, 255, 255)    # cyan right
    ]
    display_two_tiles_side_by_side(colors_2_horizontal, label="Channel")
    time.sleep(3)

    print("Done!")