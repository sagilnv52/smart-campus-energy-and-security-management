# door_window_sensor.py
# DoorWindowSensor class - simulates a magnetic reed switch
# Detects open/close state and tracks how long a door stays open
# Includes force_lock() and force_unlock() for remote control
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

import random
from datetime import datetime
from config import DOOR_OPEN_LIMIT, AFTER_HOURS_START, AFTER_HOURS_END


class DoorWindowSensor:
    """Simulates a magnetic contact sensor for doors and windows."""

    def __init__(self, name, location, entry_type="door"):
        # Store sensor identity
        self.name = name
        self.location = location
        self.sensor_type = "door_window"
        self.entry_type = entry_type  # "door" or "window"
        # State tracking
        self.is_open = False
        self.opened_at = None  # datetime when it was opened
        self.max_open_seconds = DOOR_OPEN_LIMIT

    def is_after_hours(self):
        """Check if current time is within restricted hours."""
        hour = datetime.now().hour
        if hour >= AFTER_HOURS_START or hour < AFTER_HOURS_END:
            return True
        return False

    def read(self):
        """
        Simulate a sensor reading.
        
        Each call has a 20% chance to toggle the state.
        Tracks how long the door/window has been open.
        Flags a violation if open longer than the limit.
        
        Returns a dictionary with all the reading data.
        """
        # 20% chance to toggle open/close
        if random.random() < 0.20:
            if self.is_open:
                self.is_open = False
                self.opened_at = None
            else:
                self.is_open = True
                self.opened_at = datetime.now()

        # Calculate open duration
        open_duration = 0
        if self.is_open and self.opened_at is not None:
            diff = datetime.now() - self.opened_at
            open_duration = round(diff.total_seconds(), 1)

        # Check if duration exceeds limit
        violation = open_duration > self.max_open_seconds

        return self.to_dict(open_duration, violation)

    def to_dict(self, open_duration=0, violation=False):
        """Convert current state to a dictionary for JSON publishing."""
        return {
            "sensor_name": self.name,
            "location": self.location,
            "type": self.sensor_type,
            "entry_type": self.entry_type,
            "is_open": self.is_open,
            "open_duration_sec": open_duration,
            "violation": violation,
            "after_hours": self.is_after_hours(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def force_lock(self):
        """Remotely lock the door/window (close it)."""
        self.is_open = False
        self.opened_at = None
        print("  [LOCK] {} locked remotely.".format(self.name))

    def force_unlock(self):
        """Remotely unlock the door/window (open it)."""
        self.is_open = True
        self.opened_at = datetime.now()
        print("  [UNLOCK] {} unlocked remotely.".format(self.name))

    def __str__(self):
        state = "OPEN" if self.is_open else "CLOSED"
        return "DoorWindowSensor({}, {}, {})".format(self.name, self.entry_type, state)
