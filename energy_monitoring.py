import paho.mqtt.client as mqtt
import json
from datetime import datetime


BROKER = "broker.hivemq.com"
PORT = 1883


TOPIC_ENERGY = "campus/energy/data"
TOPIC_MOTION = "campus/energy/motion"


TOPIC_ALERTS   = "campus/energy/alerts"
TOPIC_SECURITY = "campus/security/alerts"
TOPIC_COMMANDS = "campus/energy/commands"


HIGH_POWER_THRESHOLD = 500      
DEVICE_LEFT_ON_THRESHOLD = 50   
AFTER_HOURS_START = 22          
AFTER_HOURS_END = 6             


latest_motion = {}    
energy_log = []       
total_alerts = 0


def ts():
    return datetime.now().strftime("%H:%M:%S")


def is_after_hours():
    hour = datetime.now().hour
    return hour >= AFTER_HOURS_START or hour < AFTER_HOURS_END


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{ts()}] Energy Monitor connected to broker")
        client.subscribe(TOPIC_ENERGY, qos=1)
        client.subscribe(TOPIC_MOTION, qos=1)
        print(f"[{ts()}] Subscribed to: {TOPIC_ENERGY}")
        print(f"[{ts()}] Subscribed to: {TOPIC_MOTION}")
        print(f"[{ts()}] Monitoring started...\n")
    else:
        print(f"[{ts()}] Connection failed: {rc}")


def on_message(client, userdata, msg):
    global total_alerts

    try:
        data = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        return

    if msg.topic == TOPIC_MOTION:
        location = data["location"]
        latest_motion[location] = data["motion_detected"]
        return

    
    if msg.topic == TOPIC_ENERGY:
        device = data["device_id"]
        power = data["power_w"]
        location = data.get("location", "unknown")
        motion = latest_motion.get(location, True)  

        
        energy_log.append(data)
        if len(energy_log) > 100:
            energy_log.pop(0)

        
        if is_after_hours() and power > HIGH_POWER_THRESHOLD:
            alert = {
                "type":     "HIGH_POWER_AFTER_HOURS",
                "severity": "CRITICAL",
                "device":   device,
                "location": location,
                "power_w":  power,
                "message":  f"{device} consuming {power}W after hours!",
                "timestamp": datetime.now().isoformat()
            }
            client.publish(TOPIC_ALERTS, json.dumps(alert), qos=1)
            client.publish(TOPIC_SECURITY, json.dumps(alert), qos=1)
            total_alerts += 1
            print(f"[{ts()}] CRITICAL | {alert['message']}")
            print(f"[{ts()}]   -> Alert sent to security (Kamal)")

            
            cmd = {"device_id": device, "action": "OFF", "reason": "High power after hours"}
            client.publish(TOPIC_COMMANDS, json.dumps(cmd), qos=1)
            print(f"[{ts()}]   -> Auto command: turn OFF {device}")

        
        elif power > DEVICE_LEFT_ON_THRESHOLD and not motion:
            alert = {
                "type":     "DEVICE_LEFT_ON",
                "severity": "WARNING",
                "device":   device,
                "location": location,
                "power_w":  power,
                "message":  f"{device} is ON ({power}W) but no one in {location}",
                "timestamp": datetime.now().isoformat()
            }
            client.publish(TOPIC_ALERTS, json.dumps(alert), qos=1)
            total_alerts += 1
            print(f"[{ts()}] WARNING | {alert['message']}")

        
        elif power > HIGH_POWER_THRESHOLD * 2:
            alert = {
                "type":     "POWER_SPIKE",
                "severity": "CRITICAL",
                "device":   device,
                "location": location,
                "power_w":  power,
                "message":  f"{device} power spike detected: {power}W!",
                "timestamp": datetime.now().isoformat()
            }
            client.publish(TOPIC_ALERTS, json.dumps(alert), qos=1)
            client.publish(TOPIC_SECURITY, json.dumps(alert), qos=1)
            total_alerts += 1
            print(f"[{ts()}] CRITICAL | {alert['message']}")

        
        else:
            motion_str = "occupied" if motion else "empty"
            print(f"[{ts()}] OK | {device}: {power}W ({location} {motion_str})")


def main():
    client = mqtt.Client("energy_monitor")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Monitor stopped. Total alerts: {total_alerts}")
        client.disconnect()


if __name__ == "__main__":
    main()
