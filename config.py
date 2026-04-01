# config.py
# Settings for the Smart Campus Security System
# All connection parameters, topics and thresholds are here
# Changing the broker or a threshold only requires editing this file
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

# ---- MQTT Broker ----
BROKER_ADDRESS = "broker.hivemq.com"
PORT = 1883

# ---- MQTT Topics ----
# Each sensor type publishes on its own topic
# Pattern: smartcampus/security/<device>/<action>
TOPIC_MOTION = "smartcampus/security/motion/alert"
TOPIC_DOOR_WINDOW = "smartcampus/security/door_window/alert"
TOPIC_CCTV = "smartcampus/security/cctv/trigger"
TOPIC_SECURITY_CMD = "smartcampus/security/command"
TOPIC_SECURITY_LOG = "smartcampus/security/log"

# Topics from other team members (cross-system integration)
TOPIC_ENERGY = "smartcampus/energy/usage"
TOPIC_ENVIRONMENT = "smartcampus/environment/data"

# ---- Client IDs ----
# Each sensor type gets its own MQTT client = separate broker connection
# This creates 4 client-broker pairs (required for 80%+ grade)
#   Pair 1: motion publisher
#   Pair 2: door/window publisher
#   Pair 3: cctv publisher
#   Pair 4: command subscriber
CLIENT_MOTION_PUB = "kamal_motion_publisher"
CLIENT_DOOR_PUB = "kamal_door_publisher"
CLIENT_CCTV_PUB = "kamal_cctv_publisher"
CLIENT_SUBSCRIBER = "kamal_security_subscriber"

# ---- Security thresholds ----
MOTION_THRESHOLD = 0.7        # confidence 0.0 to 1.0
DOOR_OPEN_LIMIT = 30          # seconds before warning
CCTV_RECORD_DURATION = 120    # seconds per clip

# ---- After hours ----
AFTER_HOURS_START = 22  # 10 PM
AFTER_HOURS_END = 6     # 6 AM

# ---- Timing ----
SENSOR_INTERVAL = 5  # seconds between sensor readings
