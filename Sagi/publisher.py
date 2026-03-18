"""
publisher.py
Author: Sagi Alyonov

This file contains the publisher class.
The publisher sends sensor data to the MQTT broker.
"""

# Required libraries
import paho.mqtt.client as mqtt
import random
import time

# Global configuration variables
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "home/temperature"

class Publisher:
    """
    Publisher class for sending sensor data to MQTT.
    """

    def __init__(self, broker, port, topic):
        """
        Initialize publisher object with broker settings and topic.
        """
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()

    def connect_to_broker(self):
        """
        Connect publisher to MQTT broker.
        """
        self.client.connect(self.broker, self.port)
        print(f"Connected to broker: {self.broker} on port {self.port}")

    def generate_temperature(self):
        """
        Generate a random temperature value.
        """
        return random.randint(20, 30)

    def publish_data(self):
        """
        Publish temperature data continuously every 5 seconds.
        """
        while True:
            temperature = self.generate_temperature()
            self.client.publish(self.topic, temperature)
            print(f"Published to {self.topic}: {temperature}")
            time.sleep(5)

def main():
    """
    Main function to run the publisher.
    """
    publisher = Publisher(BROKER, PORT, TOPIC)
    publisher.connect_to_broker()
    publisher.publish_data()

if __name__ == "__main__":
    main()