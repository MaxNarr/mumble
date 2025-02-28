#https://www.instructables.com/Getting-18-Inch-LCD-Display-St7735s-to-Work-With-R/
#sudo nano  /home/coms2/intercom_mumble/mumble/pi/venv/lib/python3.11/site-packages/st7735/__init__.py 
#width 130 height 161. columns genauso

import time

from PIL import Image, ImageDraw, ImageFont

import st7735

MESSAGE = "Hello World! How are you today?"

# Create ST7735 LCD display class.
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



# Initialize display.
disp.begin()

WIDTH = disp.width
HEIGHT = disp.height


# Clear the display to a red background.
# Can pass any tuple of red, green, blue values (from 0 to 255 each).
# Get a PIL Draw object to start drawing on the display buffer.
img = Image.new("RGB", (WIDTH, HEIGHT), color=(255, 0, 0))

draw = ImageDraw.Draw(img)

# Draw a purple rectangle with yellow outline.
draw.rectangle((10, 10, WIDTH - 10, HEIGHT - 10), outline=(255, 255, 0), fill=(255, 0, 255))

# Draw some shapes.
# Draw a blue ellipse with a green outline.
draw.ellipse((10, 10, WIDTH - 10, HEIGHT - 10), outline=(0, 255, 0), fill=(0, 0, 255))

# Draw a white X.
draw.line((10, 10, WIDTH - 10, HEIGHT - 10), fill=(255, 255, 255))
draw.line((10, HEIGHT - 10, WIDTH - 10, 10), fill=(255, 255, 255))

# Draw a cyan triangle with a black outline.
draw.polygon([(WIDTH / 2, 10), (WIDTH - 10, HEIGHT - 10), (10, HEIGHT - 10)], outline=(0, 0, 0), fill=(0, 255, 255))

# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype("Minecraftia.ttf", 16)


# Define a function to create rotated text.  Unfortunately PIL doesn"t have good
# native support for rotated fonts, but this function can be used to make a
# text image and rotate it so it"s easy to paste in the buffer.
def draw_rotated_text(image, text, position, angle, font, fill=(255, 255, 255)):
    # Get rendered font width and height.
    x1, y1, x2, y2 = font.getbbox(text)
    width = x2 - x1
    height = y2 - y1
    # Create a new image with transparent background to store the text.
    textimage = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    # Render the text.
    textdraw = ImageDraw.Draw(textimage)
    textdraw.text((0, 0), text, font=font, fill=fill)
    # Rotate the text image.
    rotated = textimage.rotate(angle, expand=1)
    # Paste the text into the image, using it as a mask for transparency.
    image.paste(rotated, position, rotated)


# Write two lines of white text on the buffer, rotated 90 degrees counter clockwise.
draw_rotated_text(img, "Hello World!", (0, 0), 90, font, fill=(255, 255, 255))
draw_rotated_text(img, "This is a line of text.", (10, HEIGHT - 10), 0, font, fill=(255, 255, 255))

# Write buffer to display hardware, must be called to make things visible on the
# display!
disp.display(img)