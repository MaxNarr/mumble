from gpiozero import RotaryEncoder
from gpiozero import Button
from time import time

encoder1 = RotaryEncoder(18, 17, wrap=False,bounce_time=0.01)  # Replace with your GPIO pins
encoder2 = RotaryEncoder(26,20, wrap=False,bounce_time=0.01)  # Replace with your GPIO pins

last_position1 = encoder1.value
last_position2 = encoder1.value
last_press_time1 = 0
last_press_time2 = 0
double_press_threshold = 0.7  # Maximum time (seconds) between presses
button1 = Button(19,pull_up=True, bounce_time=0.02)
button2 = Button(21,pull_up=True, bounce_time=0.02)

def on_press1():
    print("Button1 pressed!")
    global last_press_time1
    current_time = time()
    diff = current_time - last_press_time1
    if diff <= double_press_threshold :
        print("Double press detected!"+ str(current_time - last_press_time1))
    last_press_time1 = current_time
def on_press2():
    print("Button2 pressed!")
    global last_press_time2
    current_time = time()
    diff = current_time - last_press_time2
    if diff <= double_press_threshold :
        print("Double press detected!"+ str(current_time - last_press_time2))
    last_press_time2 = current_time

def on_release1():
    print("Button released!")
def on_release2():
    print("Button released!")

button1.when_pressed = on_press1  # Trigger on press
button1.when_released = on_release1  # Trigger on release
button2.when_pressed = on_press2  # Trigger on press
button2.when_released = on_release2  # Trigger on release


while True:
    if encoder1.value != last_position1:
        print(f"Rotary position1: {encoder1.value}")
        last_position1 = encoder1.value

    if encoder2.value != last_position2:
        print(f"Rotary position2: {encoder2.value}")
        last_position2 = encoder2.value





