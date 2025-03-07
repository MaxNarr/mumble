#!/usr/bin/env python3

import time
import math
import spidev as SPI
from PIL import Image, ImageDraw, ImageFont
from enum import Enum

# Replace with your local ST7789 driver import
from DisplayST7789 import ST7789

CALLPHRASE = "calling"

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                DISPLAY / HARDWARE INITIALIZATION              │
#  └────────────────────────────────────────────────────────────────┘

disp = ST7789.ST7789()
disp.Init()
disp.clear()
disp.bl_DutyCycle(100)

DISPLAY_WIDTH = disp.width
DISPLAY_HEIGHT = disp.height

#
#  ┌───────────────────────────────────────────────────────────┐
#  │                    GLOBAL CONSTANTS                      │
#  └───────────────────────────────────────────────────────────┘

MINVOLUME = -2
MAXVOLUME = 2

BLINK_DURATION = 5
BLINK_INTERVAL = 0.5

BASE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = ImageFont.truetype(BASE_FONT_PATH, 14)
VOLUME_FONT = ImageFont.truetype(BASE_FONT_PATH, 10)
MIN_NAME_FONT_SIZE = 11
MAX_NAME_FONT_SIZE = 30

#
#  ┌───────────────────────────────────────────────────────────┐
#  │                 HELPER FUNCTIONS                         │
#  └───────────────────────────────────────────────────────────┘

def get_text_dimensions(text, font):
    """Return (width, height) for single-line text."""
    mask = font.getmask(text)
    return mask.size

def draw_centered_text(draw_obj, x, y, w, h, text, font, color=(255,255,255)):
    """Draw text centered in the rectangle (x, y, w, h)."""
    text_w, text_h = get_text_dimensions(text, font)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2
    draw_obj.text((text_x, text_y), text, font=font, fill=color)

def current_blink_state() -> bool:
    """Blink toggles every BLINK_INTERVAL seconds."""
    now = time.time()
    cycle = math.floor(now / BLINK_INTERVAL)
    return (cycle % 2) == 0


#
#  ┌───────────────────────────────────────────────────────────┐
#  │                       TILE CLASS                         │
#  └───────────────────────────────────────────────────────────┘

class Tile:
    """
    A tile can be placed in a page slot. Contains:
      - name
      - volume (-2..2; -3 => "muted")
      - is_calledByUser => triggers blinking
      - selected => highlight tile
      - talking => show green
      - id => identifier
    """
    def __init__(self, name: str,
                 volume: int = 0,
                 is_calledByUser: str = None,
                 selected: bool = False,
                 talking: bool = False,
                 id: int = 0):
        self.name = name
        self.volume = volume
        self.is_calledByUser = is_calledByUser
        self.selected = selected
        self.talking = talking
        self.id = id
        self.blink_start = None

    def set_volume(self, new_volume: int):
        import mumbleRPC
        self.volume = max(MINVOLUME-1, min(MAXVOLUME, new_volume))
        mumbleRPC.listen(self)
        print("Volume: " + str(self.volume))

    def call(self):
        import mumbleRPC
        mumbleRPC.call(self)
        self.is_calledByUser = CALLPHRASE

    def draw(self, draw_obj: ImageDraw.ImageDraw,
             x: int, y: int, w: int, h: int):
        """
        Draws the tile rectangle plus text. If 'selected', tile is white.
        If 'talking', tile is green. If 'is_calledByUser', it blinks red.
        """
        bg_color = (0, 0, 0)
        text_color = (255, 255, 255)

        if self.selected:
            bg_color = (255, 255, 255)
            text_color = (0, 0, 0)
        else:
            # handle blinking
            if self.is_calledByUser:
                if self.blink_start is None:
                    self.blink_start = time.time()
                if time.time() - self.blink_start < BLINK_DURATION:
                    if current_blink_state():
                        bg_color = (255, 0, 0)  # red
                    else:
                        bg_color = (0, 0, 0)
                else:
                    self.is_calledByUser = None
                    self.blink_start = None
                    bg_color = (0, 0, 0)
                text_color = (255, 255, 255)
            elif self.talking:
                bg_color = (0, 128, 0)
                text_color = (255, 255, 255)
            else:
                bg_color = (0, 0, 0)
                text_color = (255, 255, 255)

        draw_obj.rectangle((x, y, x+w, y+h), fill=bg_color, outline=(255, 255, 255))

        # Auto-fit the tile's name
        left_margin = 5
        right_margin = 5
        top_margin = 5

        max_text_width = w - left_margin - right_margin
        max_text_height = (h // 2) - top_margin

        name_font_size = MAX_NAME_FONT_SIZE
        best_font = None

        while name_font_size >= MIN_NAME_FONT_SIZE:
            trial_font = ImageFont.truetype(BASE_FONT_PATH, name_font_size)
            tw, th = get_text_dimensions(self.name, trial_font)
            if tw <= max_text_width and th <= max_text_height:
                best_font = trial_font
                break
            name_font_size -= 1

        if best_font is None:
            best_font = ImageFont.truetype(BASE_FONT_PATH, MIN_NAME_FONT_SIZE)
            tw, th = get_text_dimensions(self.name, best_font)
        else:
            tw, th = get_text_dimensions(self.name, best_font)

        name_x = x + left_margin + (max_text_width - tw) // 2
        name_y = y + top_margin
        draw_obj.text((name_x, name_y), self.name, font=best_font, fill=text_color)

        # Volume or "muted"
        if self.volume == MINVOLUME - 1:
            msg = "muted"
            msg_w, msg_h = get_text_dimensions(msg, VOLUME_FONT)
            vol_x = x + (w - msg_w) // 2
            vol_y = name_y + th + 5
            pad = 2
            draw_obj.rectangle((vol_x - pad, vol_y - pad,
                                vol_x + msg_w + pad, vol_y + msg_h + pad),
                               fill=(255, 0, 0))
            draw_obj.text((vol_x, vol_y), msg, font=VOLUME_FONT, fill=(255, 255, 255))
        else:
            if self.volume == 0:
                msg = "Vol.: Std."
            elif self.volume > 0:
                msg = f"Vol.: +{self.volume}"
            else:
                msg = f"Vol.: {self.volume}"
            msg_w, msg_h = get_text_dimensions(msg, VOLUME_FONT)
            vol_x = x + (w - msg_w) // 2
            vol_y = name_y + th + 5
            draw_obj.text((vol_x, vol_y), msg, font=VOLUME_FONT, fill=text_color)


#
#  ┌───────────────────────────────────────────────────────────┐
#  │                 "EMPTY"/PLUS TILE CLASS                  │
#  └───────────────────────────────────────────────────────────┘

class EmptyTile(Tile):
    """
    This tile is displayed if there's no actual tile in that slot.
    It just shows a plus sign to indicate you can add something.
    """
    def __init__(self):
        super().__init__(name="+", id=-1)

    def draw(self, draw_obj: ImageDraw.ImageDraw,
             x: int, y: int, w: int, h: int):
        # We'll just draw a plus sign in the center
        bg_color = (255, 255, 255) if self.selected else (0, 0, 0)
        text_color = (0, 0, 0) if self.selected else (255, 255, 255)
        draw_obj.rectangle((x, y, x+w, y+h), fill=bg_color, outline=(255, 255, 255))
        draw_centered_text(draw_obj, x, y, w, h, "+", FONT, text_color)


#
# ┌────────────────────────────────────────────────────────────┐
# │  SCROLLABLE LIST VIEW (for Tile Settings, Gen. Settings)  │
# └────────────────────────────────────────────────────────────┘

class ScrollableListView:
    """
    A generic vertical-list view that displays items as text rows.
    'items' is a list of strings. 'selected_index' is the current row selection.
    The user can scroll up/down. The user can select an item with 'middle button'.
    The maximum items displayed per "screen" is determined by the row height.
    """
    def __init__(self, items, title=""):
        self.items = items
        self.selected_index = 0
        self.title = title
        # We'll compute how many items can fit on-screen
        self.item_height = 25  # for example
        self.scroll_offset = 0  # index of the topmost item displayed

    def move_up(self):
        if self.selected_index > 0:
            self.selected_index -= 1
        # Adjust scroll offset
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index

    def move_down(self):
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
        # If the selection goes beyond the bottom displayed item,
        # shift the window
        max_items_on_screen = (DISPLAY_HEIGHT // self.item_height) - 1  # minus 1 if we want a title
        if self.selected_index > self.scroll_offset + max_items_on_screen:
            self.scroll_offset = self.selected_index - max_items_on_screen

    def render(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)

        # Draw title at top
        title_height = 25
        draw.rectangle((0, 0, DISPLAY_WIDTH, title_height), fill=(255,255,255))
        draw_centered_text(draw, 0, 0, DISPLAY_WIDTH, title_height, self.title, FONT, (0,0,0))

        # Start drawing items below title
        y_start = title_height
        # how many items fit
        max_visible = (DISPLAY_HEIGHT - title_height) // self.item_height

        visible_items = self.items[self.scroll_offset:self.scroll_offset + max_visible]

        for idx, item_text in enumerate(visible_items):
            actual_index = self.scroll_offset + idx
            y = y_start + idx * self.item_height
            # highlight if selected
            if actual_index == self.selected_index:
                bg = (255, 255, 255)
                fg = (0, 0, 0)
            else:
                bg = (0, 0, 0)
                fg = (255, 255, 255)
            draw.rectangle((0, y, DISPLAY_WIDTH, y + self.item_height), fill=bg)
            draw_centered_text(draw, 0, y, DISPLAY_WIDTH, self.item_height, item_text, FONT, fg)

        disp.ShowImage(img)

    def get_selected_item(self):
        if len(self.items) == 0:
            return None
        return self.items[self.selected_index]


#
#  ┌───────────────────────────────────────────────────────────┐
#  │                UI STATE MACHINE SETUP                    │
#  └───────────────────────────────────────────────────────────┘

class UIState(Enum):
    PAGE_VIEW = 1
    TILE_SETTINGS = 2
    GENERAL_SETTINGS = 3
    EDIT_DISPLAY_NAME = 4
    EDIT_IP = 5
    # etc...


class UIManager:
    """
    Handles what screen we are on, manages pages of tiles,
    handles the tile settings list, general settings, etc.
    """

    def __init__(self, all_tiles):
        # A pool of all possible tiles (besides "EmptyTile")
        self.all_tiles = all_tiles

        # We'll store pages as a list of lists.
        # Each page has 6 slots (2x3). Each slot is either a Tile or an EmptyTile.
        self.pages = []
        # Create the first page with all empty
        self.pages.append([EmptyTile() for _ in range(6)])
        self.selected_page_index = 0
        self.selected_tile_index = 0  # which of the 6 slots on the current page is selected

        # Current UI state
        self.state = UIState.PAGE_VIEW

        # For the scrollable list (TileSettings, GeneralSettings)
        self.tile_settings_view = None
        self.general_settings_view = None

        # Some dummy data for general settings
        self.display_name = "My Pi"
        self.ip_address = "192.168.0.100"
        self.use_dhcp = True

        self.init_general_settings_view()

    def init_general_settings_view(self):
        # A list of items for general settings
        # We'll store them as strings for simplicity
        items = ["Display Name", "IP Settings"]
        # We could add more items here, e.g. "Audio Settings", etc.
        self.general_settings_view = ScrollableListView(items, title="General Settings")

    #
    # ───────────────────────────────── PAGE VIEW ─────────────────────────────────
    #

    def render_page_view(self):
        """
        Draw the current page of 2x3 tiles, with the selected tile highlighted.
        If we have multiple pages, show some indicator at the top bar maybe.
        """
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)

        # Optionally draw a top bar with the page number
        top_bar_h = 24
        draw.rectangle((0, 0, DISPLAY_WIDTH, top_bar_h), fill=(255,255,255))
        page_text = f"Page {self.selected_page_index+1}"
        draw_centered_text(draw, 0, 0, DISPLAY_WIDTH, top_bar_h, page_text, FONT, (0,0,0))

        # 2x3 layout
        tile_area_y = top_bar_h
        tile_area_h = DISPLAY_HEIGHT - top_bar_h
        tile_w = DISPLAY_WIDTH // 2
        tile_h = tile_area_h // 3

        coords = []
        for row in range(3):
            for col in range(2):
                x = col * tile_w
                y = tile_area_y + row * tile_h
                coords.append((x, y))

        # Mark the selected slot
        page = self.pages[self.selected_page_index]

        # Draw each tile
        for i in range(6):
            tile = page[i]
            if i == self.selected_tile_index:
                tile.selected = True
            else:
                tile.selected = False

            x, y = coords[i]
            tile.draw(draw, x, y, tile_w, tile_h)

        disp.ShowImage(img)

    #
    # ───────────────────────────── TILE SETTINGS ─────────────────────────────
    #

    def enter_tile_settings_view(self):
        """
        Build a list of items: "Empty", all tile names, and "Back".
        Use the ScrollableListView to let the user pick one.
        """
        # We'll build the list in this order: "Empty", <all tile names>, "Back"
        item_names = ["Empty"]
        for t in self.all_tiles:
            item_names.append(t.name)
        item_names.append("Back")
        self.tile_settings_view = ScrollableListView(item_names, title="Select Tile")
        self.state = UIState.TILE_SETTINGS

    def render_tile_settings_view(self):
        self.tile_settings_view.render()

    def select_in_tile_settings_view(self):
        """User pressed 'middle' on a tile in the settings list."""
        chosen = self.tile_settings_view.get_selected_item()
        if chosen is None:
            return

        # If "Back", or if we are at the last item
        if chosen == "Back" or (self.tile_settings_view.selected_index == len(self.tile_settings_view.items) - 1):
            # Just go back
            self.state = UIState.PAGE_VIEW
            return

        # If "Empty"
        if chosen == "Empty":
            self.set_current_page_tile(EmptyTile())
            self.state = UIState.PAGE_VIEW
            return

        # Otherwise, find the tile in self.all_tiles
        for tile_obj in self.all_tiles:
            if tile_obj.name == chosen:
                # Assign that tile to the selected slot
                # (We might want to create a new instance if the tile is mutable.)
                # For simplicity, we just set the reference.
                # If you need a new instance, you'd do something like: Tile(tile_obj.name, etc.)
                self.set_current_page_tile(tile_obj)
                break

        self.state = UIState.PAGE_VIEW

    def set_current_page_tile(self, tile):
        self.pages[self.selected_page_index][self.selected_tile_index] = tile

    #
    # ───────────────────────────── GENERAL SETTINGS ─────────────────────────────
    #

    def open_general_settings(self):
        """Called when in PAGE_VIEW and user presses 'pushbutton1' (the back button)."""
        self.state = UIState.GENERAL_SETTINGS

    def render_general_settings_view(self):
        self.general_settings_view.render()

    def select_in_general_settings_view(self):
        chosen = self.general_settings_view.get_selected_item()
        if chosen == "Display Name":
            self.state = UIState.EDIT_DISPLAY_NAME
            return
        elif chosen == "IP Settings":
            self.state = UIState.EDIT_IP
            return
        # Potentially more items here

    #
    # ───────────────────────────── EDIT DISPLAY NAME ─────────────────────────────
    #
    # This would be where you show the keyboard. For simplicity, we just show a placeholder.

    def render_edit_display_name(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)
        msg = f"Editing display name:\n{self.display_name}\n(TODO: Implement keyboard screen)"
        draw.text((5, 5), msg, font=FONT, fill=(255,255,255))
        disp.ShowImage(img)

    #
    # ───────────────────────────── EDIT IP SETTINGS ─────────────────────────────
    #

    def render_edit_ip(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)
        msg = "IP Settings:\n"
        msg += f"Current IP: {self.ip_address}\n"
        msg += "DHCP: " + ("On" if self.use_dhcp else "Off") + "\n"
        msg += "(TODO: Implement numpad & DHCP toggle)\n"
        draw.text((5,5), msg, font=FONT, fill=(255,255,255))
        disp.ShowImage(img)

    #
    # ─────────────────────────────────── RENDER ──────────────────────────────────
    #

    def render(self):
        if self.state == UIState.PAGE_VIEW:
            self.render_page_view()
        elif self.state == UIState.TILE_SETTINGS:
            self.render_tile_settings_view()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.render_general_settings_view()
        elif self.state == UIState.EDIT_DISPLAY_NAME:
            self.render_edit_display_name()
        elif self.state == UIState.EDIT_IP:
            self.render_edit_ip()
        # Extend for more states as needed

    #
    # ──────────────────────────── EVENT HANDLERS ───────────────────────────────
    #

    def on_joystick_up(self):
        """User moved joystick up."""
        if self.state == UIState.PAGE_VIEW:
            # Move the selection up one row in the 2x3 grid
            if self.selected_tile_index >= 2:
                self.selected_tile_index -= 2
        elif self.state == UIState.TILE_SETTINGS:
            self.tile_settings_view.move_up()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.general_settings_view.move_up()
        # If editing display name or IP, you'd handle that differently (scroll up in a menu, etc.)

    def on_joystick_down(self):
        """User moved joystick down."""
        if self.state == UIState.PAGE_VIEW:
            # Move the selection down one row in the 2x3 grid
            if self.selected_tile_index <= 3:
                self.selected_tile_index += 2
        elif self.state == UIState.TILE_SETTINGS:
            self.tile_settings_view.move_down()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.general_settings_view.move_down()

    def on_joystick_left(self):
        if self.state == UIState.PAGE_VIEW:
            if self.selected_tile_index % 2 == 1:
                # just move left in the same page
                self.selected_tile_index -= 1
            else:
                # we are in col 0, going left might move to the previous page
                if self.selected_page_index > 0:
                    self.selected_page_index -= 1
                    self.selected_tile_index = 5  # rightmost slot
        # In the tile settings or general settings, do nothing or handle differently

    def on_joystick_right(self):
        if self.state == UIState.PAGE_VIEW:
            if self.selected_tile_index % 2 == 0:
                self.selected_tile_index += 1
            else:
                # we are on col 1, going right => move to next page
                # if it doesn't exist, create it
                self.selected_page_index += 1
                if self.selected_page_index >= len(self.pages):
                    self.pages.append([EmptyTile() for _ in range(6)])
                self.selected_tile_index = 0

    def on_joystick_middle(self):
        """Enter or select."""
        if self.state == UIState.PAGE_VIEW:
            # If the user "enters" the tile => open tile settings
            self.enter_tile_settings_view()
        elif self.state == UIState.TILE_SETTINGS:
            self.select_in_tile_settings_view()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.select_in_general_settings_view()
        # If in EDIT_DISPLAY_NAME or EDIT_IP, you might accept input or confirm

    #
    # ──────────────────────────── PUSH BUTTONS ───────────────────────────
    #

    def on_push_button_1(self):
        """
        This button is "open general settings" if we're in PAGE_VIEW,
        or "back" if we're in any other view.
        """
        if self.state == UIState.PAGE_VIEW:
            self.open_general_settings()
        else:
            # back => go to PAGE_VIEW
            self.state = UIState.PAGE_VIEW

    def on_push_button_2(self):
        """You can define a different action if needed."""
        pass

    def on_push_button_3(self):
        """You can define a different action if needed."""
        pass


#
#  ┌───────────────────────────────────────────────────────────────────┐
#  │               EXAMPLE: USING THE UI MANAGER                     │
#  └───────────────────────────────────────────────────────────────────┘

# if __name__ == "__main__":
#     # Example tile data
#     tileA = Tile("Tile A", volume=0, id=1)
#     tileB = Tile("Tile B", volume=1, id=2)
#     tileC = Tile("Tile C", volume=-1, id=3)
#     tileD = Tile("Tile D", volume=2, id=4)

#     all_tiles = [tileA, tileB, tileC, tileD]

#     ui_manager = UIManager(all_tiles)

#     # Pretend we have event callbacks for joystick and pushbuttons
#     # For demonstration, we'll do a simple loop. Press Ctrl+C to exit.

#     try:
#         while True:
#             # Render the current UI state
#             ui_manager.render()

#             # In real life, you'd have callbacks that call:
#             # ui_manager.on_joystick_up()
#             # ui_manager.on_joystick_down()
#             # ui_manager.on_joystick_left()
#             # ui_manager.on_joystick_right()
#             # ui_manager.on_joystick_middle()
#             # ui_manager.on_push_button_1(), etc.

#             # Here we'll just simulate a timed blink update
#             time.sleep(0.3)

#     except KeyboardInterrupt:
#         print("Exiting.")