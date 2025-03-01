#!/usr/bin/env python3

import time
from PIL import Image, ImageDraw, ImageFont
import st7735

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                  ST7735 DISPLAY INITIALIZATION                │
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

# Font a little smaller to fit more letters in small tiles
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │          TEXT DIMENSION FALLBACK FOR OLDER PIL VERSIONS       │
#  └────────────────────────────────────────────────────────────────┘

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` using getmask() fallback.
    """
    mask = font.getmask(text)
    return mask.size

def draw_centered_text(draw_obj, x, y, w, h, text, font, color=(255,255,255)):
    """
    Draw `text` centered in a rectangle (x, y, w, h).
    """
    text_w, text_h = get_text_dimensions(text, font)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                EXISTING DEMO FUNCTIONS: 4 & 2 TILES           │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
    """
    4 tiles (2x2):
      +----------+----------+
      |  0       |   1      |
      +----------+----------+
      |  2       |   3      |
      +----------+----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 4  # all black
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 2
    coords = [(0,0), (tile_w,0), (0,tile_h), (tile_w,tile_h)]

    for i, (tx, ty) in enumerate(coords):
        color = tile_colors[i]
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT)

    disp.display(img)


def display_two_tiles(tile_colors=None, label="Channel"):
    """
    2 tiles (vertical):
      +----------+
      |   0      |
      +----------+
      |   1      |
      +----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 2
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH
    tile_h = HEIGHT // 2
    coords = [(0,0), (0,tile_h)]

    for i, (tx, ty) in enumerate(coords):
        color = tile_colors[i]
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT)

    disp.display(img)


def display_two_tiles_side_by_side(tile_colors=None, label="Channel"):
    """
    2 tiles (horizontal):
      +----------+----------+
      |   0      |    1     |
      +----------+----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 2
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT
    left_color, right_color = tile_colors

    # Left tile
    draw.rectangle((0, 0, tile_w, tile_h), fill=left_color)
    draw_centered_text(draw, 0, 0, tile_w, tile_h, label, FONT)

    # Right tile
    draw.rectangle((tile_w, 0, WIDTH, tile_h), fill=right_color)
    draw_centered_text(draw, tile_w, 0, tile_w, tile_h, label, FONT)

    disp.display(img)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │               EXISTING: 6-TILE MENU (2 x 3)                   │
#  └────────────────────────────────────────────────────────────────┘

def display_six_tile_menu(selected_tile=0, labels=None):
    """
    6 tiles (2 columns x 3 rows):
      +---------+---------+
      |   0     |    1    |
      +---------+---------+
      |   2     |    3    |
      +---------+---------+
      |   4     |    5    |
      +---------+---------+
    White border, black background normally;
    Selected tile = white fill, black text.
    """
    if labels is None:
        labels = [f"Item {i+1}" for i in range(6)]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 3

    # Generate tile coords in row-major order
    tile_coords = []
    index = 0
    for row in range(3):
        for col in range(2):
            x = col * tile_w
            y = row * tile_h
            tile_coords.append((x, y))
            index += 1

    for i in range(6):
        tx, ty = tile_coords[i]
        if i == selected_tile:
            fill_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            fill_color = (0, 0, 0)
            text_color = (255, 255, 255)

        # Draw tile with white border
        draw.rectangle(
            (tx, ty, tx + tile_w, ty + tile_h),
            fill=fill_color,
            outline=(255, 255, 255)
        )
        draw_centered_text(draw, tx, ty, tile_w, tile_h, labels[i], FONT, text_color)

    disp.display(img)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │   NEW: GERMAN KEYBOARD (3 ROWS x 10 COLUMNS = 30 LETTERS)     │
#  └────────────────────────────────────────────────────────────────┘

def display_german_keyboard(selected_key=0):
    """
    Displays a German QWERTZ layout, 30 letters total, 
    arranged in 3 rows x 10 columns:

      Row 0: Q W E R T Z U I O P
      Row 1: A S D F G H J K L Ö
      Row 2: Y X C V B N M Ä Ü ß

    Each letter is in a tile with a white border.
    If selected, the tile inverts (white background, black text).
    """
    # German QWERTZ letters (30 total):
    keyboard_letters = [
        "Q","W","E","R","T","Z","U","I","O","P",
        "A","S","D","F","G","H","J","K","L","Ö",
        "Y","X","C","V","B","N","M","Ä","Ü","ß"
    ]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 3 rows x 10 columns
    cols = 10
    rows = 3
    tile_w = WIDTH // cols
    tile_h = HEIGHT // rows

    for i in range(len(keyboard_letters)):
        row = i // cols
        col = i % cols
        tx = col * tile_w
        ty = row * tile_h

        if i == selected_key:
            fill_color = (255, 255, 255)  # white background
            text_color = (0, 0, 0)        # black text
        else:
            fill_color = (0, 0, 0)        # black background
            text_color = (255, 255, 255)  # white text

        # Draw key with white outline
        draw.rectangle(
            (tx, ty, tx + tile_w, ty + tile_h),
            fill=fill_color,
            outline=(255, 255, 255)
        )

        # Draw the letter
        letter = keyboard_letters[i]
        draw_centered_text(draw, tx, ty, tile_w, tile_h, letter, FONT, text_color)

    disp.display(img)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                            DEMO MAIN                          │
#  └────────────────────────────────────────────────────────────────┘

if __name__ == "__main__":
    # 1) DEMO: 4 TILES
    print("Displaying 4 tiles...")
    colors_4 = [
        (0, 0, 0),       # black
        (0, 0, 255),     # blue
        (255, 255, 255), # white
        (255, 0, 0)      # red
    ]
    display_four_tiles(colors_4, label="Channel")
    time.sleep(2)

    # 2) DEMO: 2 TILES (VERTICAL)
    print("Displaying 2 tiles vertically...")
    colors_2_vertical = [
        (255, 255, 0),   # yellow top
        (0, 255, 0)      # green bottom
    ]
    display_two_tiles(colors_2_vertical, label="Channel")
    time.sleep(2)

    # 3) DEMO: 2 TILES (HORIZONTAL)
    print("Displaying 2 tiles horizontally...")
    colors_2_horizontal = [
        (255, 0, 255),   # magenta left
        (0, 255, 255)    # cyan right
    ]
    display_two_tiles_side_by_side(colors_2_horizontal, label="Channel")
    time.sleep(2)

    # 4) DEMO: 6-TILE MENU
    print("Displaying 6-tile menu with selection...")
    menu_labels = ["Option A", "Option B", "Option C", "Option D", "Option E", "Option F"]
    for i in range(6):
        print(f"Selecting tile index {i} ({menu_labels[i]})")
        display_six_tile_menu(selected_tile=i, labels=menu_labels)
        time.sleep(1)

    # 5) NEW DEMO: GERMAN KEYBOARD
    print("Displaying German QWERTZ keyboard with selection...")
    # We'll iterate through all 30 letters
    for i in range(30):
        display_german_keyboard(selected_key=i)
        time.sleep(0.3)

    print("Done!")