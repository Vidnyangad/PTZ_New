"""
PTZ Controller Module
Handles Pan-Tilt-Zoom camera control using ONVIF ContinuousMove protocol
"""
from onvif import ONVIFCamera


class PTZController:
    """
    PTZ Camera Controller using ONVIF ContinuousMove
    Based on working code that successfully controls Active Pixel PTZ cameras
    """
    
    def __init__(self, camera_ip, username, password, protocol='onvif', port=8899, camera_address=1):
        """
        Initialize PTZ Controller with ONVIF
        
        Args:
            camera_ip: IP address of the camera
            username: Camera username
            password: Camera password
            protocol: Protocol (always 'onvif' for this controller)
            port: ONVIF port (default: 8899)
            camera_address: Not used for ONVIF, kept for compatibility
        """
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.port = port
        
        print(f"Connecting to ONVIF camera at {camera_ip}:{port}...")
        
        try:
            # Initialize ONVIF camera
            self.cam = ONVIFCamera(camera_ip, port, username, password)
            
            # Create media and PTZ services
            self.media = self.cam.create_media_service()
            self.ptz = self.cam.create_ptz_service()
            
            # Get the first profile token
            profiles = self.media.GetProfiles()
            if not profiles:
                raise Exception("No media profiles found on camera")
            
            self.token = profiles[0].token
            
            print(f"✓ ONVIF PTZ controller initialized")
            print(f"  Profile token: {self.token}")
            
        except Exception as e:
            print(f"✗ ONVIF initialization failed: {e}")
            raise Exception(f"Failed to initialize ONVIF: {e}")
    
    def move(self, direction, speed=50):
        """
        Move camera in specified direction using ONVIF ContinuousMove
        
        Args:
            direction: Direction to move ('up', 'down', 'left', 'right', 
                      'up_left', 'up_right', 'down_left', 'down_right')
            speed: Movement speed (0-100), converted to ONVIF velocity (-1.0 to 1.0)
        """
        # Convert speed (0-100) to velocity (0.0-1.0)
        velocity = speed / 100.0
        velocity = max(min(velocity, 1.0), 0.0)
        
        # Direction to velocity mapping
        direction_map = {
            'right':      {'pan':  velocity, 'tilt': 0.0},
            'left':       {'pan': -velocity, 'tilt': 0.0},
            'up':         {'pan': 0.0, 'tilt':  velocity},
            'down':       {'pan': 0.0, 'tilt': -velocity},
            'up_right':   {'pan':  velocity, 'tilt':  velocity},
            'up_left':    {'pan': -velocity, 'tilt':  velocity},
            'down_right': {'pan':  velocity, 'tilt': -velocity},
            'down_left':  {'pan': -velocity, 'tilt': -velocity},
        }
        
        if direction not in direction_map:
            raise ValueError(f"Invalid direction: {direction}")
        
        vel = direction_map[direction]
        
        try:
            # Send continuous move command with short timeout for quick response
            self.ptz.ContinuousMove({
                'ProfileToken': self.token,
                'Velocity': {
                    'PanTilt': {'x': vel['pan'], 'y': vel['tilt']},
                    'Zoom': {'x': 0.0}
                },
                'Timeout': 'PT0.5S'  # 0.5 second timeout for quick response
            })
            
            return True
            
        except Exception as e:
            print(f"✗ ONVIF move error: {e}")
            # Don't raise exception to avoid blocking UI
            return False
    
    def stop(self):
        """Stop all PTZ movement using ONVIF"""
        try:
            self.ptz.Stop({
                'ProfileToken': self.token,
                'PanTilt': True,
                'Zoom': True
            })
            return True
        except:
            # Silently fail - camera may auto-stop
            return True
    
    def zoom(self, direction, speed=50):
        """
        Control camera zoom using ONVIF
        
        Args:
            direction: 'in' or 'out'
            speed: Zoom speed (0-100)
        """
        # Convert speed to velocity
        velocity = speed / 100.0
        MAX_ZOOM_SPEED = 0.5
        velocity = min(velocity, MAX_ZOOM_SPEED)
        
        zoom_velocity = velocity if direction == 'in' else -velocity
        
        print(f"ONVIF Zoom: {direction} at speed {speed}")
        
        try:
            self.ptz.ContinuousMove({
                'ProfileToken': self.token,
                'Velocity': {
                    'PanTilt': {'x': 0.0, 'y': 0.0},
                    'Zoom': {'x': zoom_velocity}
                }
            })
            
            print("✓ Zoom command sent")
            return True
            
        except Exception as e:
            print(f"✗ Zoom error: {e}")
            raise Exception(f"Failed to zoom: {e}")
    
    def goto_preset(self, preset_id):
        """
        Move camera to a preset position using ONVIF
        Speed control removed — camera uses internal preset speed.
        """
        print(f"ONVIF Goto Preset: {preset_id}")

        try:
            self.ptz.GotoPreset({
                'ProfileToken': self.token,
                'PresetToken': str(preset_id)
            })

            print(f"✓ Moving to preset {preset_id}")
            return True

        except Exception as e:
            print(f"✗ Goto preset error: {e}")
            raise Exception(f"Failed to go to preset: {e}")

    
    def set_preset(self, preset_id):
        """
        Save current position as a preset using ONVIF
        
        Args:
            preset_id: Preset position ID (1-255)
        """
        print(f"ONVIF Set Preset: {preset_id}")
        
        try:
            self.ptz.SetPreset({
                'ProfileToken': self.token,
                'PresetToken': str(preset_id),
                'PresetName': f'Preset_{preset_id}'
            })
            
            print(f"✓ Preset {preset_id} saved")
            return True
            
        except Exception as e:
            print(f"✗ Set preset error: {e}")
            raise Exception(f"Failed to set preset: {e}")
    
    def get_status(self):
        """Get current PTZ status using ONVIF"""
        try:
            status = self.ptz.GetStatus({'ProfileToken': self.token})
            return {
                'pan': status.Position.PanTilt.x if status.Position else 0,
                'tilt': status.Position.PanTilt.y if status.Position else 0,
                'zoom': status.Position.Zoom.x if status.Position and status.Position.Zoom else 0
            }
        except Exception as e:
            print(f"Get status error: {e}")
            return {}
        
    def move_vector(self, pan, tilt):
        request = self.ptz.create_type('ContinuousMove')
        request.ProfileToken = self.token

        request.Velocity = {
            'PanTilt': {
                'x': pan,
                'y': tilt
            },
            'Zoom': {'x': 0.0}
        }

        print("Sending vector to camera:", pan, tilt)
        self.ptz.ContinuousMove(request)
