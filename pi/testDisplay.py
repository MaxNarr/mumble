#!/usr/bin/env python3

import time
from PIL import Image, ImageDraw, ImageFont
import st7735

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                   ST7735 DISPLAY INITIALIZATION               │
#  └────────────────────────────────────────────────────────────────┘

# Create and initialize ST7735 class.
# Adjust pins (dc, backlight, rst) and rotation as needed.
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

# Get the display's width/height after rotation.
WIDTH = disp.width
HEIGHT = disp.height

# Choose a readable TTF font. Adjust size/path as needed.
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                       HELPER FUNCTIONS                        │
#  └────────────────────────────────────────────────────────────────┘

def draw_centered_text(draw_obj, x, y, w, h, text, font, color=(255,255,255)):
    """
    Draw text centered in a rectangle defined by (x, y, w, h):
      - x, y: top-left corner
      - w   : width of rectangle
      - h   : height of rectangle
    """
    text_w, text_h = font.getsize(text)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                   VERSION 1: 4-TILE LAYOUT                    │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
    """
    Draws four tiles on the ST7735 display:
    
    Layout (each tile is WIDTH/2 by HEIGHT/2):
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      | (0,0)    |          |
      +----------+----------+
      |  Tile 2  |  Tile 3  |
      |          |          |
      +----------+----------+
    
    tile_colors: A list of 4 (R,G,B) tuples. Defaults to black for all.
    label      : The text displayed in each tile. 
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 4  # All black if none given
    
    # Create an image to draw on
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 2

    # Coordinates of each tile's top-left corner
    tile_coords = [
        (0,       0),        # Tile 0
        (tile_w,  0),        # Tile 1
        (0,       tile_h),   # Tile 2
        (tile_w,  tile_h)    # Tile 3
    ]

    for i, (tx, ty) in enumerate(tile_coords):
        color = tile_colors[i]
        # Draw the background rectangle
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        # Draw centered label
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT, color=(255,255,255))

    # Send the image to the display
    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                 VERSION 2: 2-TILE LAYOUT (VERTICAL)           │
#  └────────────────────────────────────────────────────────────────┘

def display_two_tiles(tile_colors=None, label="Channel"):
    """
    Draws two tiles (top and bottom) on the ST7735 display:
    
    Layout (each tile is WIDTH by HEIGHT/2):
      +----------+
      |  Tile 0  |
      | (0,0)    |
      +----------+
      |  Tile 1  |
      | (0,topH) |
      +----------+
    
    tile_colors: A list of 2 (R,G,B) tuples. Defaults to black for both.
    label      : The text displayed in each tile.
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 2
    
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH
    tile_h = HEIGHT // 2

    # Coordinates of each tile's top-left corner
    tile_coords = [
        (0, 0),           # Tile 0 (top)
        (0, tile_h)       # Tile 1 (bottom)
    ]

    for i, (tx, ty) in enumerate(tile_coords):
        color = tile_colors[i]
        # Draw the background rectangle
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        # Draw centered label
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT, color=(255,255,255))

    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │        OPTIONAL: 2-TILE LAYOUT (HORIZONTAL SPLIT)             │
#  └────────────────────────────────────────────────────────────────┘

def display_two_tiles_side_by_side(tile_colors=None, label="Channel"):
    """
    Draws two tiles (left and right) on the ST7735 display:
    
    Layout (each tile is WIDTH/2 by HEIGHT):
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      | (0,0)    | (tileW,0)|
      +----------+----------+
    
    tile_colors: A list of 2 (R,G,B) tuples. Defaults to black for both.
    label      : The text displayed in each tile.
    """
    if tile_colors is None:
        tile_colors = [(0,0,0), (0,0,0)]
    
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT

    # Left tile
    color_left = tile_colors[0]
    draw.rectangle((0, 0, tile_w, tile_h), fill=color_left)
    draw_centered_text(draw, 0, 0, tile_w, tile_h, label, FONT, color=(255,255,255))

    # Right tile
    color_right = tile_colors[1]
    draw.rectangle((tile_w, 0, WIDTH, tile_h), fill=color_right)
    draw_centered_text(draw, tile_w, 0, tile_w, tile_h, label, FONT, color=(255,255,255))

    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                          DEMO MAIN                            │
#  └────────────────────────────────────────────────────────────────┘

if __name__ == "__main__":
    # 1) DEMO: 4 Tiles
    print("Displaying 4 tiles...")
    colors_4 = [
        (0, 0, 0),       # black
        (0, 0, 255),     # blue
        (255, 255, 255), # white
        (255, 0, 0)      # red
    ]
    display_four_tiles(colors_4, label="Channel")
    time.sleep(3)

    # 2) DEMO: 2 Tiles (Vertical)
    print("Displaying 2 tiles vertically...")
    colors_2_vertical = [
        (255, 255, 0),   # yellow top
        (0, 255, 0)      # green bottom
    ]
    display_two_tiles(colors_2_vertical, label="Channel")
    time.sleep(3)

    # 3) DEMO: 2 Tiles (Horizontal)
    print("Displaying 2 tiles horizontally...")
    colors_2_horizontal = [
        (255, 0, 255),   # magenta left
        (0, 255, 255)    # cyan right
    ]
    display_two_tiles_side_by_side(colors_2_horizontal, label="Channel")
    time.sleep(3)

    print("Done!")