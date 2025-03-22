#!/bin/bash

# Get the current hostname
HOSTNAME=$(hostname)

# 1. Activate virtual environment and run Python script
echo "[$(date)] Starting Python backend..."
source ~/mumble/pi/venv/bin/activate
python ~/mumble/pi/run.py &

# 2. Launch Mumble in headless mode
echo "[$(date)] Starting Mumble client as $HOSTNAME..."
~/mumble/build/mumble mumble://${HOSTNAME}@intercom0.local --platform offscreen &

# 3. Wait for Mumble to connect
sleep 1

# 4. Run RPC command
echo "[$(date)] Running Mumble RPC..."
~/mumble/build/mumble rpc getchannelinfo --platform offscreen