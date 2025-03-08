import subprocess
import jackcontroll
from displayLib import Tile
import os

BASEDIR_MUMBLE = os.path.expanduser("~/mumble/build/")
#BASEDIR_MUMBLE = "/home/coms2/intercom_mumble/mumble/build/"  # Adjust to your environment
PLATFORM_PARAM = "-platform offscreen"
def talk(channel: Tile , on=True, toggle=False):
    """
    Example: mumble rpc shouttochannel_{channel_id}
    """
    if toggle:
        channel.talking = not channel.talking
    else:
        channel.talking = on

    if channel.talking:
        cmd = f"{BASEDIR_MUMBLE}mumble rpc shouttochannel_{channel.id} {PLATFORM_PARAM}"
        output = run_command(cmd)
        jackcontroll.connectSideToneJack()
    else:
        cmd = f"{BASEDIR_MUMBLE}mumble rpc stopshouttochannel_{channel.id} {PLATFORM_PARAM}"
        output = run_command(cmd)
        jackcontroll.disconnectSideToneJack()
    return output

def listen(channel: Tile ):
    """
    Example: mumble rpc listentochannelatvolume_{channel_id}_{volume}
    """
    cmd = f"{BASEDIR_MUMBLE}mumble rpc listentochannelatvolume_{channel.id}_{channel.volume * 10} {PLATFORM_PARAM}" #da mumble -30...30. wir senden aber nur bis 20
    output = run_command(cmd)
    return output


def start_mumble():
    """
    Example: mumble
    """
    cmd = f"{BASEDIR_MUMBLE}mumble {PLATFORM_PARAM}"
    output = run_command(cmd)
    return output


def get_channel_info():
    """
    Example: mumble rpc getchannelinfo
    """
    cmd = f"{BASEDIR_MUMBLE}mumble rpc getchannelinfo {PLATFORM_PARAM}"
    output = run_command(cmd)
    return output

def call(channel: Tile ):
    cmd = f"{BASEDIR_MUMBLE}mumble rpc calltochannel_{channel.id} {PLATFORM_PARAM}"
    output = run_command(cmd)
    return output

def run_command(command, timeout=10):
    """Runs a shell command with a timeout and returns its output as a string."""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"