#!/usr/bin/env python3
"""
Camera Connection Test Script
Run this to verify your camera settings before starting the main application
"""

from video_capture import VideoCapture
from ptz_controller import PTZController
import sys

# Camera configuration
CAMERA_IP = "192.168.1.11"
CAMERA_USER = "admin"
CAMERA_PASSWORD = "admin"
RECORDINGS_DIR = "recordings"

def test_video_stream():
    """Test video stream connection"""
    print("\n" + "="*60)
    print("Testing Video Stream Connection")
    print("="*60)
    
    video = VideoCapture(CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD, RECORDINGS_DIR)
    
    result = video.test_connection()
    
    if result['success']:
        print("✓ SUCCESS: Connected to camera")
        print(f"  Resolution: {result['resolution']}")
        print(f"  FPS: {result['fps']}")
        
        # Try to save a test snapshot
        try:
            snapshot_path = video.save_snapshot("test_snapshot.jpg")
            print(f"✓ Test snapshot saved: {snapshot_path}")
        except Exception as e:
            print(f"✗ Could not save snapshot: {e}")
            
        return True
    else:
        print(f"✗ FAILED: {result['message']}")
        print("\nTroubleshooting steps:")
        print("1. Verify camera IP address is correct")
        print("2. Check username and password")
        print("3. Ensure camera is powered on and network connected")
        print("4. Try accessing camera web interface in browser")
        print(f"   http://{CAMERA_IP}")
        print("5. Check if RTSP streaming is enabled in camera settings")
        print("\nCommon RTSP URLs to try:")
        for url in video.stream_urls:
            print(f"   {url}")
        
        return False

def test_ptz_control():
    """Test PTZ control"""
    print("\n" + "="*60)
    print("Testing PTZ Control")
    print("="*60)
    
    ptz = PTZController(CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD)
    
    try:
        # Try to get camera status
        status = ptz.get_status()
        print("✓ PTZ controller initialized")
        
        # Test a small movement
        print("Testing camera movement (right for 1 second)...")
        ptz.move('right', 30)
        import time
        time.sleep(1)
        ptz.stop()
        print("✓ PTZ movement test completed")
        
        return True
        
    except Exception as e:
        print(f"✗ PTZ control error: {e}")
        print("\nNote: PTZ control may fail if:")
        print("1. Camera doesn't support PTZ")
        print("2. PTZ API endpoints are different for your camera model")
        print("3. You need to configure ONVIF instead of HTTP API")
        print("\nCheck your camera's documentation for:")
        print("- PTZ CGI command format")
        print("- ONVIF support")
        
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "PTZ CAMERA TEST UTILITY" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    
    print(f"\nCamera IP: {CAMERA_IP}")
    print(f"Username: {CAMERA_USER}")
    print(f"Password: {'*' * len(CAMERA_PASSWORD)}")
    
    # Test video stream
    video_ok = test_video_stream()
    
    # Test PTZ control
    ptz_ok = test_ptz_control()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Video Stream: {'✓ PASS' if video_ok else '✗ FAIL'}")
    print(f"PTZ Control:  {'✓ PASS' if ptz_ok else '✗ FAIL'}")
    
    if video_ok and ptz_ok:
        print("\n✓ All tests passed! You can run the main application:")
        print("  python app.py")
    elif video_ok:
        print("\n⚠ Video stream works but PTZ control failed.")
        print("  You can still record videos, but PTZ may need configuration.")
        print("  Check README.md for PTZ configuration help.")
    else:
        print("\n✗ Video stream connection failed.")
        print("  Please fix camera connection before running the application.")
        print("  See troubleshooting steps above.")
    
    print("\n")
    
    return 0 if (video_ok and ptz_ok) else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
