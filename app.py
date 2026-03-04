"""
Flask Application for PTZ Camera Control and Video Recording
"""
from flask import Flask, render_template, jsonify, request, send_from_directory, Response
from datetime import datetime
import os
import cv2
import time
import threading
import logging
from ptz_controller import PTZController
from video_capture import VideoCapture
from motion_engine import MotionEngine
from recipes.sample_recipe import recipe as sample_recipe
import video_processor

# ================= SUPPRESS OPENCV/FFMPEG WARNINGS =================
# Suppress H.264 decoding errors (normal for RTSP streams)
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'  # Only show errors, not warnings

# Set FFmpeg log level to quiet (suppress H.264 decode errors)
import warnings
warnings.filterwarnings('ignore')

# ================= LOW LATENCY RTSP =================
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"      # Changed to TCP for more reliability
    "fflags;nobuffer|"
    "flags;low_delay|"
    "max_delay;0|"
    "analyzeduration;0|"       # Don't analyze stream (faster startup)
    "probesize;32"             # Minimal probe (faster startup)
)

# Suppress Flask development server warnings
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Configuration
CAMERA_IP = "192.168.1.11"
CAMERA_USER = "admin"  # Change these credentials
CAMERA_PASSWORD = "password"
RECORDINGS_DIR = r"C:\SavedPTZVideos"
PTZ_PROTOCOL = "onvif"  # Using ONVIF protocol
PTZ_PORT = 8899  # ONVIF port
CAMERA_ADDRESS = 1  # Not used for ONVIF
PREVIEW_FPS = 15  # Frame rate for live preview

# Ensure recordings directory exists
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Initialize PTZ controller and video capture
ptz = PTZController(CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD, protocol=PTZ_PROTOCOL, port=PTZ_PORT, camera_address=CAMERA_ADDRESS)

latest_frame = None
frame_lock = threading.Lock()

def get_latest_frame():
    with frame_lock:
        return None if latest_frame is None else latest_frame.copy()

video_capture = VideoCapture(
    CAMERA_IP,
    CAMERA_USER,
    CAMERA_PASSWORD,
    RECORDINGS_DIR,
    frame_provider=get_latest_frame
)
motion_engine = MotionEngine(ptz)

# Global states for tracking the system status (for the Pi viewer)
# states: 'idle', 'recording', 'processing', 'playback'
server_state = 'idle'
state_lock = threading.Lock()

def set_server_state(new_state):
    global server_state
    with state_lock:
        server_state = new_state
        print(f"Server state changed to: {server_state}")

def get_server_state():
    with state_lock:
        return server_state

# Global state for automated motion sequence status
automated_motion_active = False

# ================= LIVE STREAM WITH SEPARATE THREAD =================

def capture_loop():
    """Continuous frame capture in separate thread with error recovery"""
    global latest_frame
    
    cap = video_capture._connect_to_stream()
    if cap:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    error_count = 0
    max_errors = 10
    
    while True:
        if cap is None or not cap.isOpened():
            time.sleep(1)
            cap = video_capture._connect_to_stream()
            if cap:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                error_count = 0  # Reset error count on reconnect
            continue
        
        try:
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # Verify frame is valid (not corrupted)
                if frame.size > 0:
                    with frame_lock:
                        latest_frame = frame.copy()
                    error_count = 0  # Reset error count on success
            else:
                error_count += 1
                if error_count > max_errors:
                    # Too many errors, reconnect
                    cap.release()
                    cap = None
                    error_count = 0
        except Exception as e:
            # Skip corrupted frames silently
            error_count += 1
            if error_count > max_errors:
                cap.release()
                cap = None
                error_count = 0
        
        time.sleep(0.002)  # Minimal delay

# Start capture thread
threading.Thread(target=capture_loop, daemon=True).start()

def generate_frames():
    """Generate MJPEG stream from captured frames"""
    interval = 1.0 / PREVIEW_FPS
    last_time = time.time()
    
    while True:
        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()
        
        if frame is None:
            time.sleep(0.05)
            continue
        
        # Encode as JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        
        # Frame rate control
        elapsed = time.time() - last_time
        if elapsed < interval:
            time.sleep(interval - elapsed)
        last_time = time.time()


# ================= ROUTES =================

@app.route('/')
def index():
    """Render main page (Remote Control Interface)"""
    return render_template('index.html')

@app.route('/api/viewer/state', methods=['GET'])
def get_viewer_state():
    """API endpoint for Pi viewer to poll current status"""
    current_state = get_server_state()

    # If a manual recording is active and not triggered by motion recipe
    if current_state == 'idle' and video_capture.is_recording():
        return jsonify({'state': 'recording'})

    return jsonify({
        'state': current_state,
        'is_active': automated_motion_active or motion_engine.is_running
    })

@app.route('/api/viewer/trigger_playback', methods=['POST'])
def trigger_playback():
    """Trigger playback of latest.mp4 on the remote viewer"""
    # Temporarily set state to playback to trigger the Pi
    set_server_state('playback')

    # Reset back to idle after 2 seconds (giving the Pi enough time to poll and start playing)
    def reset_idle():
        time.sleep(2)
        if get_server_state() == 'playback':
            set_server_state('idle')

    threading.Thread(target=reset_idle, daemon=True).start()

    return jsonify({'success': True, 'message': 'Playback triggered'})


@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """Start video recording"""
    try:
        filename = video_capture.start_recording()
        return jsonify({
            'success': True,
            'message': 'Recording started',
            'filename': filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """Stop video recording"""
    try:
        filename = video_capture.stop_recording()
        return jsonify({
            'success': True,
            'message': 'Recording stopped',
            'filename': filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/recording/status', methods=['GET'])
def recording_status():
    """Get recording status"""
    return jsonify({
        'is_recording': video_capture.is_recording(),
        'current_file': video_capture.current_filename
    })


@app.route('/api/ptz/move', methods=['POST'])
def ptz_move():
    """Move PTZ camera"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        direction = data.get('direction')
        speed = data.get('speed', 50)
        
        if not direction:
            return jsonify({
                'success': False,
                'message': 'Direction not specified'
            }), 400
        
        print(f"PTZ Move Request: direction={direction}, speed={speed}")
        
        result = ptz.move(direction, speed)
        
        return jsonify({
            'success': True,
            'message': f'Moving {direction}'
        })
        
    except Exception as e:
        print(f"PTZ move error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/ptz/stop', methods=['POST'])
def ptz_stop():
    """Stop PTZ movement"""
    try:
        print("PTZ Stop Request")
        result = ptz.stop()
        return jsonify({
            'success': True,
            'message': 'PTZ stopped'
        })
    except Exception as e:
        print(f"PTZ stop error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/ptz/zoom', methods=['POST'])
def ptz_zoom():
    """Control PTZ zoom"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
            
        direction = data.get('direction')  # 'in' or 'out'
        
        if not direction:
            return jsonify({
                'success': False,
                'message': 'Direction not specified'
            }), 400
        
        print(f"PTZ Zoom Request: direction={direction}")
        
        result = ptz.zoom(direction)
        
        return jsonify({
            'success': True,
            'message': f'Zooming {direction}'
        })
        
    except Exception as e:
        print(f"PTZ zoom error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/ptz/preset/goto', methods=['POST'])
def goto_preset():
    """Go to a preset position"""
    try:
        data = request.json
        preset_id = data.get('preset_id')

        if not preset_id:
            return jsonify({
                'success': False,
                'message': 'Preset ID not specified'
            }), 400

        ptz.goto_preset(preset_id)

        return jsonify({
            'success': True,
            'message': f'Moving to preset {preset_id}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500



@app.route('/api/ptz/preset/set', methods=['POST'])
def set_preset():
    """Set a preset position"""
    data = request.json
    preset_id = data.get('preset_id')
    
    try:
        ptz.set_preset(preset_id)
        return jsonify({
            'success': True,
            'message': f'Preset {preset_id} saved'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/recordings', methods=['GET'])
def list_recordings():
    """List all recordings"""
    try:
        recordings = []
        for filename in os.listdir(RECORDINGS_DIR):
            if filename.endswith('.avi') or filename.endswith('.mp4'):
                filepath = os.path.join(RECORDINGS_DIR, filename)
                recordings.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'created': os.path.getctime(filepath)
                })
        
        recordings.sort(key=lambda x: x['created'], reverse=True)
        return jsonify(recordings)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/recordings/<filename>')
def download_recording(filename):
    """Download a recording"""
    return send_from_directory(RECORDINGS_DIR, filename)


@app.route('/video_feed')
def video_feed():
    """Video streaming route using optimized threaded capture"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/motion/play', methods=['POST'])
def play_motion():
    try:
        motion_engine.run_recipe(sample_recipe)
        return jsonify({
            'success': True,
            'message': 'Motion recipe started'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/motion/status', methods=['GET'])
def motion_status():
    return jsonify({
        'is_active': automated_motion_active or motion_engine.is_running
    })

@app.route('/api/motion/record', methods=['POST'])
def record_motion():
    global automated_motion_active

    def _record_and_play():
        global automated_motion_active
        try:
            automated_motion_active = True
            set_server_state('recording')

            # Start recording
            video_capture.start_recording()

            # Since video_capture.start_recording() spins up a background thread that establishes
            # an RTSP connection, reads initial frames, and creates the file, we must wait
            # enough time for it to finish initializing before blasting the camera with PTZ commands.
            # Give it ample time to start writing frames successfully.
            time.sleep(3)

            # Start motion recipe and wait for it to finish
            motion_engine.run_recipe(sample_recipe)
            if motion_engine.thread and motion_engine.thread.is_alive():
                motion_engine.thread.join()

            time.sleep(1) # Record for one more second after finishing
            # Stop recording
            recorded_filename = video_capture.stop_recording()

            # Change state to processing
            set_server_state('processing')

            # Run final video processing with FFmpeg
            recorded_path = os.path.join(RECORDINGS_DIR, recorded_filename)
            video_processor.process_final_video(recorded_path, RECORDINGS_DIR)

            # Change state to playback so the Pi immediately plays the new video
            set_server_state('playback')

            # Reset back to idle after 2 seconds
            def reset_idle():
                time.sleep(2)
                if get_server_state() == 'playback':
                    set_server_state('idle')

            threading.Thread(target=reset_idle, daemon=True).start()

        except Exception as e:
            print(f"Error in record and play motion: {e}")
            set_server_state('idle')
            try:
                # Cleanup if recording is still active
                if video_capture.is_recording():
                    video_capture.stop_recording()
            except:
                pass
        finally:
            automated_motion_active = False

    try:
        if automated_motion_active or motion_engine.is_running:
            return jsonify({
                'success': False,
                'message': 'Motion sequence is already running'
            }), 400

        threading.Thread(target=_record_and_play, daemon=True).start()

        return jsonify({
            'success': True,
            'message': 'Started recording and playing motion recipe'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':
    print("🚀 PTZ Camera Web Server with Low-Latency Streaming")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)