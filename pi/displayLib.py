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

# A base font for smaller text (volume, etc.)
BASE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
VOLUME_FONT = ImageFont.truetype(BASE_FONT_PATH, 8)  # For volume or "muted"
MIN_NAME_FONT_SIZE = 14
MAX_NAME_FONT_SIZE = 30  # channel name tries up to size 30

def current_blink_state() -> bool:
    """
    Returns True if we should draw the 'on' state of a blink,
    or False if we should draw the 'off' state.
    We toggle every BLINK_INTERVAL seconds.
    """
    now = time.time()
    cycle = math.floor(now / BLINK_INTERVAL)
    # Even cycle => 'on', odd cycle => 'off'
    return (cycle % 2) == 0

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` using getmask().
    This works even on older Pillow versions lacking font.getsize/draw.textsize.
    """
    mask = font.getmask(text)
    return mask.size


#
#  ┌──────────────────────────────────────────────────────────┐
#  │  2) TILE CLASS                                          │
#  └──────────────────────────────────────────────────────────┘

class Tile:
    """
    One tile with various states:
      - name (string)
      - volume (0..10; 0 => muted => "muted" red box)
      - is_called (bool => blink entire tile red)
      - selected (bool => white background, black text)
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
        Draw the tile in rectangle (x,y,w,h).
        Behavior priorities (highest to lowest):
          1) selected => white bg, black text
          2) is_called => blink red
          3) talking => green
          4) else => black bg, white text

        Name at top (largest possible font up to MAX_NAME_FONT_SIZE).
        Volume or "muted" in a smaller font (VOLUME_FONT) below the name.
        "muted" has a red rectangle behind the text.

        We also add a white outline around the tile.
        """
        # 1) Determine background + text color
        bg_color = (0,0,0)
        text_color = (255,255,255)

        if self.selected:
            bg_color = (255,255,255)   # white
            text_color = (0,0,0)       # black
        else:
            if self.is_called:
                # blink red if is_called
                if current_blink_state():
                    bg_color = (0,0,255)   # red
                else:
                    bg_color = (0,0,0)     # black
                text_color = (255,255,255)
            elif self.talking:
                bg_color = (0,128,0)      # green
                text_color = (255,255,255)
            else:
                bg_color = (0,0,0)        # black
                text_color = (255,255,255)

        # 2) Fill the tile background and draw a white frame
        draw_obj.rectangle((x, y, x + w, y + h),
                           fill=bg_color,
                           outline=(255,255,255))

        # 3) Draw the tile name in the top portion
        #    We'll attempt different font sizes from MAX_NAME_FONT_SIZE down.
        name_font_size = MAX_NAME_FONT_SIZE
        best_font = None
        while name_font_size >= MIN_NAME_FONT_SIZE:
            trial_font = ImageFont.truetype(BASE_FONT_PATH, name_font_size)
            tw, th = get_text_dimensions(self.name, trial_font)
            if tw <= w and th <= (h // 2):
                best_font = trial_font
                break
            name_font_size -= 1

        if best_font is None:
            # fallback if none found
            best_font = ImageFont.truetype(BASE_FONT_PATH, MIN_NAME_FONT_SIZE)
            tw, th = get_text_dimensions(self.name, best_font)
        else:
            tw, th = get_text_dimensions(self.name, best_font)

        # place near top center
        name_x = x + (w - tw)//2
        name_y = y + 2
        draw_obj.text((name_x, name_y), self.name, font=best_font, fill=text_color)

        # 4) Draw volume or "muted" below the name
        if self.volume == 0:
            # Show "muted" with red background
            msg = "muted"
            msg_w, msg_h = get_text_dimensions(msg, VOLUME_FONT)
            vol_x = x + (w - msg_w)//2
            vol_y = name_y + th + 5

            pad = 2
            draw_obj.rectangle((vol_x - pad, vol_y - pad,
                                vol_x + msg_w + pad, vol_y + msg_h + pad),
                               fill=(0,0,255))  # red behind "muted"
            draw_obj.text((vol_x, vol_y), msg, font=VOLUME_FONT, fill=(255,255,255))
        else:
            # show "Volume: X"
            msg = f"Vol.: {self.volume}"
            msg_w, msg_h = get_text_dimensions(msg, VOLUME_FONT)
            vol_x = x + (w - msg_w)//2
            vol_y = name_y + th + 5
            draw_obj.text((vol_x, vol_y), msg, font=VOLUME_FONT, fill=text_color)


#
#  ┌──────────────────────────────────────────────────────────┐
#  │  3) TILEMANAGER CLASS                                   │
#  └──────────────────────────────────────────────────────────┘

class TileManager:
    """
    Manages a list of Tile objects, supports paging & 2 layouts:
      layout="4" => 4 tiles/page (2x2)
      layout="2" => 2 tiles/page side-by-side
    The top 1/4 of screen is used for displaying the page number,
    while the bottom 3/4 is used for tiles.
    """

    def __init__(self, tiles):
        """
        tiles: list of Tile objects
        """
        self.tiles = tiles

    def render(self, page_number: int = 0, layout: str = "4"):
        """
        Draw a page of tiles onto the ST7735.

        layout="4" => 4 tiles/page (indexes: page*4..page*4+3)
        layout="2" => 2 tiles/page (indexes: page*2..page*2+1)
        """
        # 1) Which subset of tiles are on this page?
        if layout == "4":
            start_idx = page_number * 4
            end_idx = start_idx + 4
        elif layout == "2":
            start_idx = page_number * 2
            end_idx = start_idx + 2
        else:
            raise ValueError("Invalid layout. Use '4' or '2'.")

        page_tiles = self.tiles[start_idx:end_idx]

        # 2) Create new image
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)

        # 2a) Draw the page number at the top 1/4 in big white text
        top_bar_h = DISPLAY_HEIGHT // 4  # top 1/4
        page_text = f"Page {page_number}"
        # We'll just center it horizontally & vertically in that top region
        page_font = ImageFont.truetype(BASE_FONT_PATH, 18)
        ptw, pth = get_text_dimensions(page_text, page_font)
        px = (DISPLAY_WIDTH - ptw) // 2
        py = (top_bar_h - pth) // 2
        draw.text((px, py), page_text, font=page_font, fill=(255,255,255))

        # 3) The bottom 3/4 region is for tiles
        #    We'll define an offset_y for tiles
        tile_area_y = top_bar_h
        tile_area_h = DISPLAY_HEIGHT - top_bar_h

        # 4) Layout calculations
        if layout == "4":
            # 2x2 in bottom region
            tile_w = DISPLAY_WIDTH // 2
            tile_h = tile_area_h // 2
            coords = [
                (0,              tile_area_y),
                (tile_w,         tile_area_y),
                (0,              tile_area_y + tile_h),
                (tile_w,         tile_area_y + tile_h),
            ]
        else:
            # layout="2" => 2 wide x 1 tall in bottom region
            tile_w = DISPLAY_WIDTH // 2
            tile_h = tile_area_h
            coords = [
                (0, tile_area_y),
                (tile_w, tile_area_y),
            ]

        # 5) Draw each tile
        for i, tile in enumerate(page_tiles):
            if i < len(coords):
                x, y = coords[i]
                tile.draw(draw, x, y, tile_w, tile_h)

        disp.display(img)
