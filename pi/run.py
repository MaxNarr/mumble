import subprocess
import time
import socket
import xml.etree.ElementTree as ET
import os
import threading

SOCKET_PATH = f"/run/user/{os.getuid()}/python_rpc_serverSocket"
basedirMumble = "../build/"

capture_ports = None
playback_ports = None
jackstarted = False
def main():
    jackstarted = start_jackd()
    processCommands()


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
                    print(f"Received request:\n{data}")
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
                print("here1")
                output = run_command(basedirMumble + "mumble rpc getchannelinfo")
                print("here2")
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
            print(f"Received message from C++: {message}")

            # Create a reply message in XML format
            reply = ET.Element("reply")
            success = ET.SubElement(reply, "succeeded")
            success.text = "true"
            return ET.tostring(reply)
    except Exception as e:
        print(f"Error processing request: {e}")
    return b"<reply><succeeded>false</succeeded></reply>"

# Example usage
if __name__ == "__main__":
    main()
