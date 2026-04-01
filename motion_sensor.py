# motion_sensor.py
# MotionSensor class - simulates a PIR motion detector
# Uses OOP: class with __init__, read() and to_dict() methods
# In a real system read() would get data from GPIO pins
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

import random
from datetime import datetime
from config import MOTION_THRESHOLD, AFTER_HOURS_START, AFTER_HOURS_END


class MotionSensor:
    """Simulates a PIR motion sensor on campus."""

    def __init__(self, name, location):
        # Store sensor identity
        self.name = name
        self.location = location
        self.sensor_type = "motion"
        self.threshold = MOTION_THRESHOLD
        # Last reading stored here
        self.last_value = 0.0
        self.last_detected = False

    def is_after_hours(self):
        """Check if current time is within restricted hours (10PM-6AM)."""
        hour = datetime.now().hour
        if hour >= AFTER_HOURS_START or hour < AFTER_HOURS_END:
            return True
        return False

    def read(self):
        """
        Take a reading from the sensor.
        
        Daytime baseline is ~0.3 (normal activity on campus).
        Nighttime baseline is ~0.1, so any spike stands out.
        15% chance of strong motion each cycle.
        
        Returns a dictionary with all the reading data.
        """
        # Set baseline by time of day
        if self.is_after_hours():
            baseline = 0.1
        else:
            baseline = 0.3

        # Generate reading - 15% chance of strong motion
        if random.random() < 0.15:
            self.last_value = round(random.uniform(0.7, 1.0), 2)
        else:
            self.last_value = round(random.uniform(baseline - 0.05, baseline + 0.15), 2)

        # Clamp between 0 and 1
        if self.last_value < 0:
            self.last_value = 0.0
        if self.last_value > 1:
            self.last_value = 1.0

        # Is motion detected?
        self.last_detected = self.last_value >= self.threshold

        return self.to_dict()

    def to_dict(self):
        """Convert current state to a dictionary for JSON publishing."""
        return {
            "sensor_name": self.name,
            "location": self.location,
            "type": self.sensor_type,
            "value": self.last_value,
            "detected": self.last_detected,
            "after_hours": self.is_after_hours(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def __str__(self):
        """Print-friendly representation of the sensor."""
        status = "ACTIVE"
        return "MotionSensor({}, {}, {})".format(self.name, self.location, status)
