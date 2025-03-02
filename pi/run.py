import subprocess
import time
import socket
import xml.etree.ElementTree as ET
import os
import threading
from threading import Thread
import json
from displayLib import Tile, TileManager
import displayLib
import mumbleRPC
import jackcontroll
from updater_thread import UpdaterThread
from typing import List
from gpiozero import RotaryEncoder
from gpiozero import Button


SOCKET_PATH = f"/run/user/{os.getuid()}/python_rpc_serverSocket"

capture_ports = None
playback_ports = None
jackstarted = False
channels = None
tiles: List[displayLib.Tile] = None 
manager: TileManager = None
last_press_time1 = 0
last_press_time2 = 0
double_press_threshold = 0.7  # Maximum time (seconds) between presses
doublePressFlag2 = False

def main():
    jackstarted = jackcontroll.start_jackd()
    setupDisplay()
    setupControlls()
    processCommandsAndRPC()


def setupControlls():

    encoder2 = RotaryEncoder(18, 17, wrap=False,bounce_time=0.01)  
    encoder1 = RotaryEncoder(26,20, wrap=False,bounce_time=0.01)  

    last_position1 = encoder1.value
    last_position2 = encoder2.value

    button2 = Button(19,pull_up=True, bounce_time=0.02)
    button1 = Button(21,pull_up=True, bounce_time=0.02)

    button1.when_pressed = on_press1  # Trigger on press
    button1.when_released = on_release1  # Trigger on release
    button2.when_pressed = on_press2  # Trigger on press
    button2.when_released = on_release2  # Trigger on release

    # Start a background thread to watch each encoder
    t1 = Thread(target=monitor_encoder1, args=(encoder1,), daemon=True)
    t2 = Thread(target=monitor_encoder2, args=(encoder2,), daemon=True)
    t1.start()
    t2.start()


def monitor_encoder1(encoder):
    old_value = encoder.value
    while True:
        new_value = encoder.value
        if new_value != old_value:
            global manager
            if new_value > old_value:
                manager.nextTile(1,True)
            else:
                manager.nextTile(-1,True)
            old_value = new_value
        time.sleep(0.05)  # or 0.005 or whatever

def monitor_encoder2(encoder):
    old_value = encoder.value
    while True:
        new_value = encoder.value
        if new_value != old_value:
            global manager
            if new_value > old_value:
                manager.getTile().set_volume =manager.getTile().volume +1
            else:
                manager.getTile().set_volume =manager.getTile().volume -1
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

def on_press1():
    print("Button1 pressed!")
    manager.getTile().is_called=True
    global last_press_time1
    current_time = time.time()
    diff = current_time - last_press_time1
    if diff <= double_press_threshold :
        print("Double press detected!"+ str(current_time - last_press_time1))
    last_press_time1 = current_time

def on_release1():
    manager.getTile().is_called=False

def on_press2():
    print("Button2 pressed!")
    global last_press_time2, tiles, doublePressFlag2
    current_time = time.time()
    diff = current_time - last_press_time2
    if diff <= double_press_threshold :
        doublePressFlag2 = True
    last_press_time2 = current_time
    mumbleRPC.talk(manager.getTile(),on=True)

def on_release2():
    global manager,doublePressFlag2
    if not doublePressFlag2:
        mumbleRPC.talk(manager.getTile(),on=False)
        print("stop talking")



def setupDisplay():

    # 1) Create some tiles
    global tiles, manager
    tiles = [
        Tile(name="Ch A", volume=5),
        Tile(name="Ch B", volume=0),
        Tile(name="Ch C", volume=8, is_called=True),
        Tile(name="Ch D", volume=2),
        Tile(name="Ch E", volume=5),
        Tile(name="Ch F", volume=10),
        # ... add as many as you want ...
    ]

    # 2) Create a TileManager
    manager = TileManager(tiles)
    print("render first tiles")
    # 3) Render page 0 with layout "4" (4 tiles per page)
    manager.render(page_number=0, layout="4")
    i = 0
    #manager.page_selected = True
    #frameUpdater = UpdaterThread(manager, times=0, interval=0.2) #10fps
    #frameUpdater.start()

    time.sleep(3)

    tiles[2].is_called = False
    #frameUpdater.stop()


    # Re-render the same page
    manager.render(page_number=0, layout="4")
    #time.sleep(3)

    # 5) Switch to layout "2" (2 tiles per page) on page 1, for example
    #manager.render(page_number=1, layout="2")
    #time.sleep(3)


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
            global channels 
            channels = getChannelsFromJson(message)
            updateTiles(channels)
            # Create a reply message in XML format
            reply = ET.Element("reply")
            success = ET.SubElement(reply, "succeeded")
            success.text = "true"
            return ET.tostring(reply)
    except Exception as e:
        print(f"Error processing request: {e}")
    return b"<reply><succeeded>false</succeeded></reply>"

def updateTiles(channels):
    global tiles
    tiles = []
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        
        # Create a Tile for each channel (you can set default states or values as needed)
        tile_obj = Tile(
            name=channel_name,
            volume=0,       # Default volume (change if desired)
            is_called=False,
            selected=False,
            talking=False,
            id=channel_id
        )
        
        tiles.append(tile_obj)

def getChannelsFromJson(json_string):
    # Parse the JSON string into a Python list of dictionaries
    channels = json.loads(json_string)
    # Loop through each channel in the list
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        parent_id = channel["parent"]

    return channels

# Example usage
if __name__ == "__main__":
    main()
