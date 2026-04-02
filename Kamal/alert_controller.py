"""
alert_controller.py
Author: Kamal

This file is the brain of the security system.
It subscribes to motion and door sensor topics.
It reads the data, decides the severity, and sends commands to the CCTV.

Severity levels:
  CRITICAL - motion detected after hours, or door open after hours
  WARNING  - motion detected during day, or door open too long
  OK       - no threats

Commands sent to CCTV:
  RECORD  - start recording (for CRITICAL)
  MONITOR - keep watching (for WARNING)
  IDLE    - do nothing (for OK)

Message format sent to CCTV: "command;severity;source"
Example: "RECORD;CRITICAL;motion"
"""

from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT settings
BROKER = "broker.hivemq.com"
PORT = 1883

# Topics we listen to
MOTION_TOPIC = "campus/security/motion"
DOOR_TOPIC = "campus/security/door"

# Topic we send commands to
CCTV_TOPIC = "campus/security/cctv"

# Thresholds
MOTION_THRESHOLD = 70
DOOR_OPEN_LIMIT = 30


class AlertController:
    """
    This class evaluates sensor data and decides what to do.
    """

    def __init__(self):
        """Set up the controller."""
        self.total_alerts = 0

    def evaluate_motion(self, value, status, period):
        """
        Decide what to do based on motion data.
        Returns a command and severity level.
        """
        if value >= MOTION_THRESHOLD and period == "after_hours":
            # Motion detected at night = very dangerous
            self.total_alerts = self.total_alerts + 1
            return "RECORD", "CRITICAL"

        elif value >= MOTION_THRESHOLD:
            # Motion detected during day = suspicious but not critical
            self.total_alerts = self.total_alerts + 1
            return "MONITOR", "WARNING"

        else:
            # No motion
            return "IDLE", "OK"

    def evaluate_door(self, state, duration, period):
        """
        Decide what to do based on door data.
        Returns a command and severity level.
        """
        if state == "OPEN" and period == "after_hours":
            # Door open at night = very dangerous
            self.total_alerts = self.total_alerts + 1
            return "RECORD", "CRITICAL"

        elif state == "OPEN" and duration > DOOR_OPEN_LIMIT:
            # Door open too long = suspicious
            self.total_alerts = self.total_alerts + 1
            return "MONITOR", "WARNING"

        elif state == "OPEN":
            # Door just opened during the day = normal
            return "IDLE", "OK"

        else:
            # Door is closed
            return "IDLE", "OK"


# Create the controller object
controller = AlertController()


# ---- MQTT callbacks ----

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(MOTION_TOPIC)
        client.subscribe(DOOR_TOPIC)
        print("Subscribed to: " + MOTION_TOPIC)
        print("Subscribed to: " + DOOR_TOPIC)
        print("")
        print("Waiting for sensor data...")
    else:
        print("Connection failed. Code: " + str(rc))


def on_message(client, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode()

    # ---- Motion data ----
    if topic == MOTION_TOPIC:
        # Message format: "value;status;time_period"
        parts = message.split(";")

        try:
            value = int(parts[0])
            status = parts[1]
            period = parts[2]
        except:
            print("Bad motion data: " + message)
            return

        # Evaluate
        command, severity = controller.evaluate_motion(value, status, period)

        print("Motion: " + str(value) + " (" + period + ") -> " + command + " [" + severity + "]")

        # Send command to CCTV
        # Format: "command;severity;source"
        cctv_message = command + ";" + severity + ";" + "motion"
        client.publish(CCTV_TOPIC, cctv_message)

    # ---- Door data ----
    if topic == DOOR_TOPIC:
        # Message format: "state;duration;time_period"
        parts = message.split(";")

        try:
            state = parts[0]
            duration = int(parts[1])
            period = parts[2]
        except:
            print("Bad door data: " + message)
            return

        # Evaluate
        command, severity = controller.evaluate_door(state, duration, period)

        print("Door: " + state + " (" + str(duration) + "s, " + period + ") -> " + command + " [" + severity + "]")

        # Send command to CCTV
        cctv_message = command + ";" + severity + ";" + "door"
        client.publish(CCTV_TOPIC, cctv_message)


# ---- Main program ----

client = mqtt.Client("kamal_alert_controller")
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker...")
client.connect(BROKER, PORT)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("")
    print("Alert controller stopped. Total alerts: " + str(controller.total_alerts))
    client.disconnect()
