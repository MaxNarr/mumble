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

# Choose a TTF font (adjust path/size if needed)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                  TEXT DIMENSION FALLBACK                      │
#  └────────────────────────────────────────────────────────────────┘
# For older Pillow versions lacking draw.textsize or font.getsize

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` 
    using a fallback via getmask().
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
#  │          EXISTING DEMOS: 4-TILE AND 2-TILE LAYOUTS            │
#  └────────────────────────────────────────────────────────────────┘

def display_four_tiles(tile_colors=None, label="Channel"):
    """
    Draws 4 tiles (2x2):
      +----------+----------+
      |  Tile 0  |  Tile 1  |
      +----------+----------+
      |  Tile 2  |  Tile 3  |
      +----------+----------+
    """
    if tile_colors is None:
        tile_colors = [(0,0,0)] * 4  # all black

    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 2

    coords = [
        (0,       0),      
        (tile_w,  0),
        (0,       tile_h),
        (tile_w,  tile_h)
    ]

    for i, (tx, ty) in enumerate(coords):
        color = tile_colors[i]
        draw.rectangle((tx, ty, tx + tile_w, ty + tile_h), fill=color)
        draw_centered_text(draw, tx, ty, tile_w, tile_h, label, FONT, (255,255,255))

    disp.display(img)


def display_two_tiles(tile_colors=None, label="Channel"):
    """
    Draws 2 tiles (vertical):
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


def display_two_tiles_side_by_side(tile_colors=None, label="Channel"):
    """
    Draws 2 tiles (horizontal):
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
#  │      NEW: 6-TILE MENU (2 COLUMNS x 3 ROWS) + SELECTION        │
#  └────────────────────────────────────────────────────────────────┘

def display_six_tile_menu(selected_tile=0, labels=None):
    """
    Draws a 6-tile menu in 2 columns x 3 rows:
    
      +---------+---------+
      |   0     |    1    |
      +---------+---------+
      |   2     |    3    |
      +---------+---------+
      |   4     |    5    |
      +---------+---------+
    
    Each tile has:
      - A white border
      - A black background w/ white text if NOT selected
      - A white background w/ black text if SELECTED
      
    Arguments:
      selected_tile (int) - which tile index (0-5) is highlighted
      labels (list)       - 6 strings for each tile, or None if you want defaults
    """
    if labels is None:
        # Default labels if none supplied
        labels = [f"Item {i+1}" for i in range(6)]

    # Create blank image
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = WIDTH // 2
    tile_h = HEIGHT // 3

    # Coordinates for each tile
    # Row-major order: 
    # 0 -> (0,0),    1 -> (tile_w,0)
    # 2 -> (0,tile_h), 3 -> (tile_w, tile_h)
    # 4 -> (0,2*tile_h), 5 -> (tile_w, 2*tile_h)
    tile_coords = []
    index = 0
    for row in range(3):
        for col in range(2):
            x = col * tile_w
            y = row * tile_h
            tile_coords.append((x, y))
            index += 1

    # Draw each tile
    for i in range(6):
        tx, ty = tile_coords[i]

        if i == selected_tile:
            # SELECTED: white background, black text
            fill_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            # NOT SELECTED: black background, white text
            fill_color = (0, 0, 0)
            text_color = (255, 255, 255)

        # Draw tile rectangle with a white outline
        draw.rectangle(
            (tx, ty, tx + tile_w, ty + tile_h), 
            fill=fill_color, 
            outline=(255, 255, 255)
        )

        # Draw centered text
        draw_centered_text(draw, tx, ty, tile_w, tile_h, labels[i], FONT, text_color)

    # Send image to display
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
    time.sleep(3)

    # 2) DEMO: 2 TILES (VERTICAL)
    print("Displaying 2 tiles vertically...")
    colors_2_vertical = [
        (255, 255, 0),   # yellow top
        (0, 255, 0)      # green bottom
    ]
    display_two_tiles(colors_2_vertical, label="Channel")
    time.sleep(3)

    # 3) DEMO: 2 TILES (HORIZONTAL)
    print("Displaying 2 tiles horizontally...")
    colors_2_horizontal = [
        (255, 0, 255),   # magenta left
        (0, 255, 255)    # cyan right
    ]
    display_two_tiles_side_by_side(colors_2_horizontal, label="Channel")
    time.sleep(3)

    # 4) NEW DEMO: 6-TILE MENU 
    print("Displaying 6-tile menu with selection...")
    menu_labels = ["Option A", "Option B", "Option C", "Option D", "Option E", "Option F"]
    
    # Iterate through each tile (0-5) and select it
    for i in range(6):
        print(f"Selecting tile index {i} ({menu_labels[i]})")
        display_six_tile_menu(selected_tile=i, labels=menu_labels)
        time.sleep(1)

    print("Done!")