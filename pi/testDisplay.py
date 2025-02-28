import time
from PIL import Image, ImageDraw, ImageFont
import st7735

# 📌 Display Configuration
WIDTH = 130  # ST7735 display width
HEIGHT = 161  # ST7735 display height

# 🔄 Color presets
COLORS = {
    "default": (0, 0, 0),   # Black
    "active": (0, 0, 255),  # Blue
    "speaking": (255, 0, 0),  # Red
    "highlight": (255, 255, 255),  # White
}

# 🖥️ Initialize ST7735 Display
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

# 🖋️ Load Font
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

# 🎨 Default tile colors (Black)
tile_colors = ["default", "default", "default", "default"]


# 📌 Function: Draw a Tile
def draw_tile(draw, x, y, w, h, title, color):
    """ Draws a tile with a background color and centered title. """
    draw.rectangle((x, y, x + w - 1, y + h - 1), fill=COLORS[color], outline=(255, 255, 255))

    # Center text in the tile
    text_x, text_y, text_w, text_h = font.getbbox(title)
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2

    draw.text((text_x, text_y), title, font=font, fill=(0, 0, 0) if color == "highlight" else (255, 255, 255))


# 📌 Function: Update Display (Version 1: 4 Tiles, Version 2: 2 Tiles)
def update_display(mode=4):
    """ Updates the screen with either 4 tiles (quadrants) or 2 tiles (halves). """
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    if mode == 4:  # 4 Tiles (Quadrants)
        draw_tile(draw, 0, 0, WIDTH // 2, HEIGHT // 2, "Channel 1", tile_colors[0])
        draw_tile(draw, WIDTH // 2, 0, WIDTH // 2, HEIGHT // 2, "Channel 2", tile_colors[1])
        draw_tile(draw, 0, HEIGHT // 2, WIDTH // 2, HEIGHT // 2, "Channel 3", tile_colors[2])
        draw_tile(draw, WIDTH // 2, HEIGHT // 2, WIDTH // 2, HEIGHT // 2, "Channel 4", tile_colors[3])
    elif mode == 2:  # 2 Tiles (Top & Bottom)
        draw_tile(draw, 0, 0, WIDTH, HEIGHT // 2, "Channel 1", tile_colors[0])
        draw_tile(draw, 0, HEIGHT // 2, WIDTH, HEIGHT // 2, "Channel 2", tile_colors[1])

    disp.display(img)


# 📌 Function: Change Tile Color
def set_tile_color(tile_index, color):
    """ Changes a tile's color dynamically and refreshes display. """
    if 0 <= tile_index < len(tile_colors):
        tile_colors[tile_index] = color
        update_display(len(tile_colors))


# 🔄 Example Usage (Testing)
update_display(4)  # Start with 4 tiles

time.sleep(2)
set_tile_color(0, "active")  # Channel 1 turns blue
time.sleep(2)
set_tile_color(2, "speaking")  # Channel 3 turns red
time.sleep(2)
set_tile_color(1, "highlight")  # Channel 2 turns white
time.sleep(2)
set_tile_color(3, "active")  # Channel 4 turns blue