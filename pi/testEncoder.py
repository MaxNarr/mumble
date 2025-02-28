from gpiozero import RotaryEncoder
from gpiozero import Button
from time import time

encoder = RotaryEncoder(18, 17, wrap=False)  # Replace with your GPIO pins

last_position = encoder.value
last_press_time = 0
double_press_threshold = 0.5  # Maximum time (seconds) between presses

def on_press():
    print("Button pressed!")
    global last_press_time
    current_time = time()
    diff = current_time - last_press_time
    if diff <= double_press_threshold :
        print("Double press detected!"+ str(current_time - last_press_time))
    last_press_time = current_time

def on_release():
    print("Button released!")

button = Button(19,pull_up=True, bounce_time=0.02)

button.when_pressed = on_press  # Trigger on press
button.when_released = on_release  # Trigger on release

while True:
    if encoder.value != last_position:
        print(f"Rotary position: {encoder.value}")
        last_position = encoder.value




