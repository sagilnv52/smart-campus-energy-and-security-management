import paho.mqtt.client as mqtt


BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "campus/room1/hvac"
STATUS_TOPIC = "campus/room1/status/hvac_subscriber"


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the client connects to the MQTT broker."""
    if reason_code == 0:
        print("Connected to MQTT broker")
        client.subscribe(TOPIC)
        print(f"Subscribed to topic: {TOPIC}")

        # This status message tells other files that the subscriber is online.
        client.publish(STATUS_TOPIC, "READY", retain=True)
        print("HVAC subscriber status: READY")
    else:
        print(f"Connection failed with code {reason_code}")


def on_message(client, userdata, msg):
    """Called whenever a new HVAC command is received."""
    command = msg.payload.decode().strip()
    print(f"Received HVAC command: {command}")

    if command == "HEAT_ON":
        print("Heating system ON")
    elif command == "COOL_ON":
        print("Cooling system ON")
    elif command == "OFF":
        print("HVAC system OFF")
    else:
        print("Unknown command received")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nHVAC subscriber stopped")
        client.disconnect()


if __name__ == "__main__":
    main()
