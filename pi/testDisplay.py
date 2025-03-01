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

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                      GLOBAL VARIABLES                         │
#  └────────────────────────────────────────────────────────────────┘

# Keyboard layout rows (no umlauts):
ROW0 = ["Q","W","E","R","T","Z","U","I","O","P"]  # 10 letters
ROW1 = ["A","S","D","F","G","H","J","K","L"]      # 9 letters
ROW2 = ["Y","X","C","V","B","N","M"]              # 7 letters

# Row offsets (in "key-width" units)
ROW_OFFSETS = [0.0, 0.5, 1.0]  # last row is further to the right

# Flatten the rows to index them easily
ALL_ROWS = [ROW0, ROW1, ROW2]
ALL_LETTERS = ROW0 + ROW1 + ROW2  # total 26 letters

# For the text field content
typed_text = ""

# For the currently selected key index
selected_key_index = 0

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │          FALLBACK TEXT-SIZE HELPERS FOR OLDER PIL VERSIONS    │
#  └────────────────────────────────────────────────────────────────┘

font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)

def get_text_dimensions(text, font):
    """
    Returns (width, height) of single-line `text` using fallback getmask().
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
#  │                   DISPLAY: TEXT + KEYBOARD                    │
#  └────────────────────────────────────────────────────────────────┘

def display_screen(selected_key, typed_text):
    """
    Draws:
      1) A text field in the top 1/3 of the screen
      2) A 'realistic' German QWERTZ keyboard (bottom 2/3)
         with the given selected_key highlighted.
    """
    # Create a new blank image
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ===== 1) Draw the text field in top 1/3 =====
    text_field_height = HEIGHT // 3
    # White border rectangle for the text field
    draw.rectangle((0, 0, WIDTH, text_field_height),
                   outline=(255,255,255), fill=(0,0,0))
    # Show typed text inside
    draw_centered_text(draw, 0, 0, WIDTH, text_field_height, typed_text, font, (255,255,255))

    # ===== 2) Draw the keyboard in bottom 2/3 =====
    # We'll define the keyboard region
    kb_top_y = text_field_height
    kb_height = HEIGHT - text_field_height  # bottom 2/3

    # We remove the left margin, but keep a small "right offset" of 20
    margin_x = 0
    usable_width = WIDTH - 20

    # We'll distribute rows vertically
    total_rows = len(ALL_ROWS)  # 3
    row_height = kb_height / total_rows

    # Keep track of which key index we're on
    # We'll do something similar to the earlier code
    cur_index = 0

    for r, letters_in_row in enumerate(ALL_ROWS):
        row_y = int(kb_top_y + r * row_height)
        row_h = int(row_height)

        num_cols = len(letters_in_row)  # how many letters in this row
        key_width = usable_width / num_cols

        # shift row by fraction of one key width
        offset_pixels = int(ROW_OFFSETS[r] * key_width)

        for c, letter in enumerate(letters_in_row):
            x = margin_x + offset_pixels + int(c * key_width)
            y = row_y
            w = int(key_width)
            h = row_h

            # If this key is selected, invert colors
            if cur_index == selected_key:
                fill_color = (255,255,255)  # white
                text_color = (0,0,0)        # black
            else:
                fill_color = (0,0,0)        # black
                text_color = (255,255,255)

            draw.rectangle(
                (x, y, x + w, y + h),
                fill=fill_color,
                outline=(255,255,255)
            )
            draw_centered_text(draw, x, y, w, h, letter, font, text_color)

            cur_index += 1

    # Send to display
    disp.display(img)

#
#  ┌────────────────────────────────────────────────────────────────┐
#  │            CONTROLS: PROCESS INPUT & TEXTFIELD CONTENT        │
#  └────────────────────────────────────────────────────────────────┘

def process_input(delta, select):
    """
    Moves selection by delta in {-1, 0, +1}:
      -1 = previous key
       0 = no movement
      +1 = next key
    If select == True, append current letter to typed_text.

    Then calls display_screen() to refresh.
    """
    global selected_key_index
    global typed_text

    # Move selection (wrap around if needed)
    if delta != 0:
        selected_key_index = (selected_key_index + delta) % len(ALL_LETTERS)

    # If select is True, append the letter to typed_text
    if select:
        letter = ALL_LETTERS[selected_key_index]
        typed_text += letter

    # Redraw screen
    display_screen(selected_key_index, typed_text)

def get_textfield_content():
    """
    Returns the current typed text from the text field.
    """
    return typed_text


#
#  ┌────────────────────────────────────────────────────────────────┐
#  │                            DEMO MAIN                          │
#  └────────────────────────────────────────────────────────────────┘

if __name__ == "__main__":
    # Show initial screen
    display_screen(selected_key_index, typed_text)
    print("Starting demo...")

    # Let's do a short "fake" input sequence as an example:
    # We'll do +1 (move right) a few times, then select, etc.
    input_sequence = [
        (+1, False),
        (+1, False),
        (0, True),   # select current key
        (+1, False),
        (+1, False),
        (+1, False),
        (0, True),   # select again
        (-1, False),
        (0, True)
    ]
    for (delta, sel) in input_sequence:
        process_input(delta, sel)
        time.sleep(1)

    # Final typed text
    final_text = get_textfield_content()
    print("Final typed text:", final_text)
    time.sleep(3)
    print("Done!")
