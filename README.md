# PTZ Camera Controller & Video Recorder

A Flask-based web application for controlling PTZ (Pan-Tilt-Zoom) cameras and recording video streams.

## Features

- **Live Video Feed**: Real-time camera view displayed on the web interface
- **Video Recording**: Start/stop recording with automatic file naming (MP4 format)
- **PTZ Control**: 
  - 8-directional movement control
  - Zoom in/out
  - Preset positions (save and recall)
- **Motion Recipes**: Create custom, automated sequences of PTZ commands
- **Automated Motion Video Capture**: One-click combination of automatic recording and executing a motion recipe
- **Web Interface**: Clean, responsive, uniform flexbox UI for all controls
- **Recording Management**: View and download all recordings

## Video Format: MP4 vs AVI

The application uses **MP4** format for recordings. Here's why:

### MP4 Advantages:
- ✅ **Better compression**: Smaller file sizes (typically 50-70% smaller than AVI)
- ✅ **Universal compatibility**: Works on all devices, browsers, and media players
- ✅ **Streaming support**: Can start playing before fully downloaded
- ✅ **Modern standard**: Better metadata support

### AVI Characteristics:
- ⚠️ **Larger files**: Minimal compression, takes more disk space
- ✅ **Simpler format**: Less processing overhead during recording
- ⚠️ **Limited browser support**: May not play directly in some browsers

**Recommendation**: MP4 is better for most use cases. Only switch to AVI if you need uncompressed footage for editing or have compatibility issues with MP4.

## System Architecture

The application is split into three main modules:

1. **app.py**: Main Flask application and API endpoints. It manages a persistent background thread that continuously reads frames from the camera. This ensures a stable stream connection.
2. **ptz_controller.py**: PTZ camera control (supports HTTP API and ONVIF)
3. **video_capture.py**: Video stream capture and recording using OpenCV. It now utilizes a shared frame-provider model—when recording begins, it seamlessly writes the pre-fetched frames from `app.py` directly to the output file rather than spinning up a redundant camera connection.

## Installation

### Prerequisites

- Python 3.8 or higher
- Network access to your PTZ camera
- Camera must support RTSP or HTTP video streaming

### Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure camera settings** in `app.py`:
```python
CAMERA_IP = "192.168.1.11"        # Your camera IP
CAMERA_USER = "admin"              # Camera username
CAMERA_PASSWORD = "admin"          # Camera password
RECORDINGS_DIR = "recordings"      # Where to save videos
```

3. **Create recordings directory**:
```bash
mkdir recordings
```

## Camera Configuration

### Finding Your Camera's Stream URL

Different camera manufacturers use different streaming URLs. The application tries multiple common formats, but you may need to customize the URLs in `video_capture.py`:

```python
self.stream_urls = [
    f"rtsp://{username}:{password}@{camera_ip}:554/stream1",
    f"rtsp://{username}:{password}@{camera_ip}:554/cam/realmonitor?channel=1&subtype=0",
    # Add your camera's specific URL here
]
```

Common formats by manufacturer:
- **Dahua**: `rtsp://user:pass@ip:554/cam/realmonitor?channel=1&subtype=0`
- **Hikvision**: `rtsp://user:pass@ip:554/Streaming/Channels/101`
- **Axis**: `rtsp://user:pass@ip/axis-media/media.amp`
- **Foscam**: `rtsp://user:pass@ip:554/videoMain`

### PTZ Command Configuration

The PTZ controller uses HTTP CGI commands by default. If your camera uses different commands, modify the endpoints in `ptz_controller.py`:

```python
self.base_url = f"http://{camera_ip}/cgi-bin/ptz.cgi"
```

For ONVIF support, install the optional library:
```bash
pip install onvif-zeep
```

## Running the Application

1. **Start the Flask server**:
```bash
python app.py
```

2. **Open your browser** and navigate to:
```
http://localhost:5000
```

3. **Access from other devices** on your network:
```
http://YOUR_COMPUTER_IP:5000
```

## Usage

### Recording Video

1. Click **"Start Recording"** to begin capturing video
2. The status will change to "Recording" with a red indicator
3. Click **"Stop Recording"** to finish
4. Videos are automatically saved with timestamps

### Automated Motion Video Capture
1. Go to the "Motion Recipe" section on the dashboard
2. Click **"Save Motion Video"**
3. The server will begin instantaneously appending incoming frames to a recording file and subsequently run a predefined sequence of PTZ movements (a motion recipe).
4. Recording stops automatically once the motion sequence is finished. Because recording does not require a new RTSP connection under the hood, this process is smooth, instantaneous, and network-efficient.
5. **Post-Processing:** Upon completion, the backend will automatically invoke `FFmpeg` to fade out the last 1 second of the clip, append `montage.mp4` to the timeline, completely overwrite the track with `audio.mp3`, and output the final video as `latest.mp4`.
    - Note: For post-processing to work, you must ensure you have `ffmpeg` installed on your system. You must also place your `montage.mp4` and `audio.mp3` files in your configured `RECORDINGS_DIR` (e.g. `C:\SavedPTZVideos\`).

### PTZ Control

- Use the **directional arrows** to pan/tilt the camera
- Hold down the buttons for continuous movement
- Click **STOP** in the center to halt movement
- Use **Zoom In/Out** buttons for zoom control

### Presets

1. Move camera to desired position
2. Click **"Set 1"** (or 2, 3, 4) to save the position
3. Click **"Goto 1"** to return to that position later

### Viewing Recordings

- All recordings appear in the "Recordings" section
- Click **Download** to save to your computer
- Recordings are stored in the `recordings/` directory

## File Structure

```
.
├── app.py                  # Main Flask application
├── ptz_controller.py       # PTZ control module
├── video_capture.py        # Video recording module
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Web interface
└── recordings/            # Saved video files
```

## API Endpoints

### Recording
- `POST /api/recording/start` - Start recording
- `POST /api/recording/stop` - Stop recording
- `GET /api/recording/status` - Get recording status

### Motion Recipes
- `POST /api/motion/play` - Play the default motion recipe (without recording)
- `POST /api/motion/record` - Start video recording, play the motion recipe, and cleanly stop recording when done

### PTZ Control
- `POST /api/ptz/move` - Move camera (direction, speed)
- `POST /api/ptz/stop` - Stop movement
- `POST /api/ptz/zoom` - Zoom in/out
- `POST /api/ptz/preset/goto` - Go to preset
- `POST /api/ptz/preset/set` - Save preset

### Recordings
- `GET /api/recordings` - List all recordings
- `GET /recordings/<filename>` - Download recording

## Troubleshooting

### Cannot connect to camera stream

1. **Verify camera IP**: Ping the camera
   ```bash
   ping 192.168.1.11
   ```

2. **Check credentials**: Ensure username/password are correct

3. **Test RTSP stream**: Use VLC Media Player
   - Open Network Stream
   - Enter: `rtsp://username:password@192.168.1.11:554/stream1`

4. **Check camera settings**: 
   - RTSP must be enabled in camera settings
   - Port 554 must be open
   - Verify stream path in camera documentation

### PTZ commands not working

1. Check camera manufacturer documentation for correct API endpoints
2. Some cameras require ONVIF protocol instead of HTTP
3. Verify camera supports PTZ commands (not all IP cameras have PTZ)

### Recording file is empty or corrupted

1. Ensure camera stream is accessible
2. Check disk space in recordings directory
3. Try different video codec (change XVID to MJPG in video_capture.py)

### High CPU usage during recording

1. Reduce video resolution in camera settings
2. Lower FPS (frames per second)
3. Use hardware encoding if available

## Customization

### Change video format back to AVI

If you prefer AVI format, in `video_capture.py`, change:
```python
# Line ~75: Change filename extension
self.current_filename = f"recording_{timestamp}.avi"

# Line ~100: Change codec
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Instead of 'mp4v'
```

### Change video codec

In `video_capture.py`, modify:
```python
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Current (MP4)
# Other options:
# 'XVID' - AVI format (better compatibility with some systems)
# 'H264' - Better compression (requires ffmpeg)
# 'MJPG' - Motion JPEG (larger files, better for editing)
```

### Change output format

Replace `.mp4` with `.avi` for AVI files (and adjust codec accordingly).

### Adjust recording quality

Modify camera's stream settings to change resolution and bitrate.

## Security Notes

- **Change default credentials** in production
- Use HTTPS for secure communication
- Implement authentication for the web interface
- Restrict network access to trusted devices

## License

MIT License - Feel free to modify and use as needed.

## Support

For issues specific to your camera model, consult your camera's documentation for:
- RTSP stream URLs
- PTZ command API
- Supported protocols (HTTP, ONVIF)
