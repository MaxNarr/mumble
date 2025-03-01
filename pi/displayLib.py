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
    bgr=False,
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
VOLUME_FONT = ImageFont.truetype(BASE_FONT_PATH, 10)  # For volume or "muted"
MIN_NAME_FONT_SIZE = 11
MAX_NAME_FONT_SIZE = 30  # channel name tries up to size 30

def current_blink_state() -> bool:
    """
    Returns True if we should draw the 'on' (red) state,
    or False if we should draw the 'off' (black) state.
    We toggle every BLINK_INTERVAL seconds.
    """
    now = time.time()
    cycle = math.floor(now / BLINK_INTERVAL)
    return (cycle % 2) == 0

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` using getmask().
    (Fallback for older PIL versions lacking font.getsize or draw.textsize.)
    """
    mask = font.getmask(text)
    return mask.size


#
#  ┌──────────────────────────────────────────────────────────┐
#  │  TILE CLASS                                             │
#  └──────────────────────────────────────────────────────────┘

class Tile:
    """
    One tile with states:
      - name
      - volume (-5..5; -6 => muted => "muted" red box)
      - is_called => blink red
      - selected => white bg, black text
      - talking => green bg
    """

    def __init__(self, name: str,
                 volume: int = 0,
                 is_called: bool = False,
                 selected: bool = False,
                 talking: bool = False,
                 id: int = 0):
        self.name = name
        self.volume = volume
        self.is_called = is_called
        self.selected = selected
        self.talking = talking
        self.id = id

    def set_volume(self, new_volume: int):
        import mumbleRPC
        self.volume = max(-6, min(5, new_volume))
        mumbleRPC.listen(self)


    def draw(self, draw_obj: ImageDraw.ImageDraw,
             x: int, y: int, w: int, h: int):
        # Decide background + text colors
        bg_color = (0,0,0)
        text_color = (255,255,255)

        if self.selected:
            # Highest priority: selected
            bg_color = (255,255,255)  # white
            text_color = (0,0,0)      # black
        else:
            if self.is_called:
                # blink red if is_called
                if current_blink_state():
                    bg_color = (255,0,0)  # red
                else:
                    bg_color = (0,0,0)    # black
                text_color = (255,255,255)
            elif self.talking:
                bg_color = (0,128,0)     # green
                text_color = (255,255,255)
            else:
                bg_color = (0,0,0)
                text_color = (255,255,255)

        # Draw the tile background + white border
        draw_obj.rectangle((x, y, x+w, y+h),
                           fill=bg_color,
                           outline=(255,255,255))

                # Large name at top
        left_margin = 5
        right_margin = 5
        top_margin = 5

        # The maximum text width we allow (subtract left/right margins)
        max_text_width = w - left_margin - right_margin
        # The maximum text height is half the tile, minus the top margin
        max_text_height = (h // 2) - top_margin

        name_font_size = MAX_NAME_FONT_SIZE
        best_font = None

        while name_font_size >= MIN_NAME_FONT_SIZE:
            trial_font = ImageFont.truetype(BASE_FONT_PATH, name_font_size)
            tw, th = get_text_dimensions(self.name, trial_font)

            # Check if text width/height fit within our margins
            if tw <= max_text_width and th <= max_text_height:
                best_font = trial_font
                break
            name_font_size -= 1

        # Fallback if we never found a suitable size
        if best_font is None:
            best_font = ImageFont.truetype(BASE_FONT_PATH, MIN_NAME_FONT_SIZE)
            tw, th = get_text_dimensions(self.name, best_font)
        else:
            tw, th = get_text_dimensions(self.name, best_font)

        # Now place the text:
        # - x + left_margin is our "left edge"
        # - we center the text in the available horizontal space: max_text_width
        name_x = x + left_margin + (max_text_width - tw) // 2
        name_y = y + top_margin

        draw_obj.text((name_x, name_y), self.name, font=best_font, fill=text_color)


        # Then volume or muted
        if self.volume == -6:
            msg = "muted"
            msg_w, msg_h = get_text_dimensions(msg, VOLUME_FONT)
            vol_x = x + (w - msg_w)//2
            vol_y = name_y + th + 5
            pad = 2
            # red box behind "muted"
            draw_obj.rectangle((vol_x - pad, vol_y - pad,
                                vol_x + msg_w + pad, vol_y + msg_h + pad),
                               fill=(255,0,0))
            draw_obj.text((vol_x, vol_y), msg, font=VOLUME_FONT, fill=(255,255,255))
        else:
            if self.volume == 0:
                            msg = f"Vol.: Std."
            elif self.volume > 0:
                msg = f"Vol.: +{self.volume}"
            elif self.volume <0:    
                msg = f"Vol.: {self.volume}"

            msg_w, msg_h = get_text_dimensions(msg, VOLUME_FONT)
            vol_x = x + (w - msg_w)//2
            vol_y = name_y + th + 5
            draw_obj.text((vol_x, vol_y), msg, font=VOLUME_FONT, fill=text_color)


#
#  ┌──────────────────────────────────────────────────────────┐
#  │  TILEMANAGER CLASS                                      │
#  └──────────────────────────────────────────────────────────┘

class TileManager:
    """
    Manages a list of Tile objects with paging + layouts:
      layout="4" => 4 tiles/page (2x2)
      layout="2" => 2 tiles/page side-by-side

    The top 1/4 of screen is for a page bar. We also have a boolean
    page_selected => if True, we invert the bar colors.
    """

    def __init__(self, tiles):
        """
        tiles: list of Tile objects
        """
        self.tiles = tiles
        self.page_selected = False  # new state: highlight top bar if True
        self.tile_selected = 0  # index of selected tile

        # Keep track of the last page + layout used, so 'update()' can re-render
        self.last_page = 0
        self.last_layout = "4"

    def getTile(self, index: int = -1,autoselect=False)->Tile:
        if index == -1: 
            index=self.tile_selected
        return self.tiles[index]
    
    def nextTile(self, step:int=1, autoselect=False)->Tile:
        self.tile_selected= (self.tile_selected+step)%len(self.tiles)
        return self.getTile(autoselect)

    def select_page_bar(self, selected: bool):
        """Set whether the page bar is selected (inverted colors)."""
        self.page_selected = selected

    def render(self, page_number: int = 0, layout: str = "4"):
        """
        Draws the page of tiles onto ST7735. Also draws a page bar at the top.
        Save page_number + layout so we can re-call them in update().
        """
        self.last_page = page_number
        self.last_layout = layout

        # 1) Determine which tiles are on this page
        if layout == "4":
            start_idx = page_number * 4
            end_idx = start_idx + 4
        elif layout == "2":
            start_idx = page_number * 2
            end_idx = start_idx + 2
        else:
            raise ValueError("Invalid layout. Use '4' or '2'.")

        page_tiles = self.tiles[start_idx:end_idx]

        # 2) Create image
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)

        # 2a) Draw the page bar at top 1/4
        top_bar_h = DISPLAY_HEIGHT // 4
        page_text = f"Page {page_number}"

        # If page bar is selected => invert colors
        if self.page_selected:
            bar_bg = (255,255,255)
            bar_text_color = (0,0,0)
        else:
            bar_bg = (0,0,0)
            bar_text_color = (255,255,255)

        # Fill top bar
        draw.rectangle((0, 0, DISPLAY_WIDTH, top_bar_h), fill=bar_bg)

        # Center the text in that region
        page_font = ImageFont.truetype(BASE_FONT_PATH, 18)
        ptw, pth = get_text_dimensions(page_text, page_font)
        px = (DISPLAY_WIDTH - ptw)//2
        py = (top_bar_h - pth)//2
        draw.text((px, py), page_text, font=page_font, fill=bar_text_color)

        # 3) The bottom 3/4 region => tiles
        tile_area_y = top_bar_h
        tile_area_h = DISPLAY_HEIGHT - top_bar_h

        # 4) Layout positions
        if layout == "4":
            # 2x2
            tile_w = DISPLAY_WIDTH // 2
            tile_h = tile_area_h // 2
            coords = [
                (0,               tile_area_y),
                (tile_w,          tile_area_y),
                (0,               tile_area_y + tile_h),
                (tile_w,          tile_area_y + tile_h),
            ]
        else:
            # layout="2"
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

        # 6) Show it
        disp.display(img)

    def update(self):
        """
        Re-render the same page + layout as last time.
        Call this repeatedly to achieve blinking.
        """
        self.render(self.last_page, self.last_layout)