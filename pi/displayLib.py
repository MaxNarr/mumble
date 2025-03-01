#!/usr/bin/env python3

import time
from PIL import Image, ImageDraw, ImageFont
import st7735
import math


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


DISPLAY_WIDTH = disp.width
DISPLAY_HEIGHT = disp.height

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

    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = DISPLAY_WIDTH // 2
    tile_h = DISPLAY_HEIGHT // 2
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

    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = DISPLAY_WIDTH
    tile_h = DISPLAY_HEIGHT // 2
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

    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = DISPLAY_WIDTH // 2
    tile_h = DISPLAY_HEIGHT

    # Left tile
    draw.rectangle((0, 0, tile_w, tile_h), fill=tile_colors[0])
    draw_centered_text(draw, 0, 0, tile_w, tile_h, label, FONT)

    # Right tile
    draw.rectangle((tile_w, 0, DISPLAY_WIDTH, tile_h), fill=tile_colors[1])
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

    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    tile_w = DISPLAY_WIDTH // 2
    tile_h = DISPLAY_HEIGHT // 3

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
    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Text field area
    text_field_height = DISPLAY_HEIGHT // 3
    draw.rectangle((0, 0, DISPLAY_WIDTH, text_field_height),
                   outline=(255,255,255), fill=(0,0,0))
    draw_centered_text(draw, 0, 0, DISPLAY_WIDTH, text_field_height, typed_text, FONT, (255,255,255))

    # Keyboard area
    kb_top_y = text_field_height
    kb_height = DISPLAY_HEIGHT - text_field_height
    margin_x = 0
    usable_width = DISPLAY_WIDTH - 20  # keep a 20-pixel margin on the right

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

# We’ll define a "blink" rate for is_called
BLINK_INTERVAL = 0.5  # seconds

# A base font for volume/muted
BASE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BASE_FONT = ImageFont.truetype(BASE_FONT_PATH, 14)  # used for volume text
MIN_NAME_FONT_SIZE = 10  # minimal fallback for tile name
MAX_NAME_FONT_SIZE = 30  # maximum trial for tile name

def current_blink_state() -> bool:
    """
    Returns True if we should draw the 'on' state of a blink,
    or False if we should draw the 'off' state.
    We toggle every BLINK_INTERVAL seconds.
    """
    t = time.time()
    cycle = math.floor((t / BLINK_INTERVAL))  # integer stepping
    return (cycle % 2) == 0

#
# ┌──────────────────────────────────────────────────────────┐
# │  2) TILE CLASS                                          │
# └──────────────────────────────────────────────────────────┘

class Tile:
    """
    Represents one tile with various states:
      - name (string)
      - volume (0..10; 0 => muted => "muted" red box)
      - is_called (bool => blink entire tile red)
      - selected (bool => override colors => white bg, black font)
      - talking (bool => entire tile green)
    """

    def __init__(self, name: str, volume: int = 5,
                 is_called: bool = False,
                 selected: bool = False,
                 talking: bool = False):
        self.name = name
        self.volume = volume
        self.is_called = is_called
        self.selected = selected
        self.talking = talking

    def set_volume(self, new_volume: int):
        """Update volume (0..10). If 0 => tile is muted."""
        self.volume = max(0, min(10, new_volume))

    def draw(self, draw_obj: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int):
        """
        Draw the tile in the rectangle (x, y, w, h).
        Behavior:
          1) If selected => white bg, black font.
          2) Else if is_called => blink red background.
          3) Else if talking => green background.
          4) Else => black background, white font.

          - Name at the top, as large as fits horizontally.
          - Volume or "muted" below the name in a smaller font.
          - "muted" text has a red rectangle behind it (white text).
        """
        # 1) Determine tile background & text color
        bg_color = (0,0,0)
        text_color = (255,255,255)

        if self.selected:
            bg_color = (255,255,255)
            text_color = (0,0,0)
        else:
            if self.is_called:
                # BLINK in red if is_called
                if current_blink_state():
                    bg_color = (255,0,0)  # red
                else:
                    bg_color = (0,0,0)    # black or "off"
                text_color = (255,255,255)
            elif self.talking:
                bg_color = (0,128,0)  # green
                text_color = (255,255,255)
            else:
                bg_color = (0,0,0)
                text_color = (255,255,255)

        # Fill the tile background
        draw_obj.rectangle((x, y, x + w, y + h), fill=bg_color)

        # 2) Draw the tile name, fitted at the top
        # We'll attempt font sizes from MAX_NAME_FONT_SIZE down to MIN_NAME_FONT_SIZE
        # until we find one that fits horizontally in 'w'.
        name_font_size = MAX_NAME_FONT_SIZE
        while name_font_size >= MIN_NAME_FONT_SIZE:
            trial_font = ImageFont.truetype(BASE_FONT_PATH, name_font_size)
            text_w, text_h = trial_font.getsize(self.name)
            # If it fits in width, and not too tall for half the tile, accept it
            # (We assume the name takes up ~ half the tile height at most.)
            if text_w <= w and text_h <= (h // 2):
                # Found a fitting font
                break
            name_font_size -= 1
        else:
            # If we exit the while without break => fallback
            trial_font = ImageFont.truetype(BASE_FONT_PATH, MIN_NAME_FONT_SIZE)
            text_w, text_h = trial_font.getsize(self.name)

        # Center horizontally, place near top (some padding)
        name_x = x + (w - text_w)//2
        name_y = y + 2  # small top margin
        draw_obj.text((name_x, name_y), self.name, font=trial_font, fill=text_color)

        # 3) Draw the volume or "muted"
        # We'll do in base font or smaller near the bottom half
        vol_font = BASE_FONT
        if self.volume == 0:
            # muted => show a red box with "muted" in white text
            msg = "muted"
            msg_w, msg_h = vol_font.getsize(msg)
            # Let's place it below the name
            vol_x = x + (w - msg_w)//2
            vol_y = name_y + text_h + 5  # a little spacing from name

            # red background for the text region
            red_pad = 2
            draw_obj.rectangle(
                (vol_x - red_pad, vol_y - red_pad,
                 vol_x + msg_w + red_pad, vol_y + msg_h + red_pad),
                fill=(255,0,0)
            )
            # white text
            draw_obj.text((vol_x, vol_y), msg, font=vol_font, fill=(255,255,255))

        else:
            # show "Volume: X"
            msg = f"Volume: {self.volume}"
            msg_w, msg_h = vol_font.getsize(msg)
            vol_x = x + (w - msg_w)//2
            vol_y = name_y + text_h + 5
            draw_obj.text((vol_x, vol_y), msg, font=vol_font, fill=text_color)


#
# ┌──────────────────────────────────────────────────────────┐
# │  3) TILEMANAGER CLASS                                   │
# └──────────────────────────────────────────────────────────┘

class TileManager:
    """
    Manages a list of Tiles. Supports paging and two layout modes:
      - layout="4": 4 tiles/page (2 wide x 2 high)
      - layout="2": 2 tiles/page (2 wide x 1 high)
    """

    def __init__(self, tiles):
        """
        tiles: a list of Tile objects
        """
        self.tiles = tiles

    def render(self, page_number: int = 0, layout: str = "4"):
        """
        Draws a page of tiles onto the ST7735 display.

        layout="4" => 4 tiles per page in a 2×2 grid
          indexes: page_number*4 .. page_number*4+3
        layout="2" => 2 tiles per page, side by side
          indexes: page_number*2 .. page_number*2+1
        """
        # 1) Determine which subset of tiles to draw
        if layout == "4":
            start_idx = page_number * 4
            end_idx = start_idx + 4
        elif layout == "2":
            start_idx = page_number * 2
            end_idx = start_idx + 2
        else:
            raise ValueError("Invalid layout. Use '4' or '2'.")

        # slice the list
        page_tiles = self.tiles[start_idx:end_idx]
        if not page_tiles:
            # If page is empty, just draw blank
            img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0, 0, 0))
            disp.display(img)
            return

        # 2) Create a new image
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)

        # 3) Depending on layout, compute tile positions
        if layout == "4":
            # 2x2
            tile_w = DISPLAY_WIDTH // 2
            tile_h = DISPLAY_HEIGHT // 2
            # positions:
            coords = [
                (0,         0),
                (tile_w,    0),
                (0,         tile_h),
                (tile_w,    tile_h),
            ]
        else:
            # layout == "2": 2 side by side, full height
            tile_w = DISPLAY_WIDTH // 2
            tile_h = DISPLAY_HEIGHT
            coords = [
                (0, 0),
                (tile_w, 0),
            ]

        # 4) Draw each tile in its region
        for i, tile in enumerate(page_tiles):
            if i < len(coords):
                x, y = coords[i]
                tile.draw(draw, x, y, tile_w, tile_h)

        # 5) Send to display
        disp.display(img)
