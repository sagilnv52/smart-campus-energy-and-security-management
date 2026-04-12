

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime


BROKER = "broker.hivemq.com"
PORT = 1883


TOPIC_ENERGY = "campus/energy/data"
TOPIC_MOTION = "campus/energy/motion"


DEVICES = {
    "lab1_computer":  {"location": "lab1",    "base_w": 150, "variance": 50},
    "lab1_printer":   {"location": "lab1",    "base_w": 30,  "variance": 20},
    "lab2_projector": {"location": "lab2",    "base_w": 250, "variance": 30},
    "library_lights": {"location": "library", "base_w": 200, "variance": 40},
    "server_room_ac": {"location": "server",  "base_w": 800, "variance": 100},
}


def ts():
    return datetime.now().strftime("%H:%M:%S")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{ts()}] Publisher connected to broker")
    else:
        print(f"[{ts()}] Connection failed: {rc}")


def read_smart_plug(device_id, profile):
    """Simulate smart plug reading (real system: API call to TP-Link/Shelly)."""
    power = round(profile["base_w"] + random.uniform(-profile["variance"], profile["variance"]), 2)
    voltage = round(220 + random.uniform(-5, 5), 1)
    return {
        "device_id":  device_id,
        "location":   profile["location"],
        "power_w":    power,
        "voltage_v":  voltage,
        "current_a":  round(power / voltage, 3),
        "energy_kwh": round(power / 1000, 4),
        "status":     "ON",
        "timestamp":  datetime.now().isoformat()
    }


def read_motion_sensor(location):
    """Simulate PIR motion sensor (real system: GPIO or Zigbee sensor)."""
    hour = datetime.now().hour
    
    if hour >= 22 or hour < 6:
        motion = random.random() < 0.1
    else:
        motion = random.random() < 0.8

    return {
        "location":        location,
        "motion_detected": motion,
        "timestamp":       datetime.now().isoformat()
    }


def main():
    client = mqtt.Client("energy_publisher")
    client.on_connect = on_connect
    client.connect(BROKER, PORT)
    client.loop_start()

    print(f"[{ts()}] Publisher started. Sending data every 5 seconds...\n")

    try:
        while True:
            locations_sent = set()

            for device_id, profile in DEVICES.items():
                
                energy = read_smart_plug(device_id, profile)
                client.publish(TOPIC_ENERGY, json.dumps(energy), qos=1)
                print(f"[{ts()}] PUB energy | {device_id}: {energy['power_w']}W")

                
                loc = profile["location"]
                if loc not in locations_sent:
                    motion = read_motion_sensor(loc)
                    client.publish(TOPIC_MOTION, json.dumps(motion), qos=1)
                    status = "MOTION" if motion["motion_detected"] else "no motion"
                    print(f"[{ts()}] PUB motion | {loc}: {status}")
                    locations_sent.add(loc)

            print(f"[{ts()}] --- cycle done ---\n")
            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\n[{ts()}] Publisher stopped.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
