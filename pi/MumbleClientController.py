import subprocess
import os
import signal
import threading
import mumbleRPC

class MumbleClientController:
    _instance = None

    BASE = "/home/intercom/mumble"
    MUMBLE_BIN = f"{BASE}/build/mumble"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MumbleClientController, cls).__new__(cls)
            cls._instance._mumble_proc = None
            cls._instance.current_url = None
        return cls._instance

    def _delayed_refresh(self):
        import time
        time.sleep(3)
        try:
            mumbleRPC.get_channel_info()
        except Exception as e:
            print("[Client] Delayed channel refresh failed:", e)

    # Build URL from IP + username
    def _make_url(self, ip, username="client"):
        return f"mumble://{username}@{ip}"

    # -------------------------------------------------------------
    # Start client
    # -------------------------------------------------------------
    def connect(self, ip, username="client"):
        url = self._make_url(ip, username)
        self.current_url = url
        print(f"[Client] Connecting to: {url}")

        self.stop()  # stop old instance if running

        self._mumble_proc = subprocess.Popen(
            [self.MUMBLE_BIN, url, "--platform", "offscreen"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
        # Delayed channel refresh
        threading.Thread(target=self._delayed_refresh, daemon=True).start()
        return True

    # -------------------------------------------------------------
    # Stop client
    # -------------------------------------------------------------
    def stop(self):
        if self._mumble_proc is None:
            return
        print("[Client] Stopping Mumble instance...")
        try:
            os.killpg(os.getpgid(self._mumble_proc.pid), signal.SIGTERM)
        except:
            pass
        self._mumble_proc = None

    # -------------------------------------------------------------
    # Reconnect
    # -------------------------------------------------------------
    def reconnect(self):
        if not self.current_url:
            print("[Client] No saved URL to reconnect.")
            return False

        print("[Client] Reconnecting to last URL:", self.current_url)
        self.stop()
        self._mumble_proc = subprocess.Popen(
            [self.MUMBLE_BIN, self.current_url, "--platform", "offscreen"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
        # Delayed channel refresh
        threading.Thread(target=self._delayed_refresh, daemon=True).start()
        return True

    # -------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------
    def close(self):
        self.stop()