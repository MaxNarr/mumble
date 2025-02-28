from gpiozero import RotaryEncoder
from gpiozero import Button
from signal import pause

encoder = RotaryEncoder(17, 18, wrap=True)  # Replace with your GPIO pins

last_position = encoder.value
def on_press():
    print("Button pressed!")

def on_release():
    print("Button released!")

button = Button(19)

button.when_pressed = on_press  # Trigger on press
button.when_released = on_release  # Trigger on release

while True:
    if encoder.value != last_position:
        print(f"Rotary position: {encoder.value}")
        last_position = encoder.value




