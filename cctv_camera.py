# cctv_camera.py
# CCTVCamera class - simulates an IP security camera
# Can start and stop recording, logs events to a file
# Auto-stops recording after max duration
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

from datetime import datetime
from config import CCTV_RECORD_DURATION


class CCTVCamera:
    """Simulates an IP security camera with recording capability."""

    def __init__(self, name, location, resolution="1080p"):
        # Store camera identity
        self.name = name
        self.location = location
        self.sensor_type = "cctv"
        self.resolution = resolution
        # Recording state
        self.is_recording = False
        self.recording_start = None
        self.max_duration = CCTV_RECORD_DURATION
        self.log_file = "cctv_recordings.log"

    def get_status(self):
        """
        Get current camera status.
        Auto-stops recording if max duration exceeded.
        
        Returns a dictionary with camera state.
        """
        elapsed = 0
        if self.is_recording and self.recording_start is not None:
            diff = datetime.now() - self.recording_start
            elapsed = round(diff.total_seconds(), 1)

            # Auto-stop if exceeded max duration
            if elapsed >= self.max_duration:
                self.stop_recording()
                elapsed = 0

        return self.to_dict(elapsed)

    def to_dict(self, elapsed=0):
        """Convert current state to dictionary for JSON publishing."""
        return {
            "camera_name": self.name,
            "location": self.location,
            "type": self.sensor_type,
            "is_recording": self.is_recording,
            "elapsed_sec": elapsed,
            "resolution": self.resolution,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def start_recording(self, reason="motion_detected"):
        """
        Start recording. Logs the event to file.
        Does nothing if already recording.
        """
        if self.is_recording:
            return

        self.is_recording = True
        self.recording_start = datetime.now()

        # Log to file
        log_line = "[{}] RECORDING STARTED - Camera: {}, Reason: {}\n".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            self.name, reason)

        with open(self.log_file, "a") as f:
            f.write(log_line)

        print("  [CCTV] Recording started: {}".format(self.name))

    def stop_recording(self):
        """Stop recording. Logs duration to file."""
        if not self.is_recording:
            return

        elapsed = 0
        if self.recording_start is not None:
            diff = datetime.now() - self.recording_start
            elapsed = round(diff.total_seconds(), 1)

        self.is_recording = False
        self.recording_start = None

        # Log to file
        log_line = "[{}] RECORDING STOPPED - Camera: {}, Duration: {}s\n".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            self.name, elapsed)

        with open(self.log_file, "a") as f:
            f.write(log_line)

        print("  [CCTV] Recording stopped: {}".format(self.name))

    def __str__(self):
        state = "RECORDING" if self.is_recording else "IDLE"
        return "CCTVCamera({}, {}, {})".format(self.name, self.resolution, state)
