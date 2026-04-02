"""
door_publisher.py
Author: Kamal

This file simulates a magnetic contact sensor for doors.
It randomly opens and closes the door and tracks how long it stays open.
The message format is a simple string: "state;duration;time_period"
Example: "OPEN;45;after_hours"
"""

import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT settings
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "campus/security/door"

# How many seconds a door can stay open before it is a problem
DOOR_OPEN_LIMIT = 30


class DoorSensor:
    """
    This class simulates a door sensor.
    It tracks if the door is open or closed and for how long.
    """

    def __init__(self, name, location):
        """Set up the sensor."""
        self.name = name
        self.location = location
        self.is_open = False
        self.opened_at = None  # when the door was opened

    def is_after_hours(self):
        """Check if current time is between 10PM and 6AM."""
        hour = datetime.now().hour
        if hour >= 22 or hour < 6:
            return True
        return False

    def read(self):
        """
        Simulate a door reading.
        20% chance to toggle the state each cycle.
        Returns the state, how long it has been open, and the time period.
        """
        # 20% chance to toggle
        if random.randint(1, 10) <= 2:
            if self.is_open:
                # Close the door
                self.is_open = False
                self.opened_at = None
            else:
                # Open the door
                self.is_open = True
                self.opened_at = datetime.now()

        # Calculate how long the door has been open
        duration = 0
        if self.is_open and self.opened_at is not None:
            diff = datetime.now() - self.opened_at
            duration = int(diff.total_seconds())

        # Get state as string
        if self.is_open:
            state = "OPEN"
        else:
            state = "CLOSED"

        # Get time period
        if self.is_after_hours():
            period = "after_hours"
        else:
            period = "normal_hours"

        return state, duration, period


# ---- MQTT callback ----

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print("Connection failed. Code: " + str(rc))


# ---- Main program ----

# Create sensor object
sensor = DoorSensor("Door-Main-Entrance", "Block-A Ground Floor")

# Create MQTT client
client = mqtt.Client("kamal_door_publisher")
client.on_connect = on_connect

# Connect
print("Connecting to broker...")
client.connect(BROKER, PORT)
client.loop_start()
time.sleep(2)

# Start publishing
print("Door publisher started. Sensor: " + sensor.name)
print("Location: " + sensor.location)
print("")

try:
    while True:
        # Read sensor
        state, duration, period = sensor.read()

        # Build message: "state;duration;time_period"
        message = state + ";" + str(duration) + ";" + period

        # Publish
        client.publish(TOPIC, message)
        print("Sent: " + message)

        time.sleep(5)

except KeyboardInterrupt:
    print("")
    print("Door publisher stopped.")
    client.loop_stop()
    client.disconnect()
