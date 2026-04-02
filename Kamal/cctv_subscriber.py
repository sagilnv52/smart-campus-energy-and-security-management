"""
cctv_subscriber.py
Author: Kamal

This file is the CCTV camera controller.
It receives commands from the alert controller and acts on them.
It saves every event to a SQLite database.

Incoming message format: "command;severity;source"
Example: "RECORD;CRITICAL;motion"
"""

import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT settings
BROKER = "broker.hivemq.com"
PORT = 1883
CCTV_TOPIC = "campus/security/cctv"

# Database
DB_NAME = "security_data.db"


class SecurityDatabase:
    """
    This class handles saving security events to SQLite.
    """

    def __init__(self, db_name):
        """Create the database and table."""
        self.db_name = db_name
        self.create_table()

    def create_table(self):
        """Create the table if it does not exist."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS security_events
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           command TEXT,
                           severity TEXT,
                           source TEXT,
                           time_received TEXT)""")

        conn.commit()
        cursor.close()
        conn.close()
        print("Database ready: " + self.db_name)

    def save_event(self, command, severity, source):
        """Save one security event to the database."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "INSERT INTO security_events (command, severity, source, time_received) VALUES (?, ?, ?, ?)",
                (command, severity, source, time_now))

            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            print("Database error: " + str(e))

    def get_event_count(self):
        """Count how many events are in the database."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM security_events")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        except:
            return 0


# Create database object
db = SecurityDatabase(DB_NAME)


# ---- MQTT callbacks ----

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(CCTV_TOPIC)
        print("Subscribed to: " + CCTV_TOPIC)
        print("")
        print("Waiting for commands...")
    else:
        print("Connection failed. Code: " + str(rc))


def on_message(client, userdata, msg):
    message = msg.payload.decode()

    # Parse message: "command;severity;source"
    parts = message.split(";")

    if len(parts) < 3:
        print("Bad message: " + message)
        return

    command = parts[0]
    severity = parts[1]
    source = parts[2]

    # React to the command
    print("")
    if command == "RECORD" and severity == "CRITICAL":
        print("!!! CRITICAL ALERT from " + source + " !!!")
        print(">>> CCTV RECORDING STARTED <<<")
    elif command == "MONITOR" and severity == "WARNING":
        print("WARNING from " + source)
        print(">>> CCTV monitoring mode <<<")
    elif command == "IDLE":
        print("IDLE from " + source + " - no threats")
    else:
        print("Command: " + command + " Severity: " + severity)

    # Save to database
    db.save_event(command, severity, source)

    # Show how many events total
    total = db.get_event_count()
    print("  (Total events in database: " + str(total) + ")")


# ---- Main program ----

client = mqtt.Client("kamal_cctv_subscriber")
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker...")
client.connect(BROKER, PORT)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("")
    total = db.get_event_count()
    print("CCTV subscriber stopped. Total events saved: " + str(total))
    client.disconnect()
