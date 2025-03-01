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

# Smaller font to help fit keys
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
    Draw `text` centered in rectangle (x, y, w, h).
    """
    text_w, text_h = get_text_dimensions(text, font)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │          DEMOS: 4-TILE, 2-TILE, SIDE-BY-SIDE, 6-MENU           │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
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
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 2

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT

    left_color, right_color = tile_colors

    draw.rectangle((0, 0, tile_w, tile_h), fill=left_color)
    draw_centered_text(draw, 0, 0, tile_w, tile_h, label, FONT)

    draw.rectangle((tile_w, 0, WIDTH, tile_h), fill=right_color)
    draw_centered_text(draw, tile_w, 0, tile_w, tile_h, label, FONT)

    disp.display(img)


def display_six_tile_menu(selected_tile=0, labels=None):
    if labels is None:
        labels = [f"Item {i+1}" for i in range(6)]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 3

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
            fill_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            fill_color = (0, 0, 0)
            text_color = (255, 255, 255)

        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h),
                       fill=fill_color,
                       outline=(255,255,255))
        draw_centered_text(draw, tx, ty, tile_w, tile_h, labels[i], FONT, text_color)

    disp.display(img)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │  NEW: GERMAN "QWERTZ" WITHOUT UMLAUTS, ROW 2 FURTHER RIGHT    │
#  └────────────────────────────────────────────────────────────────┘

def display_german_keyboard_realistic(selected_key=0):
    """
    Bottom 2/3 of screen; row 2 is further to the right.
    No 'Ä', 'Ü', 'Ö', 'ß'.
    
    Layout: 3 rows, with different key counts:
      Row 0: 10 letters = Q W E R T  Z U I O P
      Row 1:  9 letters = A S D F G  H J K L
      Row 2:  7 letters = Y X C V B  N M

    row_offsets = [0.0, 0.5, 1.0] to stagger them horizontally.
    """

    row0 = ["Q","W","E","R","T","Z","U","I","O","P"]       # 10
    row1 = ["A","S","D","F","G","H","J","K","L"]           # 9
    row2 = ["Y","X","C","V","B","N","M"]                   # 7
    rows_data = [row0, row1, row2]

    row_offsets = [0.0, 0.3, 0.6]  # shift row2 more to the right
    total_rows = len(rows_data)    # 3

    # Keyboard area = bottom 2/3
    top_y = HEIGHT // 3
    kb_height = (HEIGHT * 2) // 3  # integer

    # We'll leave some horizontal margin on each side
    margin_x = 0 #WIDTH // 20
    usable_width = WIDTH #- 2 * margin_x

    # Create blank image
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0,0,0))
    draw = ImageDraw.Draw(img)

    # We'll loop each row, compute that row's key width from how many letters
    # are in that row, so it fills ~usable_width.
    # Each row has a fraction offset (row_offsets[r]) in "key-width units."
    index = 0  # which key is being selected (0..25 in total)

    for r, row_letters in enumerate(rows_data):
        # number of columns in this row
        num_cols = len(row_letters)
        # each key's size
        row_y = int(top_y + r * (kb_height / total_rows))
        row_h = int(kb_height / total_rows)
        key_width = usable_width / num_cols
        offset_pixels = int(row_offsets[r] * key_width)  # shift row by fraction of one key width

        for c, letter in enumerate(row_letters):
            x = margin_x + offset_pixels + int(c * key_width)
            y = row_y
            w = int(key_width)
            h = row_h

            # Check if this is the selected key
            if index == selected_key:
                fill_color = (255,255,255)  # white
                text_color = (0,0,0)        # black
            else:
                fill_color = (0,0,0)        # black
                text_color = (255,255,255)

            # Draw key w/ white outline
            draw.rectangle(
                (x, y, x + w, y + h),
                fill=fill_color,
                outline=(255,255,255)
            )

            # Center letter text
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
        display_six_tile_menu(selected_tile=i, labels=menu_labels)
        time.sleep(1)

    # 5) DEMO: NEW GERMAN KEYBOARD (NO UMLAUTS), SHIFT ROW 2 RIGHT
    print("Displaying 26-letter German QWERTZ layout, last row further right...")
    # Iterate through all 26 letters so user sees each one selected
    total_letters = 26
    for sel_index in range(total_letters):
        display_german_keyboard_realistic(selected_key=sel_index)
        time.sleep(0.4)

    print("Done!")
