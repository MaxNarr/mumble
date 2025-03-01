import subprocess
import time
import socket
import xml.etree.ElementTree as ET
import os
import threading
import json
from displayLib import Tile, TileManager
import displayLib

SOCKET_PATH = f"/run/user/{os.getuid()}/python_rpc_serverSocket"
basedirMumble = "../build/"

capture_ports = None
playback_ports = None
jackstarted = False
channels = None

def main():
    jackstarted = start_jackd()
    menue()
    processCommands()

def menue():
 # 1) Use the tile demos
 
 #   displayLib.display_four_tiles(
 #       tile_colors=[(0,0,0),(0,0,255),(255,255,255),(255,0,0)],
 #       label="Channel"
 #   )
 #   time.sleep(2)

 #   displayLib.display_two_tiles(label="Two Tiles Demo")
 #   time.sleep(2)

    # 2) Use the 6-tile menu
    #displayLib.display_six_tile_menu(selected_tile=2,
            #labels=["Option A","Option B","Option C",
             #       "Option D","Option E","Option F"])
    #time.sleep(2)

    # 3) Use the keyboard
    #    We'll 'scroll' right +1, then select, etc.
    #displayLib.process_input(+1, False)  # move selection right
    #time.sleep(1)

    #displayLib.process_input(0, True)    # select current letter
    #time.sleep(1)

    # Get typed text
    #text = displayLib.get_textfield_content()
    #print("Typed text so far:", text)

    # 1) Create some tiles
    tiles = [
        Tile(name="Channel A", volume=5),
        Tile(name="Channel B", volume=0, talking=True),
        Tile(name="Channel C", volume=8, is_called=True),
        Tile(name="Channel D", volume=2),
        Tile(name="Channel E", volume=5),
        Tile(name="Channel F", volume=10),
        # ... add as many as you want ...
    ]

    # 2) Create a TileManager
    manager = TileManager(tiles)

    # 3) Render page 0 with layout "4" (4 tiles per page)
    manager.render(page_number=0, layout="4")
    i = 0
    while True:
        manager.update()
        time.sleep(0.1)
        i += 1
        if i > 50:
            break

    time.sleep(3)

    # 4) Toggle some states
    tiles[0].selected = True
    tiles[2].is_called = False
    tiles[2].talking = True

    # Re-render the same page
    manager.render(page_number=0, layout="4")
    time.sleep(3)

    # 5) Switch to layout "2" (2 tiles per page) on page 1, for example
    manager.render(page_number=1, layout="2")
    time.sleep(3)



def run_command(command, timeout=10):
    """Runs a shell command with a timeout and returns its output as a string."""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"


def processCommands():
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
        args=(basedirMumble,),
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

def user_input_loop(basedirMumble):
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
                output = run_command(basedirMumble + "mumble rpc shouttochannel_1")
                connectSideToneJack()

            case "TalkStop":
                output = run_command(basedirMumble + "mumble rpc stopshouttochannel_1")
                disconnectSideToneJack()

            case "Listen":
                output = run_command(basedirMumble + "mumble rpc listentochannelatvolume_1_10")
            case "ListenStop":
                output = run_command(basedirMumble + "mumble rpc listentochannelatvolume_1_-40")
            case "Start":
                output = run_command(basedirMumble + "mumble")
            case "getchannelinfo":
                output = run_command(basedirMumble + "mumble rpc getchannelinfo")
            case "getUsersInfo":
                output = run_command(basedirMumble + "mumble rpc getusersinfo")
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


def start_jackd(interface="hw:2", sample_rate=48000, buffer_size=128, periods=3):
    """
    Starts the JACK audio server with ALSA as the backend.
    
    :param interface: ALSA device (e.g., "hw:0" or "hw:1").
    :param sample_rate: Sample rate in Hz.
    :param buffer_size: Buffer size in frames.
    :param periods: Number of periods per buffer.
    """
    jack_command = f"jackd -d alsa -d {interface} -r {sample_rate} -p {buffer_size} -n {periods}"
    
    try:
        print("Starting JACK server...")
        jack_process = subprocess.Popen(jack_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)  # Give JACK time to initialize

        # Verify JACK is running
        result = subprocess.run("jack_lsp", shell=True, text=True, capture_output=True)
        if "system" not in result.stdout:
            print("Error: JACK did not start properly.")
            jack_process.terminate()
            return False
        
        print("JACK server started successfully.")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

def connect_jack_ports(source, destination, disconnect=False):
    """
    Connects two JACK ports using `jack_connect`.

    :param source: The source JACK port (e.g., "system:capture_1").
    :param destination: The destination JACK port (e.g., "system:playback_1").
    :param disconnect: if true it disconnects this rout, if false it connects

    """

    condisconType = "connect"
    if disconnect: condisconType ="disconnect"

    try:
        result = subprocess.run(f"jack_{condisconType} {source} {destination}", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Connected {source} -> {destination}")
        else:
            print(f"Failed to connect {source} -> {destination}: {result.stderr.strip()}")
    except Exception as e:
        print(f"Error connecting {source} -> {destination}: {e}")

def connectSideToneJack():
    """
    Sets up JACK connections between input and output ports.
    """
    global capture_ports, playback_ports  # <-- Declare them as global

    try:
        # List available ports
        result = subprocess.run("jack_lsp", shell=True, capture_output=True, text=True)
        ports = result.stdout.strip().split("\n")

        capture_ports = [p for p in ports if "capture" in p]
        playback_ports = [p for p in ports if "playback" in p]

        if not capture_ports or not playback_ports:
            print("Error: No valid JACK ports found.")
            return
        
        # Connect first capture to all playback (adjust as needed)
        for i in range(max(len(capture_ports), len(playback_ports))):
            connect_jack_ports(capture_ports[0], playback_ports[i])

    except Exception as e:
        print(f"Error setting up JACK connections: {e}")

def disconnectSideToneJack():
    """
    Close up JACK connections between input and output ports.
    """
    global capture_ports, playback_ports  # <-- Declare them as global
    try:
        if not capture_ports or not playback_ports:
            print("Error: No valid JACK ports found.")
            return
        # Connect first capture to all playback (adjust as needed)
        for i in range(max(len(capture_ports), len(playback_ports))):
            connect_jack_ports(capture_ports[0], playback_ports[i],True)

    except Exception as e:
        print(f"Error setting up JACK connections: {e}")


def handle_request(data):
    try:
        root = ET.fromstring(data)
        if root.tag == "send_message":
            message = root.find("message").text
            #print(f"Received message from C++: {message}")
            global channels 
            channels = getChannelsFromJson(message)
            # Create a reply message in XML format
            reply = ET.Element("reply")
            success = ET.SubElement(reply, "succeeded")
            success.text = "true"
            return ET.tostring(reply)
    except Exception as e:
        print(f"Error processing request: {e}")
    return b"<reply><succeeded>false</succeeded></reply>"


def getChannelsFromJson(json_string):

    # Parse the JSON string into a Python list of dictionaries
    channels = json.loads(json_string)

    # Loop through each channel in the list
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        parent_id = channel["parent"]
        
        # Do something with each channel
        print(f"Channel ID: {channel_id}, Name: {channel_name}, Parent: {parent_id}")
    return channels

# Example usage
if __name__ == "__main__":
    main()
