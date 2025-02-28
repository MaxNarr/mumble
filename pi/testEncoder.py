from gpiozero import RotaryEncoder
from gpiozero import Button
from time import time

encoder = RotaryEncoder(17, 18, wrap=True)  # Replace with your GPIO pins

last_position = encoder.value
last_press_time = 0
double_press_threshold = 0.5  # Maximum time (seconds) between presses

def on_press():
    global last_press_time
    current_time = time()
    
    if current_time - last_press_time <= double_press_threshold:
        print("Double press detected!"+ str(current_time - last_press_time))
    last_press_time = current_time

def on_release():
    print("Button released!")

button = Button(19)

button.when_pressed = on_press  # Trigger on press
button.when_released = on_release  # Trigger on release

while True:
    if encoder.value != last_position:
        print(f"Rotary position: {encoder.value}")
        last_position = encoder.value




