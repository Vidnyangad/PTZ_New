"""
Video Capture Module
Handles video stream recording from IP camera
"""
import cv2
import threading
import time
from datetime import datetime
import os


class VideoCapture:
    """
    Video Capture and Recording Manager
    Handles streaming and recording from IP cameras
    """
    
    def __init__(self, camera_ip, username, password, recordings_dir):
        """
        Initialize Video Capture
        
        Args:
            camera_ip: IP address of the camera
            username: Camera username
            password: Camera password
            recordings_dir: Directory to save recordings
        """
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.recordings_dir = recordings_dir
        
        self._is_recording = False
        self._recording_thread = None
        self._stop_event = threading.Event()
        self.current_filename = None
        
        # Video stream URL formats (try multiple formats)
        self.stream_urls = [
            f"rtsp://{username}:{password}@{camera_ip}:554/stream1",
            f"rtsp://{username}:{password}@{camera_ip}:554/cam/realmonitor?channel=1&subtype=0",
            f"rtsp://{username}:{password}@{camera_ip}/live/ch00_0",
            f"http://{username}:{password}@{camera_ip}/video.cgi",
            f"http://{camera_ip}/axis-cgi/mjpg/video.cgi?user={username}&password={password}"
        ]
        
    def is_recording(self):
        """Check if currently recording"""
        return self._is_recording
    
    def start_recording(self):
        """
        Start recording video stream
        
        Returns:
            str: Filename of the recording
        """
        if self._is_recording:
            raise Exception("Already recording")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_filename = f"recording_{timestamp}.mp4"
        filepath = os.path.join(self.recordings_dir, self.current_filename)
        
        # Reset stop event
        self._stop_event.clear()
        
        # Start recording thread
        self._recording_thread = threading.Thread(
            target=self._record_video,
            args=(filepath,),
            daemon=True
        )
        self._is_recording = True
        self._recording_thread.start()
        
        return self.current_filename
    
    def stop_recording(self):
        """
        Stop recording video stream
        
        Returns:
            str: Filename of the stopped recording
        """
        if not self._is_recording:
            raise Exception("Not currently recording")
        
        # Signal the recording thread to stop
        self._stop_event.set()
        
        # Wait for thread to finish
        if self._recording_thread:
            self._recording_thread.join(timeout=10)
        
        self._is_recording = False
        filename = self.current_filename
        self.current_filename = None
        
        return filename
    
    def _record_video(self, filepath):
        """
        Internal method to handle video recording
        
        Args:
            filepath: Path to save the video file
        """
        cap = None
        out = None
        
        try:
            # Try to connect to camera stream
            cap = self._connect_to_stream()
            
            if cap is None or not cap.isOpened():
                print("Failed to connect to camera stream")
                self._is_recording = False
                return
            
            # Read a first frame to ensure stream is valid and dimensions are populated
            # Sometimes cap.get() returns 0 for width/height before reading the first frame.
            ret, first_frame = cap.read()
            if not ret or first_frame is None:
                print("Failed to read initial frame from camera stream")
                self._is_recording = False
                return

            # Get video properties from frame
            frame_height, frame_width = first_frame.shape[:2]
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # Use default FPS if camera doesn't provide it
            if fps == 0 or fps > 60:
                fps = 25
            
            print(f"Recording at {frame_width}x{frame_height} @ {fps}fps")
            
            # Define codec and create VideoWriter for MP4
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filepath, fourcc, fps, (frame_width, frame_height))
            
            if not out.isOpened():
                print("Failed to create video writer")
                self._is_recording = False
                return
            
            # Write the first frame we already read
            out.write(first_frame)
            frame_count = 1
            start_time = time.time()
            
            # Recording loop
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                
                if not ret:
                    print("Failed to read frame, attempting to reconnect...")
                    cap.release()
                    time.sleep(1)
                    cap = self._connect_to_stream()
                    if cap is None:
                        break
                    continue
                
                # Write frame to file
                out.write(frame)
                frame_count += 1
                
                # Print status every 100 frames
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    print(f"Recorded {frame_count} frames ({elapsed:.1f}s)")
                
                # Small delay to prevent CPU overload
                time.sleep(0.001)
            
            print(f"Recording stopped. Total frames: {frame_count}")
            
        except Exception as e:
            print(f"Recording error: {e}")
            self._is_recording = False
            
        finally:
            # Clean up
            if cap:
                cap.release()
            if out:
                out.release()
    
    def _connect_to_stream(self):
        """
        Try to connect to camera stream using various URL formats
        
        Returns:
            cv2.VideoCapture object or None
        """
        for url in self.stream_urls:
            print(f"Trying to connect to: {url}")
            
            try:
                cap = cv2.VideoCapture(url)
                
                # Try to read a test frame
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    print(f"Successfully connected to: {url}")
                    # In livestream RTSP, we can't reliably seek/reset,
                    # so we just return the currently working capture object
                    return cap
                else:
                    cap.release()
                    
            except Exception as e:
                print(f"Failed to connect to {url}: {e}")
                continue
        
        print("Failed to connect to camera with any URL format")
        print("\nPlease check:")
        print("1. Camera IP address is correct")
        print("2. Username and password are correct")
        print("3. Camera supports RTSP or HTTP streaming")
        print("4. Network connectivity to camera")
        print("\nYou may need to update the stream_urls in video_capture.py")
        print("to match your camera's specific URL format.")
        
        return None
    
    def get_snapshot(self):
        """
        Capture a single frame from the camera
        
        Returns:
            numpy.ndarray: Image frame or None
        """
        cap = self._connect_to_stream()
        
        if cap is None:
            return None
        
        try:
            ret, frame = cap.read()
            if ret:
                return frame
            return None
        finally:
            cap.release()
    
    def save_snapshot(self, filename=None):
        """
        Save a snapshot from the camera
        
        Args:
            filename: Optional filename, auto-generated if None
            
        Returns:
            str: Path to saved snapshot
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapshot_{timestamp}.jpg"
        
        filepath = os.path.join(self.recordings_dir, filename)
        
        frame = self.get_snapshot()
        
        if frame is not None:
            cv2.imwrite(filepath, frame)
            return filepath
        else:
            raise Exception("Failed to capture snapshot")
    
    def test_connection(self):
        """
        Test connection to camera
        
        Returns:
            dict: Connection test results
        """
        cap = self._connect_to_stream()
        
        if cap is None:
            return {
                'success': False,
                'message': 'Failed to connect to camera'
            }
        
        try:
            ret, frame = cap.read()
            
            if ret and frame is not None:
                return {
                    'success': True,
                    'message': 'Successfully connected to camera',
                    'resolution': f"{frame.shape[1]}x{frame.shape[0]}",
                    'fps': int(cap.get(cv2.CAP_PROP_FPS))
                }
            else:
                return {
                    'success': False,
                    'message': 'Connected but failed to read frame'
                }
                
        finally:
            cap.release()
    
    def get_mjpeg_stream(self):
        """
        Generator function for MJPEG streaming with optimized settings for low latency
        Yields JPEG frames for live video display in browser
        """
        cap = self._connect_to_stream()
        
        if cap is None:
            # Return a black frame with error text if connection fails
            import numpy as np
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, 'Camera Connection Failed', (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            ret, jpeg = cv2.imencode('.jpg', error_frame)
            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            return
        
        try:
            # Set buffer size to 1 to reduce latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    # Try to reconnect
                    cap.release()
                    time.sleep(0.5)
                    cap = self._connect_to_stream()
                    if cap is None:
                        break
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    continue
                
                # Skip frames to reduce lag (process every 2nd frame)
                frame_count += 1
                if frame_count % 2 != 0:
                    continue
                
                # Resize frame for faster encoding (optional - adjust as needed)
                # Uncomment if you want smaller resolution for faster streaming
                # height, width = frame.shape[:2]
                # frame = cv2.resize(frame, (width // 2, height // 2))
                
                # Encode frame as JPEG with lower quality for speed
                ret, jpeg = cv2.imencode('.jpg', frame, [
                    cv2.IMWRITE_JPEG_QUALITY, 70,  # Reduced from 85 for speed
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1
                ])
                
                if not ret:
                    continue
                
                frame_bytes = jpeg.tobytes()
                
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # No delay - send frames as fast as possible
                
        except GeneratorExit:
            # Client disconnected
            pass
        except Exception as e:
            print(f"MJPEG stream error: {e}")
        finally:
            if cap:
                cap.release()