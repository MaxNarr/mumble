import subprocess
import socket
import threading
import time
import os
from zeroconf import Zeroconf, ServiceInfo


class MumbleServerController:
    BASE = "/home/intercom/mumble"
    SERVER_BIN = f"{BASE}/build_server/mumble-server"

    def __init__(self, name="RPi Mumble Server", port=64738, path=SERVER_BIN):
        self.name = name
        self.port = port
        self.path = path
        self.server_process = None
        self.zeroconf = Zeroconf()
        self.service_info = None

    # ------------------------------------------
    # IP HELPER
    # ------------------------------------------
    def get_ip(self):
        # Reliable way to detect LAN IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    # ------------------------------------------
    # ZEROCONF ADVERTISING
    # ------------------------------------------
    def start_advertising(self):
        ip = self.get_ip()
        print(f"[Zeroconf] Advertising server at {ip}:{self.port}")

        self.service_info = ServiceInfo(
            "_mumble._tcp.local.",
            f"{socket.gethostname()}._mumble._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties={},
            server=f"{socket.gethostname()}.local."
        )

        self.zeroconf.register_service(self.service_info)

    def stop_advertising(self):
        if self.service_info:
            print("[Zeroconf] Stopping advertisement…")
            try:
                self.zeroconf.unregister_service(self.service_info)
            except Exception:
                pass
            self.service_info = None

    # ------------------------------------------
    # START/STOP MUMBLE SERVER
    # ------------------------------------------
    def start_server(self):
        if self.server_process:
            print("Server already running.")
            return

        print("[Mumble] Starting server…")
        self.server_process = subprocess.Popen(
            [self.path, "-fg"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Start Zeroconf service
        self.start_advertising()

        # Optional: print server output in background
        threading.Thread(target=self._stream_output, daemon=True).start()

    def _stream_output(self):
        for line in self.server_process.stdout:
            print("[Mumble]", line, end="")

    def stop_server(self):
        if not self.server_process:
            print("Server is not running.")
            return

        print("[Mumble] Stopping server…")
        self.server_process.terminate()

        try:
            self.server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("[Mumble] Force killing server…")
            self.server_process.kill()

        self.server_process = None

        # Stop Zeroconf service
        self.stop_advertising()

    # ------------------------------------------
    # CLEANUP
    # ------------------------------------------
    def close(self):
        self.stop_server()
        self.zeroconf.close()