import subprocess
import time
import socket
import xml.etree.ElementTree as ET
import os
import threading
from threading import Thread
import json
from displayLib import Tile, UIManager
import displayLib
import mumbleRPC
import jackcontroll
from updater_thread import UpdaterThread
from typing import List
import math
from gpiozero import RotaryEncoder
from gpiozero import Button


SOCKET_PATH = f"/run/user/{os.getuid()}/python_rpc_serverSocket"
MINVOLUME = -2
MAXVOLUME = 2
CALLPHRASE= "calling"

#als GPIO Pinnummer
ENCODER1_PIN_CS = 14
ENCODER1_PIN_DS = 15
ENCODER1_PIN_BTN = 18
ENCODER2_PIN_CS = 2
ENCODER2_PIN_DS = 3
ENCODER2_PIN_BTN = 4

KEY_UP_PIN     = 6 
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13

KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16


capture_ports = None
playback_ports = None
jackstarted = False
tiles: List[displayLib.Tile] = None 
manager: UIManager = None
last_press_time1 = 0
last_press_time2 = 0
double_press_threshold = 0.7  # Maximum time (seconds) between presses
doublePressFlag2 = False


def on_press1():
    print("Button1 pressed!")
    manager.getTile().is_calledByUser=CALLPHRASE
    global last_press_time1
    current_time = time.time()
    diff = current_time - last_press_time1
    if diff <= double_press_threshold :
        print("Double press detected!"+ str(current_time - last_press_time1))
    last_press_time1 = current_time

def on_release1():
    manager.getTile().is_calledByUser=None

def on_press2():
    global last_press_time2, doublePressFlag2
    current_time = time.time()
    diff = current_time - last_press_time2
    if diff <= double_press_threshold :
        doublePressFlag2 = True
    elif doublePressFlag2:        
        doublePressFlag2 = False
        return

    last_press_time2 = current_time
    mumbleRPC.talk(manager.getTile(),on=True)

def on_release2():
    global manager,doublePressFlag2
    print("stop talking1")

    if not doublePressFlag2:
        print("stop talking2")
        mumbleRPC.talk(manager.getTile(),on=False)
        print("stop talking3")
#             # 
#             # 
#             # 
#             # 
#             # 
#             # , etc.

# Event functions for new buttons
def on_press_up():
	ui_manager.on_joystick_up()

def on_release_up():
	pass

def on_press_down():
	ui_manager.on_joystick_down()

def on_release_down():
	pass

def on_press_right():
	ui_manager.on_joystick_right()

def on_release_right():
	pass

def on_press_left():
	ui_manager.on_joystick_left()

def on_release_left():
	pass

def on_press_middle():
	ui_manager.on_joystick_middle()

def on_release_middle():
	pass

def on_press_disp1():
	ui_manager.on_push_button_1()

def on_release_disp1():
	pass

def on_press_disp2():
	pass

def on_release_disp2():
    pass

def main():
    jackstarted = jackcontroll.start_jackd()
    print("1")
    setupDisplay()
    print("2")
    setupControlls()
    print("3")
    processCommandsAndRPC()
    print("4")


def setupControlls():

    global manager
    
    # Start a background thread to watch each encoder
    
    buttonThread = Thread(target=wait_for_buttons, daemon=True)
    encoderThread1 = Thread(target=monitor_encoder1, daemon=True)
    encoderThread2 = Thread(target=monitor_encoder2, args=(manager,) ,daemon=True)
    encoderThread1.start()
    encoderThread2.start()
    buttonThread.start()
    #while True:
    #    time.sleep(0.5)

def wait_for_buttons():
    button1 = Button(ENCODER1_PIN_BTN,pull_up=True, bounce_time=0.02)
    button2 = Button(ENCODER2_PIN_BTN,pull_up=True, bounce_time=0.02)
    
    #new buttons
    button_up = Button(KEY_UP_PIN,pull_up=True, bounce_time=0.02)
    button_down = Button(KEY_DOWN_PIN,pull_up=True, bounce_time=0.02)
    button_right = Button(KEY_RIGHT_PIN,pull_up=True, bounce_time=0.02)
    button_left = Button(KEY_LEFT_PIN,pull_up=True, bounce_time=0.02)
    button_middle = Button(KEY_PRESS_PIN,pull_up=True, bounce_time=0.02)
    button_disp1 = Button(KEY1_PIN,pull_up=True, bounce_time=0.02)
    button_disp2 = Button(KEY2_PIN,pull_up=True, bounce_time=0.02)
    button_disp3 = Button(KEY3_PIN,pull_up=True, bounce_time=0.02)


    button1.when_pressed = on_press1  # Trigger on press
    button1.when_released = on_release1  # Trigger on release
    button2.when_pressed = on_press2  # Trigger on press
    button2.when_released = on_release2  # Trigger on release

    button_up.when_pressed = on_press_up
    button_up.when_released = on_release_up

    button_down.when_pressed = on_press_down
    button_down.when_released = on_release_down

    button_right.when_pressed = on_press_right
    button_right.when_released = on_release_right

    button_left.when_pressed = on_press_left
    button_left.when_released = on_release_left

    button_middle.when_pressed = on_press_middle
    button_middle.when_released = on_release_middle

    button_disp1.when_pressed = on_press_disp1
    button_disp1.when_released = on_release_disp1

    button_disp2.when_pressed = on_press_disp2
    button_disp2.when_released = on_release_disp2

    button_disp3.when_pressed = on_press_disp3
    button_disp3.when_released = on_release_disp3

    print("button is setup")
    while True:
        time.sleep(2)

def monitor_encoder1():
    encoder = RotaryEncoder(ENCODER1_PIN_CS,ENCODER1_PIN_DS, wrap=True,bounce_time=0.01,max_steps=0)  
    old_value = encoder.steps
    while True:
        new_value = encoder.steps
        if new_value != old_value:
            if new_value > old_value:
                manager.nextTile(1,True)
            else:
                manager.nextTile(-1,True)
            old_value = new_value
        time.sleep(0.05)  # or 0.005 or whatever

def monitor_encoder2(manager):
    encoder = RotaryEncoder(ENCODER2_PIN_CS, ENCODER2_PIN_DS, wrap=False,bounce_time=0.01,max_steps=3)  
    print(manager.getTile())
    old_value = encoder.value
    while True:
        new_value = max(MINVOLUME-1, min(math.floor(encoder.value*3), MAXVOLUME))  # the smallest step is 0.33 --> *3 = 1
        if new_value != old_value:
            print("newval: "+str(new_value))
            manager.getTile().set_volume(new_value)
 
            old_value = new_value
        time.sleep(0.05)  # or 0.005 or whatever

#1: 
# drehen: Selection
# drücken: Call
# doppel drücken: Setup ? 
# Selection geht von alleine wieder weg ?

#2:
# drehen: Lautstärke
# drücken: PTT to selection
# doppel drücken: toggle Talk to selection





def setupDisplay():

    # 1) Create some tiles
    global manager
    tiles = [
        Tile(name="Ch A", volume=5),
        Tile(name="Ch B", volume=0),
        Tile(name="Ch C", volume=8, is_calledByUser=CALLPHRASE),
        Tile(name="Ch D", volume=2),
        Tile(name="Ch E", volume=5),
        Tile(name="Ch F", volume=10),
        # ... add as many as you want ...
    ]

    # 2) Create a TileManager
    manager = UIManager(tiles)
    # 3) Render page 0 with layout "4" (4 tiles per page)
    manager.render()
    frameUpdater = UpdaterThread(manager, times=0, interval=0.1) #10fps
    frameUpdater.start()
    #manager.page_selected = True
    #frameUpdater.stop()
    #manager.render(page_number=1, layout="2")

def processCommandsAndRPC():
    """Starts two threads:
       1) One for socket connections
       2) One for user input
    """
    # 1. Create and bind the socket server
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(SOCKET_PATH)
    except OSError:
        print("Removing existing socket file and rebinding...")
        os.remove(SOCKET_PATH)
        server.bind(SOCKET_PATH)

    server.listen(1)
    print(f"Python RPC Server listening on {SOCKET_PATH}...")
    print("Enter a command (Talk, TalkStop, Listen, ListenStop, Start, getchannelinfo, getUsersInfo) or type 'exit' to quit:")

    # 2. Start thread for the socket listener
    socket_thread = threading.Thread(
        target=socket_listener,
        args=(server,),  # pass the server socket
        daemon=True      # daemon=True means it will exit when main thread exits
    )
    socket_thread.start()

    # 3. Start thread for user input (optional; 
    #    or you can do user input on the main thread)
    user_thread = threading.Thread(
        target=user_input_loop,
        daemon=True
    )
    user_thread.start()

    # 4. Keep main thread alive until user types 'exit'
    #    We'll just join the user_thread so the program doesn’t exit immediately
    user_thread.join()

    # 5. Once 'exit' is detected, close the server and remove the socket
    server.close()
    try:
        os.remove(SOCKET_PATH)
    except FileNotFoundError:
        pass
    print("Server and threads stopped.")

def socket_listener(server):
    """Loop forever accepting new connections. Each connection is handled immediately."""
    while True:
        try:
            conn, _ = server.accept()
            with conn:
                data = recv_full_message(conn)
                if data:
                    print("got msg")
                    response = handle_request(data)
                    conn.sendall(response)
        except OSError:
            # If the server socket is closed externally, break out
            break
        except Exception as e:
            print(f"Error in socket_listener: {e}")
            break

def user_input_loop():
    """Loop forever reading user input from stdin."""
    while True:
        user_input = input("> ").strip()
        if user_input.lower() == "exit":
            print("Exiting program.")
            # Return from this thread, which causes .join() to complete
            return
        
        # Dispatch command
        match user_input:
            case "Talk":
                output = mumbleRPC.talk()
            case "TalkStop":
                output = mumbleRPC.talk_stop()
            case "Listen":
                output = mumbleRPC.listen(1,5)
            case "ListenStop":
                output = mumbleRPC(1,-40)
            case "Start":
                output = mumbleRPC.start_mumble
            case "getchannelinfo":
                output = mumbleRPC.get_channel_info
            case _:
                output = "Invalid command"

        print(output)

def recv_full_message(conn):
    buffer = b""
    while True:
        chunk = conn.recv(4096)  # Read in 4KB chunks (adjust as needed)
        if not chunk:
            break  # Connection closed
        buffer += chunk
        if len(chunk) < 4096:  # If chunk is smaller, likely end of message
            break
    return buffer.decode("utf-8")

def handle_request(data):
    try:
        root = ET.fromstring(data)
        if root.tag == "send_message":
            message = root.find("message").text
            #print(f"Received message from C++: {message}")
            channels = getChannelsFromJson(message)
            updateTiles(channels)
            # Create a reply message in XML format
            reply = ET.Element("reply")
            success = ET.SubElement(reply, "succeeded")
            success.text = "true"
            return ET.tostring(reply)
        
        elif root.tag == "call":
            fromuser = root.find("from").text
            tochannel = root.find("to").text
            #print(f"Received message from C++: {message}")
            calledFrom(fromuser,tochannel)
            # Create a reply message in XML format
            reply = ET.Element("reply")
            success = ET.SubElement(reply, "succeeded")
            success.text = "true"
            return ET.tostring(reply)
        
    except Exception as e:
        print(f"Error processing request: {e}")
    return b"<reply><succeeded>false</succeeded></reply>"

def updateTiles(channels):
    tiles = []
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        
        # Create a Tile for each channel (you can set default states or values as needed)
        tile_obj = Tile(
            name=channel_name,
            volume=0,       # Default volume (change if desired)
            is_calledByUser=None,
            selected=False,
            talking=False,
            id=channel_id
        )
        
        tiles.append(tile_obj)
        manager.tiles = tiles
        

def calledFrom(fromuser:str,tochannel:str):
    print("called")
    for channelTile in manager.tiles:
        if channelTile.id == int(tochannel):  # Convert str to int            print("by user: " + str(fromuser))
            channelTile.is_calledByUser = fromuser


def getChannelsFromJson(json_string):
    # Parse the JSON string into a Python list of dictionaries
    return json.loads(json_string)
    # for debug
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        parent_id = channel["parent"]

    return channels

# Example usage
if __name__ == "__main__":
    main()
