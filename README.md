# PTZ Camera Centralized Controller & Remote Viewer

A distributed application for controlling PTZ (Pan-Tilt-Zoom) cameras, recording video streams, and automating motion sequences.

This project is built on a **split-architecture** design:
1. A central **Windows Server** handles all heavy lifting (video capture, FFmpeg processing, API hosting, and PTZ controls).
2. A lightweight **Raspberry Pi Viewer** acts as a digital signage thin-client, displaying the live camera feed, recording indicators, and playing back the final automated videos.
3. The **Web Interface** acts purely as a remote control panel (without the live video feed) to trigger movements and recordings.

---

## Features

- **Centralized Processing**: Zero video processing or OpenCV load on the Raspberry Pi; all recording and FFmpeg rendering happens on the Windows machine.
- **Dedicated Remote Control UI**: A responsive, uniform flexbox web interface for executing PTZ commands and starting recordings.
- **Automated Motion Sequences**: Create custom sequences of PTZ commands ("recipes") synced perfectly with video recording.
- **Smart Digital Signage (Pi Viewer)**:
  - Streams the live MJPEG feed from the Windows server.
  - Automatically displays a dynamic "Recording" GIF when sequences are active.
  - Hardware-accelerated playback of the final `latest.mp4` video directly on the TV/Monitor upon completion.
  - Fallback synthetic OpenCV GIF generation if real GIF assets aren't present.

---

## System Architecture

The application is split into two primary nodes:

### 1. The Windows Server (`app.py`)
- Manages a persistent background thread that continuously reads frames from the camera.
- Exposes API endpoints for PTZ movement (`ptz_controller.py`) and motion recipes (`motion_engine.py`).
- Saves high-res MP4 video directly to disk (e.g., `C:\SavedPTZVideos`).
- Executes FFmpeg (`video_processor.py`) to fade, append montages, and add audio.
- Exposes the `/api/viewer/state` endpoint to orchestrate the remote display.

### 2. The Raspberry Pi Display (`pi_viewer.py`)
- Connected via HDMI to a television or monitor.
- Runs an un-throttled OpenCV window to display the live feed.
- Polls the Windows server state every second to switch between Live View, Recording Indicators, and Video Playback (via `cvlc` / VLC).

---

## Installation: Windows Server (Backend)

### Prerequisites
- Python 3.8+
- Network access to your PTZ camera (RTSP / HTTP)
- [FFmpeg installed](https://ffmpeg.org/download.html) and added to your system PATH.

### Setup
1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure Settings** in `app.py`:
```python
CAMERA_IP = "192.168.1.11"         # Your camera IP
CAMERA_USER = "admin"               # Camera username
CAMERA_PASSWORD = "password"        # Camera password
RECORDINGS_DIR = r"C:\SavedPTZVideos" # Where to save and render videos
```

3. **Ensure Output Directories & Assets Exist**:
Create the directory above. If you plan to use the automated "Motion Video" feature, you **must** place a `montage.mp4` and `audio.mp3` inside that folder, or the post-processing will fail.

4. **Run the Server**:
```bash
python app.py
```
*The web interface is now available on your network at `http://YOUR_WINDOWS_IP:5000`.*

---

## Installation: Raspberry Pi (Viewer)

### Prerequisites
- Raspberry Pi connected to a screen via HDMI.
- VLC Media Player installed (for hardware-accelerated playback).

### Setup
1. **Install Dependencies**:
```bash
sudo apt update
sudo apt install -y vlc python3-opencv python3-numpy
```
*(No need to install the heavy `requirements.txt` from the server on the Pi)*

2. **Configure Settings** in `pi_viewer.py`:
Open the file and point it to the IP address of your Windows machine:
```python
SERVER_IP = "192.168.1.100"  # Change this to your Windows Server IP
SERVER_PORT = 5000
```

3. **Optional (GIFs)**:
Place a `recording.gif` and `processing.gif` in the `/tmp/` directory of the Pi for the coolest visual effects. If you don't provide them, the script will automatically generate a synthetic blinking text screen.

4. **Run the Viewer**:
```bash
python3 pi_viewer.py
```

---

## Usage Guide

1. **Remote Control**: Open a web browser on your phone, tablet, or laptop and navigate to the Windows server's IP address (e.g. `http://192.168.1.100:5000`).
2. **Move Camera**: Use the manual directional arrows or presets to frame the shot.
3. **Save Motion Video**:
    - Click "Save Motion Video" on the web interface.
    - The TV connected to the Raspberry Pi will immediately switch from the live feed to the "Recording" GIF.
    - The camera will perform the pre-programmed pan/tilt sequence.
    - Once finished, the TV will show "Processing Final Video" while the Windows machine runs FFmpeg.
    - The fully rendered `latest.mp4` video will automatically play full-screen on the TV.
4. **Replay Latest Video**: At any time, press the red "Replay Latest Video" button on your web remote to force the Pi to play the last rendered video again.

---

## Customization

### Camera Configuration
Different camera manufacturers use different RTSP stream URLs. If the server cannot connect to the stream, modify the `stream_urls` array in `video_capture.py`:
```python
self.stream_urls = [
    f"rtsp://{username}:{password}@{camera_ip}:554/stream1", # Standard
    f"rtsp://{username}:{password}@{camera_ip}:554/cam/realmonitor?channel=1&subtype=0", # Dahua
]
```

### Video Codecs
To change the recording format from MP4 to AVI, edit the `fourcc` codec in `video_capture.py` (e.g., `cv2.VideoWriter_fourcc(*'XVID')`) and change the file extensions.

---

## License
MIT License - Feel free to modify and use as needed.
