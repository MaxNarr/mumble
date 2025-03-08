#!/usr/bin/env python3

import os
import json
import time
import math
import spidev as SPI
from enum import Enum
from PIL import Image, ImageDraw, ImageFont

# Replace with your local ST7789 driver import
from DisplayST7789 import ST7789


CONFIG_FILE = "config.json"
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
# Constants
MINVOLUME = -2
MAXVOLUME = 2
BLINK_DURATION = 5
BLINK_INTERVAL = 0.5

BASE_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = ImageFont.truetype(BASE_FONT_PATH, 14)
VOLUME_FONT = ImageFont.truetype(BASE_FONT_PATH, 10)
MIN_NAME_FONT_SIZE = 11
MAX_NAME_FONT_SIZE = 30

CURSOR_TIMEOUT = 3.0  # seconds of joystick inactivity to hide cursor


#
# ┌─────────────────────────────────────────────────────────────┐
# │                 SIMPLE CONFIG MANAGER                      │
# └─────────────────────────────────────────────────────────────┘

class ConfigManager:
    """
    Loads/saves the UI configuration (pages, layout, display name, IP, etc.)
    from a JSON file.
    """
    def __init__(self, filename=CONFIG_FILE):
        self.filename = filename

    def load_config(self):
        if not os.path.exists(self.filename):
            return None
        with open(self.filename, "r") as f:
            data = json.load(f)
        return data

    def save_config(self, data):
        with open(self.filename, "w") as f:
            json.dump(data, f, indent=2)


#
# ┌─────────────────────────────────────────────────────────────┐
# │                        HELPER FUNCS                        │
# └─────────────────────────────────────────────────────────────┘

def get_text_dimensions(text, font):
    mask = font.getmask(text)
    return mask.size

def current_blink_state() -> bool:
    """Blink toggles every BLINK_INTERVAL seconds."""
    now = time.time()
    cycle = math.floor(now / BLINK_INTERVAL)
    return (cycle % 2) == 0

def draw_centered_multiline(draw_obj, x, y, w, h, lines, fonts, color=(255,255,255), spacing=5):
    """
    Draw multiple lines (each with a given font) centered horizontally & vertically.
    lines: [ "TileName", "Volume" ] for example
    fonts: [ nameFont, volumeFont ]
    We'll compute total height, then center as a block in the tile.
    """
    total_height = 0
    line_sizes = []
    for line, fnt in zip(lines, fonts):
        tw, th = get_text_dimensions(line, fnt)
        line_sizes.append((tw, th))
        total_height += th
    # add spacing between lines
    total_height += spacing * (len(lines) - 1)

    # y offset for the block
    start_y = y + (h - total_height) // 2

    cur_y = start_y
    for (line, fnt), (tw, th) in zip(zip(lines, fonts), line_sizes):
        text_x = x + (w - tw) // 2
        text_y = cur_y
        draw_obj.text((text_x, text_y), line, font=fnt, fill=color)
        cur_y += th + spacing


#
# ┌─────────────────────────────────────────────────────────────┐
# │                          TILE CLASS                        │
# └─────────────────────────────────────────────────────────────┘

class Tile:
    def __init__(self, name="Unnamed", volume=0, id=0,
                 is_calledByUser=None,
                 selected=False, talking=False):
        self.name = name
        self.volume = volume
        self.id = id
        self.is_calledByUser = is_calledByUser
        self.selected = selected
        self.talking = talking
        self.blink_start = None

    def set_volume(self, new_volume: int):
        # Example
        import mumbleRPC
        self.volume = max(MINVOLUME-1, min(MAXVOLUME, new_volume))
        mumbleRPC.listen(self)
        print("Volume: " + str(self.volume))

    def call(self):
        import mumbleRPC
        mumbleRPC.call(self)
        self.is_calledByUser = "calling"

    def draw(self, draw_obj: ImageDraw.ImageDraw,
             x: int, y: int, w: int, h: int,
             tile_cursor_active: bool):
        """
        If tile_cursor_active is False, we ignore 'selected'.
        We'll center the name text + volume text in the tile (vertically & horizontally).
        """
        bg = (0,0,0)
        fg = (255,255,255)

        # If the tile is "selected" but the cursor is hidden => treat as unselected.
        is_sel = (self.selected and tile_cursor_active)

        if is_sel:
            bg = (255,255,255)
            fg = (0,0,0)
        else:
            # Possibly blink red if is_calledByUser
            if self.is_calledByUser:
                if self.blink_start is None:
                    self.blink_start = time.time()
                if (time.time() - self.blink_start) < BLINK_DURATION:
                    if current_blink_state():
                        bg = (255,0,0)
                    else:
                        bg = (0,0,0)
                else:
                    self.is_calledByUser = None
                    self.blink_start = None
                    bg = (0,0,0)
                fg = (255,255,255)
            elif self.talking:
                bg = (0,128,0)
                fg = (255,255,255)

        draw_obj.rectangle((x,y,x+w,y+h), fill=bg, outline=(255,255,255))

        # Build the lines to display: [tileName, volumeText]
        # Center them in the tile
        if self.volume == MINVOLUME-1:
            volume_str = "muted"
        elif self.volume == 0:
            volume_str = "Std."
        elif self.volume > 0:
            volume_str = f"+{self.volume}"
        else:
            volume_str = str(self.volume)

        name_font_size = MAX_NAME_FONT_SIZE
        best_font = None
        # For short demonstration, let's pick a font size for the name
        while name_font_size >= MIN_NAME_FONT_SIZE:
            trial = ImageFont.truetype(BASE_FONT_PATH, name_font_size)
            tw, th = get_text_dimensions(self.name, trial)
            if tw <= w - 10 and th <= (h//2):
                best_font = trial
                break
            name_font_size -= 1
        if best_font is None:
            best_font = ImageFont.truetype(BASE_FONT_PATH, MIN_NAME_FONT_SIZE)

        # For volume text, just use VOLUME_FONT
        lines = [self.name, volume_str]
        fonts = [best_font, VOLUME_FONT]
        draw_centered_multiline(draw_obj, x, y, w, h, lines, fonts, color=fg, spacing=5)


class EmptyTile(Tile):
    """
    A tile that shows a plus sign if not selected, or invert if selected/cursor active.
    """
    def __init__(self):
        super().__init__(name="+", id=-1, volume=0)

    def draw(self, draw_obj: ImageDraw.ImageDraw,
             x: int, y: int, w: int, h: int,
             tile_cursor_active: bool):
        bg = (255,255,255) if (self.selected and tile_cursor_active) else (0,0,0)
        fg = (0,0,0) if (self.selected and tile_cursor_active) else (255,255,255)
        draw_obj.rectangle((x,y,x+w,y+h), fill=bg, outline=(255,255,255))
        draw_centered_multiline(
            draw_obj, x, y, w, h, ["+"], [FONT],
            color=fg, spacing=0
        )


#
# ┌─────────────────────────────────────────────────────────────┐
# │           SCROLLABLE LIST VIEW & UI STATES                 │
# └─────────────────────────────────────────────────────────────┘

class ScrollableListView:
    def __init__(self, items, title=""):
        self.items = items
        self.title = title
        self.selected_index = 0
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
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), (0,0,0))
        draw = ImageDraw.Draw(img)
        title_height = 25
        # title bar
        draw.rectangle((0,0,DISPLAY_WIDTH,title_height), fill=(255,255,255))
        draw_centered_text(draw, 0,0, DISPLAY_WIDTH,title_height, self.title, FONT, (0,0,0))

        y_start = title_height
        max_vis = (DISPLAY_HEIGHT - title_height) // self.item_height
        visible = self.items[self.scroll_offset : self.scroll_offset+max_vis]

        for idx, item in enumerate(visible):
            actual_index = self.scroll_offset + idx
            y = y_start + idx*self.item_height
            if actual_index == self.selected_index:
                bg = (255,255,255)
                fg = (0,0,0)
            else:
                bg = (0,0,0)
                fg = (255,255,255)
            draw.rectangle((0,y,DISPLAY_WIDTH,y+self.item_height), fill=bg)
            draw_centered_text(draw, 0,y, DISPLAY_WIDTH,self.item_height, item, FONT, fg)

        disp.ShowImage(img)

    def get_selected_item(self):
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None


class UIState(Enum):
    PAGE_VIEW = 1
    TILE_SETTINGS = 2
    GENERAL_SETTINGS = 3
    EDIT_DISPLAY_NAME = 4
    EDIT_IP = 5


#
# ┌─────────────────────────────────────────────────────────────┐
# │                    LAYOUT ENUM                             │
# └─────────────────────────────────────────────────────────────┘
class LayoutOption(Enum):
    TWO_BY_THREE = (2,3)
    TWO_BY_TWO   = (2,2)
    TWO_BY_ONE   = (2,1)


#
# ┌─────────────────────────────────────────────────────────────┐
# │                  UI MANAGER CLASS                          │
# └─────────────────────────────────────────────────────────────┘

class UIManager:
    def __init__(self, all_tiles):
        self.cfg_manager = ConfigManager()
        self.all_tiles = all_tiles
        # Default
        self.layout = LayoutOption.TWO_BY_THREE
        self.pages = []
        self.selected_page_index = 0
        self.selected_tile_index = 0

        # White cursor
        self.tile_cursor_active = True
        self.last_input_time = time.time()

        # Talk group row
        self.selected_talk_group_row = 0

        # UI state
        self.state = UIState.PAGE_VIEW

        # Some example config
        self.display_name = "My Pi"
        self.ip_address = "192.168.0.100"
        self.use_dhcp = True

        self.tile_settings_view = None
        self.general_settings_view = None

        # Attempt to load config
        loaded = self.cfg_manager.load_config()
        if loaded:
            self.apply_loaded_config(loaded)
        else:
            # if no config => init default single page
            self.pages = [ [EmptyTile() for _ in range(self.num_slots_per_page())] ]

        self.init_general_settings_view()

    def init_general_settings_view(self):
        items = ["Display Name", "IP Settings"]
        # You could also add a "Layout" item if you want
        self.general_settings_view = ScrollableListView(items, title="General Settings")

    #
    # ──────────────────────────── LOAD/SAVE CONFIG ────────────────────────────
    #

    def apply_loaded_config(self, data):
        """
        data is a dict from JSON. Example structure:
        {
          "layout": "2x3",
          "pages": [
             [ {"name":"Tile A", "id":1, "volume":0}, {"name":"Tile B",...} ... ],
             ...
          ],
          "displayName": "My Pi",
          "ipAddress": "192.168.0.100",
          "useDHCP": true
        }
        """
        # layout
        layout_str = data.get("layout","2x3")
        if layout_str == "2x3":
            self.layout = LayoutOption.TWO_BY_THREE
        elif layout_str == "2x2":
            self.layout = LayoutOption.TWO_BY_TWO
        elif layout_str == "2x1":
            self.layout = LayoutOption.TWO_BY_ONE
        else:
            self.layout = LayoutOption.TWO_BY_THREE

        # pages
        raw_pages = data.get("pages", [])
        self.pages = []
        for raw_page in raw_pages:
            tile_list = []
            for tdict in raw_page:
                if tdict.get("id",-1) == -1:
                    tile_list.append(EmptyTile())
                else:
                    new_tile = Tile(name=tdict.get("name","Unnamed"),
                                    volume=tdict.get("volume",0),
                                    id=tdict.get("id",0))
                    tile_list.append(new_tile)
            # If the page is shorter/longer than needed, adjust
            needed = self.num_slots_per_page()
            if len(tile_list) < needed:
                tile_list += [EmptyTile()]*(needed - len(tile_list))
            elif len(tile_list) > needed:
                tile_list = tile_list[:needed]
            self.pages.append(tile_list)
        if not self.pages:
            # if empty, at least create one
            self.pages = [ [EmptyTile() for _ in range(self.num_slots_per_page())] ]

        # displayName / ip
        self.display_name = data.get("displayName","My Pi")
        self.ip_address = data.get("ipAddress","192.168.0.100")
        self.use_dhcp = data.get("useDHCP", True)

    def save_config(self):
        """
        Convert our current UI data to JSON-friendly dict and write to disk.
        """
        data = {}
        # layout
        if self.layout == LayoutOption.TWO_BY_THREE:
            data["layout"] = "2x3"
        elif self.layout == LayoutOption.TWO_BY_TWO:
            data["layout"] = "2x2"
        elif self.layout == LayoutOption.TWO_BY_ONE:
            data["layout"] = "2x1"

        # pages
        raw_pages = []
        for page in self.pages:
            tlist = []
            for tile in page:
                if isinstance(tile, EmptyTile):
                    tlist.append({"id": -1})
                else:
                    tlist.append({
                        "name": tile.name,
                        "id": tile.id,
                        "volume": tile.volume
                    })
            raw_pages.append(tlist)
        data["pages"] = raw_pages
        data["displayName"] = self.display_name
        data["ipAddress"] = self.ip_address
        data["useDHCP"] = self.use_dhcp

        self.cfg_manager.save_config(data)

    #
    # ──────────────────────────── LAYOUT HELPERS ─────────────────────────────
    #

    def num_cols(self):
        return self.layout.value[0]

    def num_rows(self):
        return self.layout.value[1]

    def num_slots_per_page(self):
        return self.num_cols() * self.num_rows()

    #
    # ───────────────────── RENDER & STATE-SPECIFIC DISPLAYS ─────────────────
    #

    def check_cursor_timeout(self):
        """Hide tile cursor if inactivity > CURSOR_TIMEOUT."""
        if self.tile_cursor_active and (time.time() - self.last_input_time > CURSOR_TIMEOUT):
            self.tile_cursor_active = False

    def render_page_view(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), (0,0,0))
        draw = ImageDraw.Draw(img)

        # top bar
        top_bar_h = 24
        draw.rectangle((0,0,DISPLAY_WIDTH,top_bar_h), fill=(255,255,255))
        page_text = f"Page {self.selected_page_index+1}"
        # Show display name too?
        draw_centered_text(draw, 0,0, DISPLAY_WIDTH,top_bar_h, page_text, FONT, (0,0,0))

        tile_area_y = top_bar_h
        tile_area_h = DISPLAY_HEIGHT - top_bar_h

        tile_w = DISPLAY_WIDTH // self.num_cols()
        tile_h = tile_area_h // self.num_rows()

        page = self.pages[self.selected_page_index]

        # draw tiles
        for idx, tile in enumerate(page):
            row = idx // self.num_cols()
            col = idx % self.num_cols()
            x = col*tile_w
            y = tile_area_y + row*tile_h

            tile.selected = (idx == self.selected_tile_index)
            tile.draw(draw, x,y, tile_w, tile_h, self.tile_cursor_active)

        # talk group row outline in green
        tg_y = tile_area_y + self.selected_talk_group_row*tile_h
        draw.rectangle((0, tg_y, DISPLAY_WIDTH, tg_y + tile_h),
                       outline=(0,255,0), width=2)

        disp.ShowImage(img)

    def render_tile_settings_view(self):
        self.tile_settings_view.render()

    def render_general_settings_view(self):
        self.general_settings_view.render()

    def render_edit_display_name(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), (0,0,0))
        draw = ImageDraw.Draw(img)
        msg = f"Editing display name:\n{self.display_name}\n(TODO: Implement keyboard screen)"
        draw.text((5,5), msg, font=FONT, fill=(255,255,255))
        disp.ShowImage(img)

    def render_edit_ip(self):
        img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), (0,0,0))
        draw = ImageDraw.Draw(img)
        msg = "IP Settings:\n"
        msg += f"IP: {self.ip_address}\n"
        msg += "DHCP: " + ("On" if self.use_dhcp else "Off")
        draw.text((5,5), msg, font=FONT, fill=(255,255,255))
        disp.ShowImage(img)

    def render(self):
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

    #
    # ───────────────────── TILE SETTINGS LOGIC ──────────────────────────────
    #

    def enter_tile_settings_view(self):
        items = ["Empty"]
        for t in self.all_tiles:
            items.append(t.name)
        items.append("Back")
        self.tile_settings_view = ScrollableListView(items, title="Select Tile")
        self.state = UIState.TILE_SETTINGS

    def select_in_tile_settings_view(self):
        chosen = self.tile_settings_view.get_selected_item()
        if not chosen:
            return
        if chosen == "Back" or chosen == self.tile_settings_view.items[-1]:
            self.state = UIState.PAGE_VIEW
            return
        if chosen == "Empty":
            self.set_current_page_tile(EmptyTile())
            self.state = UIState.PAGE_VIEW
            return
        # else find that tile in all_tiles
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
    # ───────────────────── GENERAL SETTINGS LOGIC ───────────────────────────
    #

    def open_general_settings(self):
        self.state = UIState.GENERAL_SETTINGS

    def select_in_general_settings_view(self):
        chosen = self.general_settings_view.get_selected_item()
        if chosen == "Display Name":
            self.state = UIState.EDIT_DISPLAY_NAME
        elif chosen == "IP Settings":
            self.state = UIState.EDIT_IP

    #
    # ───────────────────── EVENT HANDLERS ──────────────────────────────────
    #

    def record_user_input(self):
        """
        Called for joystick movements in page view to reactivate the tile cursor.
        (We do NOT call this in on_push_button_2 or 3, so talk-group changes won't re-activate.)
        """
        self.last_input_time = time.time()
        if not self.tile_cursor_active:
            # re-activate and jump to top-left tile on current page
            self.tile_cursor_active = True
            self.selected_tile_index = 0

    def on_joystick_up(self):
        if self.state == UIState.PAGE_VIEW:
            self.record_user_input()
            # move the tile cursor up
            cols = self.num_cols()
            if self.selected_tile_index >= cols:
                self.selected_tile_index -= cols
        elif self.state == UIState.TILE_SETTINGS:
            self.tile_settings_view.move_up()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.general_settings_view.move_up()

    def on_joystick_down(self):
        if self.state == UIState.PAGE_VIEW:
            self.record_user_input()
            total = self.num_slots_per_page()
            cols = self.num_cols()
            if self.selected_tile_index + cols < total:
                self.selected_tile_index += cols
        elif self.state == UIState.TILE_SETTINGS:
            self.tile_settings_view.move_down()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.general_settings_view.move_down()

    def on_joystick_left(self):
        if self.state == UIState.PAGE_VIEW:
            self.record_user_input()
            if (self.selected_tile_index % self.num_cols()) == 0:
                # go to previous page
                if self.selected_page_index > 0:
                    self.selected_page_index -= 1
                    self.selected_tile_index = self.num_slots_per_page()-1
            else:
                self.selected_tile_index -= 1

    def on_joystick_right(self):
        if self.state == UIState.PAGE_VIEW:
            self.record_user_input()
            cols = self.num_cols()
            if (self.selected_tile_index % cols) == (cols-1):
                self.selected_page_index += 1
                if self.selected_page_index >= len(self.pages):
                    self.pages.append([EmptyTile() for _ in range(self.num_slots_per_page())])
                self.selected_tile_index = 0
            else:
                self.selected_tile_index += 1

    def on_joystick_middle(self):
        if self.state == UIState.PAGE_VIEW:
            self.record_user_input()
            # open tile settings
            self.enter_tile_settings_view()
        elif self.state == UIState.TILE_SETTINGS:
            self.select_in_tile_settings_view()
        elif self.state == UIState.GENERAL_SETTINGS:
            self.select_in_general_settings_view()

    #
    # ───────────────────── TALK GROUP SELECTION ────────────────────────────
    #

    def get_current_talk_group_tiles(self):
        """
        Return the 2 tiles in the row = self.selected_talk_group_row
        for a 2-column layout. If layout is not 2-column, adapt as needed.
        """
        row = self.selected_talk_group_row
        start_idx = row * self.num_cols()
        page = self.pages[self.selected_page_index]
        end_idx = start_idx + self.num_cols()
        return page[start_idx:end_idx]

    def on_push_button_1(self):
        # if in PAGE_VIEW => open general settings, else => go back
        if self.state == UIState.PAGE_VIEW:
            self.open_general_settings()
        else:
            self.state = UIState.PAGE_VIEW

    def on_push_button_2(self):
        # talk group up
        if self.state == UIState.PAGE_VIEW:
            row = self.selected_talk_group_row
            if row > 0:
                self.selected_talk_group_row -= 1
            else:
                # go to previous page if possible
                if self.selected_page_index > 0:
                    self.selected_page_index -= 1
                    self.selected_talk_group_row = self.num_rows()-1

    def on_push_button_3(self):
        # talk group down
        if self.state == UIState.PAGE_VIEW:
            row = self.selected_talk_group_row
            if row < self.num_rows()-1:
                self.selected_talk_group_row += 1
            else:
                # next page
                self.selected_page_index += 1
                if self.selected_page_index >= len(self.pages):
                    self.pages.append([EmptyTile() for _ in range(self.num_slots_per_page())])
                self.selected_talk_group_row = 0

#
