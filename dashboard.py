"""
dashboard.py
Author: Sagi Alyonov

This file creates a simple IoT dashboard using Streamlit.
It reads sensor data from the SQLite database and displays it.
It also sends control commands to devices using MQTT.
"""

# Required libraries
import streamlit as st
import sqlite3
import pandas as pd
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883

class CommandPublisher:
    """
    This class publishes control commands to MQTT topics.
    """

    def __init__(self, broker, port):
        """
        Initialize publisher with broker settings.
        """
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()

    def publish_command(self, topic, message):
        """
        Connect to the broker and publish a command message.
        """
        self.client.connect(self.broker, self.port)
        self.client.publish(topic, message)
        self.client.disconnect()


class Dashboard:
    """
    Dashboard class responsible for reading sensor data
    from SQLite and displaying it using Streamlit.
    """

    def __init__(self, db_name="sensor_data.db"):
        """
        Initialize dashboard with database name.
        """
        self.db_name = db_name
        self.command_publisher = CommandPublisher(BROKER, PORT)

    def load_data(self):
        """
        Load sensor data from SQLite database.
        """
        connection = sqlite3.connect(self.db_name)

        query = """
        SELECT * FROM sensor_data
        ORDER BY timestamp DESC
        """

        data = pd.read_sql_query(query, connection)

        connection.close()

        return data

    def show_latest_values(self, data):
        """
        Display the latest value for each sensor topic.
        """
        st.subheader("Latest Sensor Values")

        unique_topics = data["topic"].unique()

        for topic in unique_topics:
            latest = data[data["topic"] == topic].iloc[0]

            st.metric(
                label=topic,
                value=latest["value"]
            )

    def show_controls(self):
        """
        Display control buttons for sending commands to devices.
        """
        st.subheader("Device Controls")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Turn HVAC ON"):
                self.command_publisher.publish_command("home/hvac", "ON")
                st.success("HVAC ON command sent")

            if st.button("Turn HVAC OFF"):
                self.command_publisher.publish_command("home/hvac", "OFF")
                st.success("HVAC OFF command sent")

            if st.button("Turn Light ON"):
                self.command_publisher.publish_command("home/light", "ON")
                st.success("Light ON command sent")

            if st.button("Turn Light OFF"):
                self.command_publisher.publish_command("home/light", "OFF")
                st.success("Light OFF command sent")

        with col2:
            if st.button("Arm Security"):
                self.command_publisher.publish_command("home/security/control", "ARM")
                st.success("Security ARM command sent")

            if st.button("Disarm Security"):
                self.command_publisher.publish_command("home/security/control", "DISARM")
                st.success("Security DISARM command sent")

    def show_table(self, data):
        """
        Display all sensor data in table form.
        """
        st.subheader("All Sensor Data")
        st.dataframe(data)

    def show_dashboard(self):
        """
        Main dashboard interface.
        """
        st.title("IoT System Integration Dashboard")
        st.write("Displaying data received from MQTT sensors.")

        data = self.load_data()

        if data.empty:
            st.warning("No sensor data available yet.")
            return

        self.show_latest_values(data)

        st.divider()

        self.show_controls()

        st.divider()

        self.show_table(data)

def main():
    """
    Main program entry point.
    """
    dashboard = Dashboard()
    dashboard.show_dashboard()

if __name__ == "__main__":
    main()