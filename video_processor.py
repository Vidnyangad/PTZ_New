import subprocess
import os
import cv2

def process_final_video(recorded_video_path, recordings_dir):
    """
    Applies a 1-second fade out to the recorded video, appends a montage video,
    replaces the audio track with a custom MP3, and saves the final result.

    Args:
        recorded_video_path (str): The path to the freshly recorded video file.
        recordings_dir (str): The base directory for recordings (C:\\SavedPTZVideos).
    """
    montage_path = os.path.join(recordings_dir, "montage.mp4")
    audio_path = os.path.join(recordings_dir, "audio.mp3")
    output_path = os.path.join(recordings_dir, "latest.mp4")

    # Verify input files exist
    if not os.path.exists(recorded_video_path):
        print(f"Error: Recorded video not found at {recorded_video_path}")
        return False

    if not os.path.exists(montage_path):
        print(f"Error: Montage video not found at {montage_path}. Cannot process final video.")
        return False

    if not os.path.exists(audio_path):
        print(f"Error: Audio track not found at {audio_path}. Cannot process final video.")
        return False

    print("Processing final video montage...")

    # We need to know the duration of the recorded video to know when to start the fade-out.
    # We can use OpenCV to get the frame count and FPS.
    cap = cv2.VideoCapture(recorded_video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()

    if fps == 0 or frame_count == 0:
        print("Error: Could not determine video duration for fade out.")
        return False

    duration_seconds = frame_count / fps
    fade_duration = 1.0
    fade_start = duration_seconds - fade_duration

    if fade_start < 0:
        fade_start = 0

    # FFmpeg command breakdown:
    # -i {recorded} -i {montage} -i {audio}: Inputs 0, 1, and 2
    # [0:v]fade=t=out:st={fade_start}:d={fade_duration}[v0]: Apply fade out to the first video
    # [v0][1:v]concat=n=2:v=1:a=0[vout]: Concatenate the faded video and montage
    # -map "[vout]" -map 2:a: Map the concatenated video and the audio file
    # -shortest: Stop encoding when the shortest stream ends (usually the audio or video)
    # -c:v libx264 -c:a aac: Re-encode using standard codecs for high compatibility
    # -y: Overwrite output file

    filter_complex = (
        f"[0:v]fade=t=out:st={fade_start}:d={fade_duration}[v0];"
        f"[v0][1:v]concat=n=2:v=1:a=0[vout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", recorded_video_path,
        "-i", montage_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",  # Significantly speeds up software encoding on Raspberry Pi
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ]

    try:
        print(f"Running FFmpeg: {' '.join(cmd)}")
        # We use subprocess.run but pipe output to DEVNULL to avoid OS pipe buffer deadlocks,
        # which commonly cause FFmpeg to hang indefinitely on Raspberry Pi/Linux.
        process = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

        if process.returncode != 0:
            print("FFmpeg failed with error:")
            print(process.stderr)
            return False

        print(f"Successfully processed video. Saved to {output_path}")
        return True
    except FileNotFoundError:
        print("Error: FFmpeg is not installed or not in the system PATH. Please install FFmpeg (https://ffmpeg.org/download.html) and try again.")
        return False
    except Exception as e:
        print(f"Unexpected error running FFmpeg: {e}")
        return False
