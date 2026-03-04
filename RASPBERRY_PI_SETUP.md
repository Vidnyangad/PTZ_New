# Raspberry Pi 4 Setup Guide for PTZ Camera Controller

Moving your PTZ Camera Web Application from a Windows machine to a Raspberry Pi 4 is a great choice! The Pi 4 has plenty of power to handle the video streaming, automated PTZ controls, and the background FFmpeg video rendering.

Follow this step-by-step guide to get everything running perfectly on your Raspberry Pi.

---

## 1. Prepare the Raspberry Pi OS

1. **Install the OS:** Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install **Raspberry Pi OS (64-bit)** (the Debian Bookworm or Bullseye version) onto an SD card. The desktop or "Lite" (headless) version will both work, but "Lite" is recommended if you solely plan to access the camera via a web browser from other devices.
2. **Connect to Network:** Ensure your Pi is connected to the same local network as your PTZ camera (either via Ethernet or Wi-Fi).
3. **Update the System:** Open a terminal on the Pi (or SSH into it) and run:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

## 2. Install System Dependencies

Your application relies on OpenCV and FFmpeg for video processing. These require several underlying C++ libraries to function on Linux.

Install Python 3, pip, git, FFmpeg, and OpenCV system dependencies by running:
```bash
sudo apt install -y python3 python3-pip python3-venv git ffmpeg libsm6 libxext6 libxrender-dev libgl1 libglib2.0-0
```

*Note: `ffmpeg` is absolutely crucial here, as it replaces the Windows executable you were previously using to generate the `latest.mp4` montage.*

## 3. Download the Codebase

Clone your repository from GitHub onto the Raspberry Pi:
```bash
cd ~
git clone https://github.com/Vidnyangad/PTZ_New.git
cd PTZ_New
```

## 4. Setup Python Virtual Environment

It is best practice to install Python packages in a virtual environment on Linux to prevent system conflicts.

```bash
# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the Python requirements
pip install -r requirements.txt
```

*Note: If `opencv-python` fails to build or takes too long, you can optionally use the pre-built Linux headless version by running: `pip uninstall opencv-python && pip install opencv-python-headless`.*

## 5. Modify Hardcoded Windows Paths (IMPORTANT)

Because you moved from Windows to Linux, the hardcoded `C:\SavedPTZVideos` directory will not work and will crash the app when you try to save a video. You must update your Python files to use a Linux file path (such as `/home/pi/SavedPTZVideos`).

**Step 5A: Create the new directory**
```bash
mkdir -p /home/pi/SavedPTZVideos
```
*Don't forget to move your `montage.mp4` and `audio.mp3` files into this new `/home/pi/SavedPTZVideos` folder!*

**Step 5B: Update `app.py`**
Open `app.py` using `nano app.py` and change the `RECORDINGS_DIR` line (around line 45):
```python
# Change this:
RECORDINGS_DIR = r"C:\SavedPTZVideos"

# To this:
RECORDINGS_DIR = "/home/pi/SavedPTZVideos"
```

## 6. Run the Application

With the virtual environment still activated, start the Flask server:
```bash
python app.py
```

You should now be able to access the PTZ control panel by opening a web browser on any device on your network and navigating to:
`http://<RASPBERRY_PI_IP_ADDRESS>:5000`

## 7. Run Automatically on Boot (Optional but Recommended)

If you want the PTZ Controller to automatically start every time you plug in the Raspberry Pi, you can set it up as a systemd service.

1. **Create a service file:**
   ```bash
   sudo nano /etc/systemd/system/ptzcamera.service
   ```

2. **Paste the following configuration** (assuming your username is `pi`):
   ```ini
   [Unit]
   Description=PTZ Camera Flask Application
   After=network.target

   [Service]
   User=pi
   WorkingDirectory=/home/pi/PTZ_New
   Environment="PATH=/home/pi/PTZ_New/venv/bin"
   ExecStart=/home/pi/PTZ_New/venv/bin/python app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ptzcamera.service
   sudo systemctl start ptzcamera.service
   ```

You can check the background logs at any time using: `sudo journalctl -u ptzcamera.service -f`

---

## Troubleshooting

- **"Failed to connect to camera stream":** Ensure the Pi's IP is allowed by the camera (if it has IP filtering) and that the Pi is on the exact same subnet as the camera.
- **"FFmpeg failed":** If you get an error when saving the motion video, verify that `montage.mp4` and `audio.mp3` are definitely located inside the exact path defined by `RECORDINGS_DIR`.
- **Sluggish Performance:** If the 720p resizing and FFmpeg rendering feels slightly slower on the Pi than your PC, ensure you are using a good quality power supply for the Pi 4 (5.1V 3A) so it doesn't dynamically throttle its CPU speed.