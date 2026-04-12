

import paho.mqtt.client as mqtt
import json
from datetime import datetime


BROKER = "broker.hivemq.com"
PORT = 1883


TOPIC_COMMANDS = "campus/energy/commands"
TOPIC_ALERTS   = "campus/energy/alerts"


device_states = {}
alert_history = []


def ts():
    return datetime.now().strftime("%H:%M:%S")


def control_device(device_id, action):
    
    previous = device_states.get(device_id, "UNKNOWN")
    device_states[device_id] = action

    if action == "OFF":
        print(f"[{ts()}]   -> Smart plug OFF for {device_id}")
        print(f"[{ts()}]   -> State changed: {previous} -> OFF")
    elif action == "ON":
        print(f"[{ts()}]   -> Smart plug ON for {device_id}")
        print(f"[{ts()}]   -> State changed: {previous} -> ON")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{ts()}] Subscriber connected to broker")
        client.subscribe(TOPIC_COMMANDS, qos=1)
        client.subscribe(TOPIC_ALERTS, qos=1)
        print(f"[{ts()}] Subscribed to: {TOPIC_COMMANDS}")
        print(f"[{ts()}] Subscribed to: {TOPIC_ALERTS}")
        print(f"[{ts()}] Waiting for commands and alerts...\n")
    else:
        print(f"[{ts()}] Connection failed: {rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        return

    if msg.topic == TOPIC_COMMANDS:
        device_id = data.get("device_id", "unknown")
        action = data.get("action", "unknown")
        reason = data.get("reason", "manual")

        print(f"\n[{ts()}] COMMAND RECEIVED:")
        print(f"[{ts()}]   Device: {device_id}")
        print(f"[{ts()}]   Action: {action}")
        print(f"[{ts()}]   Reason: {reason}")

        control_device(device_id, action)

       
        confirm = {
            "device_id": device_id,
            "action":    action,
            "success":   True,
            "timestamp": datetime.now().isoformat()
        }
        client.publish("campus/energy/confirmations", json.dumps(confirm), qos=1)
        print(f"[{ts()}]   -> Confirmation sent\n")

    
    elif msg.topic == TOPIC_ALERTS:
        alert_history.append(data)
        severity = data.get("severity", "?")
        message = data.get("message", "Unknown alert")
        print(f"[{ts()}] ALERT [{severity}]: {message}")


def main():
    client = mqtt.Client("energy_subscriber")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Subscriber stopped.")
        print(f"[{ts()}] Device states: {json.dumps(device_states, indent=2)}")
        print(f"[{ts()}] Total alerts received: {len(alert_history)}")
        client.disconnect()


if __name__ == "__main__":
    main()
