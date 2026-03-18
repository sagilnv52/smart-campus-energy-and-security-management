"""
subscriber.py
Author: Sagi Alyonov

This file contains the subscriber class.
The subscriber listens to MQTT topics and receives messages.
"""

# Required libraries
import paho.mqtt.client as mqtt
import sqlite3

# Global configuration variables
BROKER = "broker.hivemq.com"
PORT = 1883
TOPICS = [
    "home/temperature",
    "home/humidity",
    "home/energy",
    "home/security"
]

class DatabaseManager:
    """
    This class manages the SQLite database
    used to store sensor data.
    """

    def __init__(self):
        self.connection = sqlite3.connect("sensor_data.db")
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        """
        Create a table for storing MQTT data.
        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.connection.commit()

    def insert_data(self, topic, value):
        """
        Save received MQTT data into database.
        """
        self.cursor.execute(
            "INSERT INTO sensor_data (topic, value) VALUES (?, ?)",
            (topic, value)
        )
        self.connection.commit()

class Subscriber:
    """
    Subscriber class for receiving sensor data from MQTT.
    """

    def __init__(self, broker, port, topics):
        """
        Initialize subscriber object with broker settings and topics.
        """
        self.broker = broker
        self.port = port
        self.topics = topics
        self.client = mqtt.Client()
        

        # Attach callback functions
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.database = DatabaseManager()

    def on_connect(self, client, userdata, flags, rc):
        """
        This method runs automatically after connection to the broker.
        It subscribes to all required topics.
        """
        print(f"Connected to broker: {self.broker} on port {self.port}")

        for topic in self.topics:
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")

    def on_message(self, client, userdata, msg):
        """
        This method runs automatically when a message is received.
        """
        message = msg.payload.decode()
        print("\nReceived Data")
        print(f"Topic   : {msg.topic}")
        print(f"Message : {message}")
        self.database.insert_data(msg.topic, message)

    def start(self):
        """
        Connect to broker and keep listening forever.
        """
        self.client.connect(self.broker, self.port)
        self.client.loop_forever()


def main():
    """
    Main function to run the subscriber.
    """
    subscriber = Subscriber(BROKER, PORT, TOPICS)
    subscriber.start()

if __name__ == "__main__":
    main()