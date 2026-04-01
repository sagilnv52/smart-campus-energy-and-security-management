# security_subscriber.py
# Pair 4: Command subscriber - listens for commands and executes them
# Uses loop_start/loop_stop pattern from class (Subscriber_AlertSystem.py)
#
# Supported commands (JSON on smartcampus/security/command):
#   {"action": "arm_system"}
#   {"action": "disarm_system"}
#   {"action": "start_recording", "target": "CCTV-Entrance-North"}
#   {"action": "stop_recording", "target": "CCTV-Entrance-North"}
#   {"action": "lock_door", "target": "Door-Main-Entrance"}
#   {"action": "status"}
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

import paho.mqtt.client as mqtt
import json
from datetime import datetime

from config import BROKER_ADDRESS, PORT, CLIENT_SUBSCRIBER
from config import TOPIC_SECURITY_CMD, TOPIC_SECURITY_LOG
from cctv_camera import CCTVCamera
from door_window_sensor import DoorWindowSensor

# Create device objects that the subscriber can control
cctv_entrance = CCTVCamera("CCTV-Entrance-North", "Block-A Main Entrance")
cctv_lab = CCTVCamera("CCTV-Lab-B", "Block-B Lab-201")
door_main = DoorWindowSensor("Door-Main-Entrance", "Block-A Ground Floor", "door")
window_lab = DoorWindowSensor("Window-Lab-B", "Block-B Lab-201", "window")

# Quick lookup by name
cameras = {"CCTV-Entrance-North": cctv_entrance, "CCTV-Lab-B": cctv_lab}
doors = {"Door-Main-Entrance": door_main, "Window-Lab-B": window_lab}


# ---- MQTT Callbacks ----

def on_connect(client, userdata, flags, rc):
    """Subscribe to command topic on successful connection."""
    if rc == 0:
        print("Subscriber connected successfully! Code:", rc)
        client.subscribe(TOPIC_SECURITY_CMD)
        print("Subscribed to:", TOPIC_SECURITY_CMD)
    else:
        print("Bad connection. Code:", rc)


def on_message(client, userdata, msg):
    """Process incoming command messages."""
    try:
        # Decode JSON (same approach as class examples)
        data = json.loads(msg.payload.decode("utf8"))
        print("\n[COMMAND RECEIVED]", data)

        action = data.get("action", "")
        target = data.get("target", "")

        if action == "arm_system":
            print("  -> System ARMED. All sensors activated.")
            send_ack(client, "System ARMED - all sensors active.")

        elif action == "disarm_system":
            # Stop all cameras when disarming
            for cam in cameras.values():
                cam.stop_recording()
            print("  -> System DISARMED.")
            send_ack(client, "System DISARMED - all sensors off.")

        elif action == "start_recording":
            if target in cameras:
                cameras[target].start_recording("manual_command")
                send_ack(client, "Recording started: " + target)
            else:
                print("  -> Unknown camera:", target)
                send_ack(client, "Unknown camera: " + target)

        elif action == "stop_recording":
            if target in cameras:
                cameras[target].stop_recording()
                send_ack(client, "Recording stopped: " + target)
            else:
                send_ack(client, "Unknown camera: " + target)

        elif action == "lock_door":
            if target in doors:
                doors[target].force_lock()
                send_ack(client, "Locked: " + target)
            else:
                send_ack(client, "Unknown door: " + target)

        elif action == "unlock_door":
            if target in doors:
                doors[target].force_unlock()
                send_ack(client, "Unlocked: " + target)
            else:
                send_ack(client, "Unknown door: " + target)

        elif action == "status":
            print("  -> Status: system running.")
            send_ack(client, "System running. All devices operational.")

        else:
            print("  -> Unknown action:", action)
            send_ack(client, "Unknown action: " + action)

    except Exception as e:
        print("Error processing message:", e)


def send_ack(client, message):
    """Send acknowledgement to the security log topic."""
    ack = {
        "type": "command_ack",
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    client.publish(TOPIC_SECURITY_LOG, json.dumps(ack))


# ---- Main ----

def main():
    # Pair 4: subscriber client
    client = mqtt.Client(CLIENT_SUBSCRIBER)
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to broker
    try:
        client.connect(BROKER_ADDRESS, PORT)
    except:
        print("Connection to broker failed.")
        return

    # Start loop (same pattern as Subscriber_AlertSystem.py from class)
    client.loop_start()

    # Keep running until Ctrl+C
    try:
        while True:
            pass  # Wait for messages
    except KeyboardInterrupt:
        print("\nShutting down subscriber...")

    client.disconnect()
    client.loop_stop()
    print("Subscriber disconnected.")


if __name__ == "__main__":
    main()
