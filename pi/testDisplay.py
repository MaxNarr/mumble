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

# We'll pick a slightly smaller font to fit keys in narrow tiles
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │          TEXT DIMENSION FALLBACK FOR OLDER PIL VERSIONS       │
#  └────────────────────────────────────────────────────────────────┘

def get_text_dimensions(text, font):
    """
    Returns (width, height) of a single-line `text`, using getmask() fallback.
    For older PIL versions that may lack draw.textsize or font.getsize.
    """
    mask = font.getmask(text)
    return mask.size

def draw_centered_text(draw_obj, x, y, w, h, text, font, color=(255,255,255)):
    """
    Draw `text` centered inside rectangle (x, y, w, h).
    """
    text_w, text_h = get_text_dimensions(text, font)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │          DEMOS: 4-TILE, 2-TILE, 2-SIDE-BY-SIDE, 6-MENU         │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
    """
    4 tiles (2x2).
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 4

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
    2 tiles (vertical).
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
    2 tiles (horizontal).
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


def display_six_tile_menu(selected_tile=0, labels=None):
    """
    6 tiles (2 columns x 3 rows).
    White border, black background normally;
    Selected = white background, black text.
    """
    if labels is None:
        labels = [f"Item {i+1}" for i in range(6)]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 3

    # Row-major coords
    tile_coords = []
    idx = 0
    for row in range(3):
        for col in range(2):
            x = col * tile_w
            y = row * tile_h
            tile_coords.append((x, y))
            idx += 1

    for i in range(6):
        tx, ty = tile_coords[i]
        if i == selected_tile:
            fill_color = (255, 255, 255)  # white
            text_color = (0, 0, 0)        # black
        else:
            fill_color = (0, 0, 0)        # black
            text_color = (255, 255, 255)  # white

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
#  │   NEW: GERMAN QWERTZ KEYBOARD, REALISTIC LAYOUT, BOTTOM 2/3   │
#  └────────────────────────────────────────────────────────────────┘

def display_german_keyboard_realistic(selected_key=0):
    """
    Displays a German QWERTZ keyboard in a "more realistic" layout, using only
    the bottom 2/3 of the screen. 3 rows of keys, each row slightly offset.
    The layout (30 letters):

      Row 0: Q W E R T  Z U I O P
      Row 1: A S D F G  H J K L Ö
      Row 2: Y X C V B  N M Ä Ü ß

    Row offsets (in 'key_width' units):
      row0_offset = 0.0
      row1_offset = 0.5  (half-key offset)
      row2_offset = 0.2  (some offset for demonstration)

    The user can highlight a selected key by inverting colors.
    """
    row0 = ["Q","W","E","R","T","Z","U","I","O","P"]
    row1 = ["A","S","D","F","G","H","J","K","L","Ö"]
    row2 = ["Y","X","C","V","B","N","M","Ä","Ü","ß"]
    all_keys = [row0, row1, row2]

    # We'll only use bottom 2/3 of the screen
    top_y = HEIGHT // 3        # integer
    kb_height = (HEIGHT * 2) // 3
    rows = 3

    # Row offsets in fraction of one key width
    # Adjust as desired to mimic a real keyboard's staggering
    row_offsets = [0.0, 0.5, 0.2]

    # For each row, we have 10 keys
    cols = 10

    # We'll define a left/right margin so keys aren't flush to edges.
    margin_x = WIDTH // 20  # ~5% margin on each side
    usable_width = WIDTH - 2 * margin_x

    # Key width is the 'usable' area / #keys, so row0 fits exactly in that area
    key_width = usable_width / cols
    row_height = kb_height / rows

    # Create blank image
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0,0,0))
    draw = ImageDraw.Draw(img)

    # For each row
    index = 0  # which key we are on (0..29)
    for r in range(rows):
        offset_x = margin_x + int(row_offsets[r] * key_width)  # pixel offset
        row_y = int(top_y + r * row_height)

        # For each column in this row
        for c in range(cols):
            letter = all_keys[r][c]
            x = int(offset_x + c * key_width)
            y = row_y
            w = int(key_width)
            h = int(row_height)

            if index == selected_key:
                fill_color = (255,255,255)  # white
                text_color = (0,0,0)        # black
            else:
                fill_color = (0,0,0)        # black
                text_color = (255,255,255)  # white

            # Draw key with white outline
            draw.rectangle(
                (x, y, x + w, y + h),
                fill=fill_color,
                outline=(255,255,255)
            )

            # Draw letter in center
            draw_centered_text(draw, x, y, w, h, letter, FONT, text_color)

            index += 1

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
    print("Displaying 2 tiles (vertical)...")
    colors_2_vertical = [
        (255, 255, 0),   # yellow top
        (0, 255, 0)      # green bottom
    ]
    display_two_tiles(colors_2_vertical, label="Channel")
    time.sleep(2)

    # 3) DEMO: 2 TILES (HORIZONTAL)
    print("Displaying 2 tiles (horizontal)...")
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
        print(f"Selecting tile index {i} = {menu_labels[i]}")
        display_six_tile_menu(selected_tile=i, labels=menu_labels)
        time.sleep(1)

    # 5) NEW DEMO: GERMAN KEYBOARD (BOTTOM 2/3) WITH OFFSET ROWS
    print("Displaying realistic German QWERTZ keyboard layout (bottom 2/3)...")
    # We'll iterate over all 30 letters
    for i in range(30):
        display_german_keyboard_realistic(selected_key=i)
        time.sleep(0.3)

    print("Done!")