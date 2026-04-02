"""
motion_publisher.py
Author: Kamal

This file simulates a PIR motion sensor on campus.
It generates random motion values and publishes them to the MQTT broker.
The message format is a simple string: "value;status;time_period"
Example: "82;DETECTED;after_hours"
"""

import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT settings
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "campus/security/motion"


class MotionSensor:
    """
    This class simulates a PIR motion sensor.
    It generates random values and checks if motion is detected.
    """

    def __init__(self, name, location):
        """Set up the sensor with a name and location."""
        self.name = name
        self.location = location
        self.threshold = 70  # values 70+ mean motion detected

    def is_after_hours(self):
        """Check if current time is between 10PM and 6AM."""
        hour = datetime.now().hour
        if hour >= 22 or hour < 6:
            return True
        return False

    def read(self):
        """
        Generate a fake motion reading.
        Returns a value between 0 and 100.
        At night the baseline is lower so any spike is more suspicious.
        """
        if self.is_after_hours():
            # Night: low baseline, but 15% chance of spike
            if random.randint(1, 100) <= 15:
                value = random.randint(70, 100)
            else:
                value = random.randint(0, 30)
        else:
            # Day: higher baseline with normal activity
            if random.randint(1, 100) <= 15:
                value = random.randint(70, 100)
            else:
                value = random.randint(10, 50)

        return value

    def get_status(self, value):
        """Decide if motion is detected based on the value."""
        if value >= self.threshold:
            return "DETECTED"
        else:
            return "clear"

    def get_time_period(self):
        """Return 'after_hours' or 'normal_hours' as a string."""
        if self.is_after_hours():
            return "after_hours"
        else:
            return "normal_hours"


# ---- MQTT callback ----

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print("Connection failed. Code: " + str(rc))


# ---- Main program ----

# Create the sensor object
sensor = MotionSensor("PIR-Corridor-A", "Block-A Corridor-1")

# Create MQTT client
client = mqtt.Client("kamal_motion_publisher")
client.on_connect = on_connect

# Connect to broker
print("Connecting to broker...")
client.connect(BROKER, PORT)
client.loop_start()
time.sleep(2)

# Start publishing
print("Motion publisher started. Sensor: " + sensor.name)
print("Location: " + sensor.location)
print("")

try:
    while True:
        # Read sensor value
        value = sensor.read()
        status = sensor.get_status(value)
        period = sensor.get_time_period()

        # Build message as simple string separated by semicolons
        # Format: "value;status;time_period"
        message = str(value) + ";" + status + ";" + period

        # Publish to broker
        client.publish(TOPIC, message)
        print("Sent: " + message)

        time.sleep(5)

except KeyboardInterrupt:
    print("")
    print("Motion publisher stopped.")
    client.loop_stop()
    client.disconnect()
