from gpiozero import RotaryEncoder

encoder = RotaryEncoder(17, 18, wrap=True)  # Replace with your GPIO pins

last_position = encoder.value

while True:
    if encoder.value != last_position:
        print(f"Rotary position: {encoder.value}")
        last_position = encoder.value