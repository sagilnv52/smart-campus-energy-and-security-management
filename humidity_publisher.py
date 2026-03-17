import random
import time

import paho.mqtt.client as mqtt


BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "campus/room1/humidity"
CONTROLLER_STATUS_TOPIC = "campus/room1/status/hvac_controller"


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the client connects to the MQTT broker."""
    if reason_code == 0:
        print("Connected to MQTT broker")
        client.subscribe(CONTROLLER_STATUS_TOPIC)
        print("Waiting for HVAC controller to become ready...")
    else:
        print(f"Connection failed with code {reason_code}")


def on_message(client, userdata, msg):
    """Checks whether the HVAC controller is ready."""
    message = msg.payload.decode().strip()
    if msg.topic == CONTROLLER_STATUS_TOPIC and message == "READY":
        userdata["controller_ready"] = True
        print("HVAC controller is ready. Humidity publisher can start.")


def generate_humidity():
    """Simulate a humidity value as a percentage."""
    return round(random.uniform(30.0, 80.0), 2)


def publish_humidity(client):
    """Generate and publish a new humidity value every 5 seconds."""
    while True:
        humidity = generate_humidity()
        client.publish(TOPIC, str(humidity))
        print(f"Published humidity: {humidity} %")
        time.sleep(5)


def main():
    status = {"controller_ready": False}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=status)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while not status["controller_ready"]:
            time.sleep(1)

        publish_humidity(client)
    except KeyboardInterrupt:
        print("\nHumidity publisher stopped")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
