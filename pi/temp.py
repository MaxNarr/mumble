#!/usr/bin/env python3

import time
import math
import spidev as SPI
from PIL import Image, ImageDraw, ImageFont
from enum import Enum

# Replace this with your local ST7789 driver import
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

# Inactivity threshold (seconds) to hide the white tile-selection cursor
CURSOR_TIMEOUT = 3.0

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
      - selected => highlight tile in white
      - talking => show green bg
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
             x: int, y: int, w: int, h: int,
             tile_cursor_active: bool):
        """
        Draws the tile rectangle plus text.
        - tile_cursor_active: If False, we ignore 'selected' and draw normally.
        """
        bg_color = (0, 0, 0)
        text_color = (255, 255, 255)

        # If the tile-selection cursor is inactive, we do not show the white highlight:
        is_selected = self.selected and tile_cursor_active

        if is_selected:
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
             x: int, y: int, w: int, h: int,
             tile_cursor_active: bool):
        # We'll just draw a plus sign in the center, ignoring volume etc.
        bg_color = (255, 255, 255) if (self.selected and tile_cursor_active) else (0, 0, 0)
        text_color = (0, 0, 0) if (self.selected and tile_cursor_active) else (255, 255, 255)
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
    """
    def __init__(self, items, title=""):
        self.items = items
        self.selected_index = 0
        self.title = title
        # We'll compute how many items can fit on-screen
        self.item_height = 25
        self.scroll_offset = 0

    def move_up(self):
        if self.selected_index > 0:
            self.selected_index -= 1
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index

    def move_down(self):
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
        max_items_on_screen = (DISPLAY_HEIGHT // self.item_height) - 1
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
        max_visible = (DISPLAY_HEIGHT - title_height) // self.item_height

        visible_items = self.items[self.scroll_offset:self.scroll_offset + max_visible]

        for idx, item_text in enumerate(visible_items):
            actual_index = self.scroll_offset + idx
            y = y_start + idx * self.item_height
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
#  │                  UI STATES / MANAGER                    │
#  └───────────────────────────────────────────────────────────┘

class UIState(Enum):
    PAGE_VIEW = 1
    TILE_SETTINGS = 2
    GENERAL_SETTINGS = 3
    EDIT_DISPLAY_NAME = 4
    EDIT_IP = 5
    LAYOUT_SETTINGS = 6


class LayoutOption(Enum):
    TWO_BY_THREE = (2, 3)  # 2 columns, 3 rows => 6 tiles per page
    TWO_BY_TWO   = (2, 2)  # 2 columns, 2 rows => 4 tiles per page
    TWO_BY_ONE   = (2, 1)  # 2 columns, 1 row  => 2 tiles per page


class UIManager:
    """
    - Manages an infinite set of pages, each page has N = cols*rows slots.
    - White cursor for single-tile selection (inactive after 3s).
    - Additional "talk group" selection: row-based highlight in green.
    - Provides menu views for tile assignment, general settings, layout settings, etc.
    """

    def __init__(self, all_tiles):
        # A pool of all possible tiles
        self.all_tiles = all_tiles

        # Default layout: 2x3
        self.layout = LayoutOption.TWO_BY_THREE

        # Create the first page
        self.pages = []
        self.pages.append([EmptyTile() for _ in range(self.num_slots_per_page())])
        self.selected_page_index = 0
        self.selected_tile_index = 0  # which slot on the page is selected

        # White tile-cursor
        self.tile_cursor_active = True
        self.last_input_time = time.time()

        # For talk groups, we store the "talk group row" selection
        self.selected_talk_group_row = 0

        # Current UI state
        self.state = UIState.PAGE_VIEW

        # For the scrollable list (TileSettings, GeneralSettings, LayoutSettings)
        self.tile_settings_view = None
        self.general_settings_view = None
        self.layout_settings_view = None

        self.display_name = "My Pi"
        self.ip_address = "192.168.0.100"
        self.use_dhcp = True

        # init some menu data
        self.init_general_settings_view()
        self.init_layout_settings_view()

    def num_cols(self):
        return self.layout.value[0]  # e.g. 2

    def num_rows(self):
        return self.layout.value[1]  # e.g. 3

    def num_slots_per_page(self):
        return self.num_cols() * self.num_rows()

    def page_count(self):
        return len(self.pages)

    def init_general_settings_view(self):
        items = ["Display Name", "IP Settings", "Layout"]
        self.general_settings_view = ScrollableListView(items, title="General Settings")

    def init_layout_settings_view(self):
        # We'll list each layout as a name
        items = ["2x3", "2x2", "2x1", "Back"]
        self.layout_settings_view = ScrollableListView(items, title="Choose Layout")

    #
    # ─────────────────────────── ACTIVITY TRACKING ─────────────────────────────
    #
    def record_user_input(self):
        """Call this whenever the user moves joystick or presses a button that affects tile selection."""
        self.last_input_time = time.time()
        # The first time user interacts again, re-activate the tile cursor in the top-left corner
        if not self.tile_cursor_active:
            self.tile_cursor_active = True
            self.selected_tile_index = 0  # jump to top-left tile on the same page

    def check_cursor_timeout(self):
        """Call periodically to see if the tile selection should be hidden."""
        if self.tile_cursor_active:
            if (time.time() - self.last_input_time) > CURSOR_TIMEOUT:
                self.tile_cursor_active = False

    #
    # ─────────────────────────── TALK GROUP LOGIC ─────────────────────────────
    #
    def get_current_talk_group_tiles(self):
        """
        Return a list of the 2 tiles in the selected talk group row.
        For a layout with 2 columns, that row is [ (row*2), (row*2 + 1) ].
        """
        row = self.selected_talk_group_row
        start_idx = row * self.num_cols()
        page = self.pages[self.selected_page_index]
        # If the row is out of range, we might need to expand pages or clamp
        if start_idx >= len(page):
            return []
        end_idx = start_idx + self.num_cols()
        return page[start_idx:end_idx]

    def talk_group_count_per_page(self):
        """Equals the number of rows in the current layout."""
        return self.num_rows()

    #
    # ─────────────────────────── PAGE VIEW RENDER ─────────────────────────────
    #

    def render_page_view(self):
        """
        Draw the grid of tiles with optional tile-selection (white) and
        the talk-group selection for the row (green border).
        """
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)

        # top bar
        top_bar_h = 24
        draw.rectangle((0, 0, DISPLAY_WIDTH, top_bar_h), fill=(255,255,255))
        page_text = f"Page {self.selected_page_index+1}"
        draw_centered_text(draw, 0, 0, DISPLAY_WIDTH, top_bar_h, page_text, FONT, (0,0,0))

        tile_area_y = top_bar_h
        tile_area_h = DISPLAY_HEIGHT - top_bar_h

        # each row is tile_h high
        tile_h = tile_area_h // self.num_rows()
        tile_w = DISPLAY_WIDTH // self.num_cols()

        page = self.pages[self.selected_page_index]
        for idx, tile in enumerate(page):
            # compute row, col
            row = idx // self.num_cols()
            col = idx % self.num_cols()
            x = col * tile_w
            y = tile_area_y + row * tile_h

            # Check if tile is currently selected
            tile.selected = (idx == self.selected_tile_index)

            # Draw tile
            tile.draw(draw, x, y, tile_w, tile_h, tile_cursor_active=self.tile_cursor_active)

        # Draw the talk group highlight for the entire row in green
        # We'll do a single green rectangle around the row
        tg_row = self.selected_talk_group_row
        tg_y = tile_area_y + tg_row * tile_h
        # talk group always 2 columns wide => entire row
        draw.rectangle((0, tg_y, DISPLAY_WIDTH, tg_y + tile_h),
                       outline=(0,255,0), width=2)

        disp.ShowImage(img)

    #
    # ───────────────────────────── RENDER STATES ─────────────────────────────
    #

    def render_tile_settings_view(self):
        self.tile_settings_view.render()

    def render_general_settings_view(self):
        self.general_settings_view.render()

    def render_layout_settings_view(self):
        self.layout_settings_view.render()

    def render_edit_display_name(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)
        msg = f"Editing display name:\n{self.display_name}\n(TODO: Implement keyboard screen)"
        draw.text((5, 5), msg, font=FONT, fill=(255,255,255))
        disp.ShowImage(img)

    def render_edit_ip(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(0,0,0))
        draw = ImageDraw.Draw(img)
        msg = "IP Settings:\n"
        msg += f"Current IP: {self.ip_address}\n"
        msg += "DHCP: " + ("On" if self.use_dhcp else "Off") + "\n"
        msg += "(TODO: Implement numpad & DHCP toggle)\n"
        draw.text((5,5), msg, font=FONT, fill=(255,255,255))
        disp.ShowImage(img)

    def render(self):
        # Possibly hide the tile cursor if inactive
        self.check_cursor_timeout()

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
        elif self.state == UIState.LAYOUT_SETTINGS:
            self.render_layout_settings_view()

    #
    # ─────────────────────────── TILE SETTINGS  ─────────────────────────────
    #

    def enter_tile_settings_view(self):
        """
        Build a list: ["Empty", all tile names, "Back"]
        """
        item_names = ["Empty"]
        for t in self.all_tiles:
            item_names.append(t.name)
        item_names.append("Back")
        self.tile_settings_view = ScrollableListView(item_names, title="Select Tile")
        self.state = UIState.TILE_SETTINGS

    def select_in_tile_settings_view(self):
        chosen = self.tile_settings_view.get_selected_item()
        if chosen is None:
            return
        if chosen == "Back" or (self.tile_settings_view.selected_index == len(self.tile_settings_view.items)-1):
            self.state = UIState.PAGE_VIEW
            return
        elif chosen == "Empty":
            self.set_current_page_tile(EmptyTile())
            self.state = UIState.PAGE_VIEW
            return
        else:
            for tile_obj in self.all_tiles:
                if tile_obj.name == chosen:
                    self.set_current_page_tile(tile_obj)
                    break
            self.state = UIState.PAGE_VIEW

    def set_current_page_tile(self, tile):
        page = self.pages[self.selected_page_index]
        if self.selected_tile_index < len(page):
            page[self.selected_tile_index] = tile

    #
    # ─────────────────────────── GENERAL SETTINGS ─────────────────────────────
    #

    def open_general_settings(self):
        self.state = UIState.GENERAL_SETTINGS

    def select_in_general_settings_view(self):
        chosen = self.general_settings_view.get_selected_item()
        if chosen == "Display Name":
            self.state = UIState.EDIT_DISPLAY_NAME
        elif chosen == "IP Settings":
            self.state = UIState.EDIT_IP
        elif chosen == "Layout":
            self.state = UIState.LAYOUT_SETTINGS
        else:
            pass

    #
    # ─────────────────────────── LAYOUT SETTINGS ─────────────────────────────
    #

    def select_in_layout_settings_view(self):
        chosen = self.layout_settings_view.get_selected_item()
        if chosen is None:
            return
        if chosen == "Back":
            self.state = UIState.GENERAL_SETTINGS
            return
        elif chosen == "2x3":
            self.set_layout(LayoutOption.TWO_BY_THREE)
        elif chosen == "2x2":
            self.set_layout(LayoutOption.TWO_BY_TWO)
        elif chosen == "2x1":
            self.set_layout(LayoutOption.TWO_BY_ONE)
        # Then return to PAGE_VIEW for now or stay in general settings—your call:
        self.state = UIState.GENERAL_SETTINGS

    def set_layout(self, layout_option: LayoutOption):
        """
        1) If the new layout has fewer or more tiles per page, we need
           to adapt the existing pages or start fresh. For simplicity,
           we’ll create brand new pages with everything empty. 
           A more advanced approach: re-map existing tiles to new pages.
        """
        self.layout = layout_option
        self.pages = []
        self.selected_page_index = 0
        self.selected_tile_index = 0
        self.pages.append([EmptyTile() for _ in range(self.num_slots_per_page())])

    #
    # ─────────────────────────── EVENT HANDLERS ─────────────────────────────
    #

    def on_joystick_up(self):
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW:
            # Move the tile selection up (white cursor)
            if self.tile_cursor_active:
                cols = self.num_cols()
                if self.selected_tile_index >= cols:
                    self.selected_tile_index -= cols
            else:
                # If the cursor is inactive, do nothing or re-activate?
                pass
        elif self.state == UIState.TILE_SETTINGS:
            self.tile_settings_view.move_up()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.general_settings_view.move_up()
        elif self.state == UIState.LAYOUT_SETTINGS:
            self.layout_settings_view.move_up()

    def on_joystick_down(self):
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW:
            if self.tile_cursor_active:
                cols = self.num_cols()
                total_slots = self.num_slots_per_page()
                if self.selected_tile_index + cols < total_slots:
                    self.selected_tile_index += cols
            else:
                pass
        elif self.state == UIState.TILE_SETTINGS:
            self.tile_settings_view.move_down()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.general_settings_view.move_down()
        elif self.state == UIState.LAYOUT_SETTINGS:
            self.layout_settings_view.move_down()

    def on_joystick_left(self):
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW and self.tile_cursor_active:
            if (self.selected_tile_index % self.num_cols()) == 0:
                # leftmost col => go to previous page?
                if self.selected_page_index > 0:
                    self.selected_page_index -= 1
                    self.selected_tile_index = self.num_slots_per_page() - 1
            else:
                self.selected_tile_index -= 1

    def on_joystick_right(self):
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW and self.tile_cursor_active:
            cols = self.num_cols()
            if (self.selected_tile_index % cols) == (cols - 1):
                # rightmost col => next page
                self.selected_page_index += 1
                if self.selected_page_index >= len(self.pages):
                    self.pages.append([EmptyTile() for _ in range(self.num_slots_per_page())])
                self.selected_tile_index = 0
            else:
                self.selected_tile_index += 1

    def on_joystick_middle(self):
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW:
            # Enter tile settings for whichever tile is selected
            self.enter_tile_settings_view()
        elif self.state == UIState.TILE_SETTINGS:
            self.select_in_tile_settings_view()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.select_in_general_settings_view()
        elif self.state == UIState.LAYOUT_SETTINGS:
            self.select_in_layout_settings_view()
        # If we had a separate confirm for EDIT_DISPLAY_NAME or EDIT_IP, handle here

    #
    # ───────────────────────── PUSH BUTTONS ─────────────────────────
    #

    def on_push_button_1(self):
        """If in PAGE_VIEW => open general settings. Otherwise => back to PAGE_VIEW."""
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW:
            self.open_general_settings()
        else:
            self.state = UIState.PAGE_VIEW

    def on_push_button_2(self):
        """
        Select the talk group up: i.e. move the selected_talk_group_row up
        If we exceed top, go to previous page. If no previous page, do nothing or wrap around.
        """
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW:
            if self.selected_talk_group_row > 0:
                self.selected_talk_group_row -= 1
            else:
                # top row => previous page if possible
                if self.selected_page_index > 0:
                    self.selected_page_index -= 1
                    self.selected_talk_group_row = self.num_rows() - 1
        else:
            # In other states, do nothing or define your own logic
            pass

    def on_push_button_3(self):
        """
        Select the talk group down: move selected_talk_group_row down
        If we exceed last row => next page
        """
        self.record_user_input()
        if self.state == UIState.PAGE_VIEW:
            if self.selected_talk_group_row < (self.num_rows() - 1):
                self.selected_talk_group_row += 1
            else:
                # bottom row => next page
                self.selected_page_index += 1
                if self.selected_page_index >= len(self.pages):
                    self.pages.append([EmptyTile() for _ in range(self.num_slots_per_page())])
                self.selected_talk_group_row = 0
        else:
            pass


#
#  ┌───────────────────────────────────────────────────────────────────┐
#  │               EXAMPLE: USING THE UI MANAGER                     │
#  └───────────────────────────────────────────────────────────────────┘

if __name__ == "__main__":
    # Example tile data
    tileA = Tile("Tile A", volume=0, id=1)
    tileB = Tile("Tile B", volume=1, id=2)
    tileC = Tile("Tile C", volume=-1, id=3)
    tileD = Tile("Tile D", volume=2, id=4)

    all_tiles = [tileA, tileB, tileC, tileD]

    ui_manager = UIManager(all_tiles)

    # In your real application, you'd wire up actual GPIO callbacks to
    # ui_manager.on_joystick_up/down/left/right/middle()
    # ui_manager.on_push_button_1/2/3()
    # For demonstration, we just run a loop that re-renders every 0.3s.

    try:
        while True:
            ui_manager.render()
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("Exiting.")