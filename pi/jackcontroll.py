import subprocess
import time
import re

def start_jackd(interface=None, sample_rate=48000, buffer_size=128, periods=3):
    """
    Starts the JACK audio server with ALSA as the backend.
    
    :param interface: ALSA device (e.g., "hw:0" or "hw:1").
    :param sample_rate: Sample rate in Hz.
    :param buffer_size: Buffer size in frames.
    :param periods: Number of periods per buffer.
    """

    if interface== None:
        devices = list_usb_devices()
        card, name, desc = None
        if devices:
            card, name, desc = devices[0]
        interface = "hw:"+ card
    
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


def list_usb_devices():
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print("Error running 'aplay -l':", e)
        return []

    usb_devices = []
    # Example line:
    # "card 0: Device [USB Audio Device], device 0: USB Audio [USB Audio]"
    for line in result.stdout.splitlines():
        if "USB" in line:
            # Extract card number and device information with a regex.
            m = re.search(r'card (\d+):\s*([^\[]+)\[([^]]+)\]', line)
            if m:
                card_number = int(m.group(1))
                name = m.group(2).strip()
                description = m.group(3).strip()
                usb_devices.append((card_number, name, description))
    return usb_devices


#def test():
    # devices = list_usb_devices()
    # if devices:
    #     print("Found USB audio devices:")
    #     for card, name, desc in devices:
    #         print(f"Card {card}: {name} [{desc}]")
    # else:
    #     print("No USB audio devices found.")