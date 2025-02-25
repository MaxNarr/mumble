import subprocess
import time


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
    basedirMumble = "../build/"
    
    print("Enter a command (Talk, TalkStop, Listen, ListenStop, Start) or type 'exit' to quit:")
    
    while True:
        user_input = input("> ").strip()
        
        if user_input.lower() == "exit":
            print("Exiting program.")
            break
        
        match user_input:
            case "Talk":
                output = run_command(basedirMumble + "mumble rpc shouttochannel_")
                connectSideToneJack() # so einfach ist es nicht... was bei mehreren channels ?--> mit zählen wie pptcounter,bzw channel list/ map

            case "TalkStop":
                output = run_command(basedirMumble + "mumble rpc stopshouttochannel_")
                disconnectSideToneJack()

            case "Listen":
                output = run_command(basedirMumble + "mumble rpc listentochannelatvolume_")
            case "ListenStop":
                output = run_command(basedirMumble + "mumble rpc stoplistentochannel")
            case "Start":
                output = run_command(basedirMumble + "mumble")
            case "getChannelInfo":
                output = run_command(basedirMumble + "mumble rpc getchannelsinfo") #holt alles in JSON zu den Channels
            case "getUsersInfo":
                output = run_command(basedirMumble + "mumble rpc getusersinfo") #holt alles in JSON zu den Channels
                  
            case _:
                output = "Invalid command"

        print(output)



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

# Example usage
if __name__ == "__main__":
    main()