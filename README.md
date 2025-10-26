
RPi YOLOv8 LoRaWAN Detector

This project deploys a real-time, motion-activated object detection pipeline on a Raspberry Pi. When the PIR sensor detects motion, the Pi Camera captures a burst of images, which are processed locally by a YOLOv8 model. If an object is detected with sufficient confidence, a separate process is triggered to send the detection data (e.g., "person, 75%") to a LoRaWAN gateway using an Ai-Thinker RA-08H module.

The system is designed to run as a reliable, auto-restarting background service using systemd.

Features

Motion-Triggered: Uses a simple PIR sensor for low-power idle state.

High-Speed Capture: Uses picamera2 to capture high-resolution image bursts directly to RAM.

Local ML Processing: Performs object detection locally using ultralytics YOLOv8, requiring no internet for analysis.

Asynchronous Alerts: Uses subprocess.Popen to launch a separate, non-blocking script for LoRa transmission, so the detection loop is immediately ready for the next event.

Robust Deployment: Includes a setup script to configure the pipeline as a systemd service, ensuring it runs on boot and restarts automatically if it crashes.

Hardware Requirements

Raspberry Pi (Model 3B+ or newer recommended)

Pi Camera (Module 2, 3, or compatible)

PIR Motion Sensor (e.g., HC-SR501)

Ai-Thinker RA-08H (or similar UART-based LoRa module)

Jumper wires & breadboard

Installation Guide

This guide assumes you are running Raspberry Pi OS (formerly Raspbian) based on Debian Bullseye or newer.

1. System Dependencies (Global)

First, update your system and install the core libcamera libraries, Python 3 development tools, and pip. These are the "necessary tools" required to compile dependencies for libraries like picamera2.

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-dev python3-pip python3-venv build-essential libcamera-dev libcamera-apps


2. Project Setup

Clone this repository and create a Python virtual environment (venv) inside the project directory.

# Clone the repository (replace with your URL)
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name

# Create a virtual environment named '.venv'
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# (To deactivate later, just type 'deactivate')


3. Python Dependencies

With your virtual environment active, install all required Python libraries from requirements.txt.

# This will install ultralytics, pyserial, picamera2, etc.
pip install -r requirements.txt


Note: picamera2 is installed inside the virtual environment. The "global" tools from Step 1 were just the system-level libraries it depends on.

4. Serial Port Permissions

To allow your Python script (running as a non-root user) to access the LoRa module connected via /dev/tty..., you must add your user to the dialout group.

sudo usermod -aG dialout $USER


IMPORTANT: You must log out and log back in (or reboot) for this change to take effect.

Configuration

Before running, you may need to adjust settings in the Python files:

monitor_motion.py

SENSOR_PIN: The GPIO pin (BCM numbering) connected to your PIR sensor's output.

BURST_COUNT: Number of images to take when motion is detected.

MODEL_NAME: The YOLOv8 model file to use (e.g., yolov8n.pt).

lora_send.py

serial.Serial(port_name, 9600, ...): Ensure the baud rate (9600) matches your RA-08H module's configuration.

final_at_command = ...: This is the most critical part. You must change this line to match the exact AT command your LoRa module expects for sending hex data.

Example: final_at_command = f"AT+SEND={payload_hex}"

Example 2: final_at_command = f"AT+TX={payload_hex}"

Check your module's datasheet!

Usage

Manual Testing

You can run the script manually at any time for testing. Make sure your virtual environment is active.

# Activate the venv if it's not already
source .venv/bin/activate

# Run the main script
python3 monitor_motion.py


Press Ctrl+C to stop the script.

Deployment as a Service (Recommended)

For a permanent, "headless" deployment, the included setup.sh script will configure and launch the project as a systemd service.

Make the script executable:

chmod +x setup.sh


Run the script with sudo:

sudo ./setup.sh


This script will automatically:

Detect your username (e.g., pi).

Install/update the Python dependencies in the venv.

Create a motion_monitor.service file in /etc/systemd/system/.

Reload systemd, enable the service to start on boot, and start it immediately.

You can check the status and logs of your service at any time:

# Check if the service is running
systemctl status motion_monitor.service

# Watch the live logs
journalctl -f -u motion_monitor.service

