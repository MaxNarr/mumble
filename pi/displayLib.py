#!/usr/bin/env python3

import time
from PIL import Image, ImageDraw, ImageFont
import st7735

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │            DISPLAY INITIALIZATION (GLOBAL)                    │
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

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │          FALLBACK TEXT SIZE FOR OLDER PIL VERSIONS            │
#  └────────────────────────────────────────────────────────────────┘

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` using `font.getmask()`.
    This helps if your Pillow version doesn't have draw.textsize or font.getsize.
    """
    mask = font.getmask(text)
    return mask.size

def draw_centered_text(draw_obj, x, y, w, h, text, font, color=(255,255,255)):
    """
    Draw `text` centered in a rectangle (x,y,w,h).
    """
    text_w, text_h = get_text_dimensions(text, font)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                   TILE DEMO FUNCTIONS                         │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
    """
    Draws 4 tiles in a 2x2 grid:
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      +----------+----------+
      |  Tile 2  |  Tile 3  |
      +----------+----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 4  # default all black

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 2
    coords = [
        (0,        0),
        (tile_w,   0),
        (0,        tile_h),
        (tile_w,   tile_h)
    ]

    for i, (tx, ty) in enumerate(coords):
        color = tile_colors[i]
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT)

    disp.display(img)


def display_two_tiles(tile_colors=None, label="Channel"):
    """
    Draws 2 tiles stacked vertically:
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
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT)

    disp.display(img)


def display_two_tiles_side_by_side(tile_colors=None, label="Channel"):
    """
    Draws 2 tiles side-by-side (horizontal):
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      +----------+----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 2

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT

    # Left tile
    draw.rectangle((0, 0, tile_w, tile_h), fill=tile_colors[0])
    draw_centered_text(draw, 0, 0, tile_w, tile_h, label, FONT)

    # Right tile
    draw.rectangle((tile_w, 0, WIDTH, tile_h), fill=tile_colors[1])
    draw_centered_text(draw, tile_w, 0, tile_w, tile_h, label, FONT)

    disp.display(img)


def display_six_tile_menu(selected_tile=0, labels=None):
    """
    Draws 6 tiles (2 columns x 3 rows):
      +---------+---------+
      |   0     |    1    |
      +---------+---------+
      |   2     |    3    |
      +---------+---------+
      |   4     |    5    |
      +---------+---------+
    - White outline
    - Black background for unselected
    - Inverted (white bg, black text) for selected tile
    """
    if labels is None:
        labels = [f"Item {i+1}" for i in range(6)]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 3

    coords = []
    idx = 0
    for row in range(3):
        for col in range(2):
            x = col * tile_w
            y = row * tile_h
            coords.append((x, y))
            idx += 1

    for i, (tx, ty) in enumerate(coords):
        if i == selected_tile:
            fill_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            fill_color = (0, 0, 0)
            text_color = (255, 255, 255)

        draw.rectangle(
            (tx, ty, tx + tile_w, ty + tile_h),
            fill=fill_color,
            outline=(255,255,255)
        )
        draw_centered_text(draw, tx, ty, tile_w, tile_h, labels[i], FONT, text_color)

    disp.display(img)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │           KEYBOARD + TEXT FIELD (BOTTOM 2/3 + TOP 1/3)        │
#  └────────────────────────────────────────────────────────────────┘

# Keyboard rows (no umlauts)
ROW0 = ["Q","W","E","R","T","Z","U","I","O","P"]  # 10
ROW1 = ["A","S","D","F","G","H","J","K","L"]      # 9
ROW2 = ["Y","X","C","V","B","N","M"]              # 7
ALL_LETTERS = ROW0 + ROW1 + ROW2

# Offsets for each row (like a real keyboard)
ROW_OFFSETS = [0.0, 0.5, 1.0]

# Globals for typed text and selection
typed_text = ""
selected_key_index = 0

def display_keyboard_screen(selected_key, typed_text):
    """
    1) A text field in the top 1/3
    2) A QWERTZ keyboard in the bottom 2/3, row2 further to the right
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Text field area
    text_field_height = HEIGHT // 3
    draw.rectangle((0, 0, WIDTH, text_field_height),
                   outline=(255,255,255), fill=(0,0,0))
    draw_centered_text(draw, 0, 0, WIDTH, text_field_height, typed_text, FONT, (255,255,255))

    # Keyboard area
    kb_top_y = text_field_height
    kb_height = HEIGHT - text_field_height
    margin_x = 0
    usable_width = WIDTH - 20  # keep a 20-pixel margin on the right

    row_height = kb_height / 3
    cur_index = 0

    for r, row_letters in enumerate([ROW0, ROW1, ROW2]):
        y = int(kb_top_y + r * row_height)
        h = int(row_height)
        num_cols = len(row_letters)
        key_width = usable_width / num_cols

        offset_pixels = int(ROW_OFFSETS[r] * key_width)

        for c, letter in enumerate(row_letters):
            x = margin_x + offset_pixels + int(c * key_width)
            w = int(key_width)

            if cur_index == selected_key:
                fill_color = (255,255,255)
                text_color = (0,0,0)
            else:
                fill_color = (0,0,0)
                text_color = (255,255,255)

            draw.rectangle((x, y, x + w, y + h),
                           fill=fill_color,
                           outline=(255,255,255))
            draw_centered_text(draw, x, y, w, h, letter, FONT, text_color)

            cur_index += 1

    disp.display(img)

def process_input(delta, select):
    """
    Moves selection by delta {-1,0,+1}:
      -1 = previous key
       0 = no move
      +1 = next key
    If `select` is True, append the current letter to typed_text.
    Then update the display.
    """
    global selected_key_index, typed_text

    if delta != 0:
        selected_key_index = (selected_key_index + delta) % len(ALL_LETTERS)

    if select:
        typed_text += ALL_LETTERS[selected_key_index]

    display_keyboard_screen(selected_key_index, typed_text)

def get_textfield_content():
    """
    Returns the typed text so far.
    """
    return typed_text

# Initialize display to show keyboard screen with default selection
display_keyboard_screen(selected_key_index, typed_text)
