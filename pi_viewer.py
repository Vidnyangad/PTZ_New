import cv2
import urllib.request
import json
import time
import subprocess
import os
import sys

# Configuration
SERVER_IP = "192.168.1.100"  # Change this to your Windows Server IP
SERVER_PORT = 5000
BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"
POLL_INTERVAL = 1.0  # seconds

import numpy as np

# In a real environment, you would place actual .gif files here.
# For demonstration without external assets, we use OpenCV VideoCapture
# which can natively read .gif files if they exist.
# If no real GIF is found, we fall back to generating synthetic animated "GIF-like" frames in memory.
RECORDING_GIF_PATH = "/tmp/recording.gif"
PROCESSING_GIF_PATH = "/tmp/processing.gif"

def generate_synthetic_gif_frames(text, bg_color):
    """Generates a list of frames to act as a synthetic GIF"""
    frames = []
    # Create 10 frames with a blinking "Recording" indicator
    for i in range(10):
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        img[:] = bg_color

        # Blinking logic (visible on even frames)
        if i % 2 == 0:
            cv2.putText(img, text, (250, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)

        frames.append(img)
    return frames

# Pre-generate synthetic frames in memory (used if no real .gif is found)
synthetic_recording_frames = generate_synthetic_gif_frames("RECORDING IN PROGRESS...", (0, 0, 150))
synthetic_processing_frames = generate_synthetic_gif_frames("PROCESSING FINAL VIDEO...", (0, 100, 150))

def get_server_state():
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/viewer/state")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get('state', 'idle')
    except Exception as e:
        print(f"Error checking state: {e}")
        return 'offline'

def play_video(video_url):
    print(f"Playing video: {video_url}")
    # On Raspberry Pi, cv2 video playback can be slow.
    # VLC or ffplay is much better for hardware acceleration.
    # We will try cv2 first for simplicity, but fallback to subprocess cvlc/ffplay is recommended for prod.

    # Check if cvlc is available (standard on Raspberry Pi OS)
    try:
        # --play-and-exit plays it once and quits. -f is fullscreen
        cmd = ["cvlc", "--play-and-exit", "-f", video_url]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except FileNotFoundError:
        pass

    # Fallback to cv2
    cap = cv2.VideoCapture(video_url)
    cv2.namedWindow('Viewer', cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('Viewer', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    delay = int(1000 / fps)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('Viewer', frame)
        if cv2.waitKey(delay) & 0xFF == 27: # ESC
            break

    cap.release()

class GifPlayer:
    def __init__(self, gif_path, synthetic_frames):
        self.gif_path = gif_path
        self.synthetic_frames = synthetic_frames
        self.cap = None
        self.frame_idx = 0
        self.is_real_gif = os.path.exists(gif_path)

        if self.is_real_gif:
            self.cap = cv2.VideoCapture(gif_path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 10
            self.delay = int(1000 / self.fps)
        else:
            self.delay = 200 # 200ms per frame

    def read_frame(self):
        if self.is_real_gif and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                # Loop back to beginning
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                return cv2.resize(frame, (1280, 720)), self.delay

        # Fallback
        frame = self.synthetic_frames[self.frame_idx % len(self.synthetic_frames)]
        self.frame_idx += 1
        return frame, self.delay

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

recording_gif_player = GifPlayer(RECORDING_GIF_PATH, synthetic_recording_frames)
processing_gif_player = GifPlayer(PROCESSING_GIF_PATH, synthetic_processing_frames)

def main():
    print(f"Starting Pi Viewer. Connecting to {BASE_URL}")
    cv2.namedWindow('Viewer', cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty('Viewer', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    stream_cap = None
    current_state = 'offline'

    last_poll_time = 0

    try:
        while True:
            # Poll state, but throttle to POLL_INTERVAL
            current_time = time.time()
            if current_time - last_poll_time >= POLL_INTERVAL:
                new_state = get_server_state()
                last_poll_time = current_time

                # State transitions
                if new_state != current_state:
                    print(f"State changed: {current_state} -> {new_state}")
                    current_state = new_state

                    # Close stream if we are no longer idle
                    if current_state != 'idle' and stream_cap is not None:
                        stream_cap.release()
                        stream_cap = None

            # Handle states
            if current_state == 'offline':
                # Draw offline screen
                img = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(img, "SERVER OFFLINE", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (100, 100, 100), 5)
                cv2.imshow('Viewer', img)
                cv2.waitKey(1000)

            elif current_state == 'recording':
                frame, delay = recording_gif_player.read_frame()
                cv2.imshow('Viewer', frame)
                if cv2.waitKey(delay) & 0xFF == 27:
                    break

            elif current_state == 'processing':
                frame, delay = processing_gif_player.read_frame()
                cv2.imshow('Viewer', frame)
                if cv2.waitKey(delay) & 0xFF == 27:
                    break

            elif current_state == 'playback':
                # Play the latest video
                video_url = f"{BASE_URL}/recordings/latest.mp4"

                # Close the opencv window so VLC can take over cleanly
                cv2.destroyAllWindows()
                play_video(video_url)

                # Recreate window
                cv2.namedWindow('Viewer', cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty('Viewer', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

                # Force an immediate poll next loop to avoid re-triggering playback
                # if state is still 'playback' (VLC blocks for a while)
                last_poll_time = 0

            elif current_state == 'idle':
                # Show Live Feed
                if stream_cap is None:
                    stream_url = f"{BASE_URL}/video_feed"
                    stream_cap = cv2.VideoCapture(stream_url)

                ret, frame = stream_cap.read()
                if ret:
                    cv2.imshow('Viewer', frame)
                else:
                    # Reconnect if stream dropped
                    stream_cap.release()
                    stream_cap = None
                    time.sleep(0.5)

                # In idle state, we check for ESC key to exit
                if cv2.waitKey(1) & 0xFF == 27:
                    break

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        if stream_cap:
            stream_cap.release()
        recording_gif_player.release()
        processing_gif_player.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
