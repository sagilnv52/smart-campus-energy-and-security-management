import paho.mqtt.client as mqtt


BROKER = "broker.hivemq.com"
PORT = 1883
TEMPERATURE_TOPIC = "campus/room1/temperature"
HVAC_TOPIC = "campus/room1/hvac"
SUBSCRIBER_STATUS_TOPIC = "campus/room1/status/hvac_subscriber"
CONTROLLER_STATUS_TOPIC = "campus/room1/status/hvac_controller"


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the client connects to the MQTT broker."""
    if reason_code == 0:
        print("Connected to MQTT broker")
        client.subscribe(SUBSCRIBER_STATUS_TOPIC)
        print("Waiting for HVAC subscriber to become ready...")
    else:
        print(f"Connection failed with code {reason_code}")


def decide_hvac_command(temperature):
    """Choose the HVAC command based on the temperature."""
    if temperature < 20:
        return "HEAT_ON"
    if temperature > 26:
        return "COOL_ON"
    return "OFF"


def on_message(client, userdata, msg):
    """Called whenever a new message is received."""
    if msg.topic == SUBSCRIBER_STATUS_TOPIC:
        message = msg.payload.decode().strip()

        if message == "READY" and not userdata["subscriber_ready"]:
            userdata["subscriber_ready"] = True
            client.subscribe(TEMPERATURE_TOPIC)
            print("HVAC subscriber is ready.")
            print(f"Subscribed to topic: {TEMPERATURE_TOPIC}")

            # This status message tells publishers that the controller is online.
            client.publish(CONTROLLER_STATUS_TOPIC, "READY", retain=True)
            print("HVAC controller status: READY")
        return

    try:
        temperature = float(msg.payload.decode())
    except ValueError:
        print("Received invalid temperature data")
        return

    print(f"Received temperature: {temperature} C")

    command = decide_hvac_command(temperature)
    client.publish(HVAC_TOPIC, command)
    print(f"Published HVAC command: {command}")


def main():
    status = {"subscriber_ready": False}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=status)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nHVAC controller stopped")
        client.disconnect()


if __name__ == "__main__":
    main()
