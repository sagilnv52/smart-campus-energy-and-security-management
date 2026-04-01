# database.py
# SecurityDatabase class - stores readings and alerts in SQLite
# Based on the same approach from Week 2 tutorial
# (Health_data_subscriber_database.py)
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

import sqlite3
import json
from datetime import datetime


class SecurityDatabase:
    """Handles all SQLite database operations for the security system."""

    def __init__(self, db_name="security_data.db"):
        self.db_name = db_name
        # Create tables on startup
        self.create_tables()

    def create_tables(self):
        """Create database tables if they don't exist yet."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Table for sensor readings
            cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_readings
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               sensor_name TEXT,
                               sensor_type TEXT,
                               location TEXT,
                               reading_data TEXT,
                               time_received TEXT)''')

            # Table for security alerts
            cursor.execute('''CREATE TABLE IF NOT EXISTS alerts
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               severity TEXT,
                               message TEXT,
                               sensor_name TEXT,
                               location TEXT,
                               time_received TEXT)''')

            conn.commit()
            cursor.close()
            conn.close()
            print("Database ready: " + self.db_name)

        except sqlite3.Error as e:
            print("Error creating database:", e)

    def insert_reading(self, reading):
        """Insert a sensor reading into the database."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            time_received = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reading_json = json.dumps(reading)

            cursor.execute(
                "INSERT INTO sensor_readings (sensor_name, sensor_type, location, reading_data, time_received) VALUES (?, ?, ?, ?, ?)",
                (reading.get("sensor_name", ""),
                 reading.get("type", ""),
                 reading.get("location", ""),
                 reading_json,
                 time_received))

            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            print("Error inserting reading:", e)

    def insert_alert(self, alert):
        """Insert a security alert into the database."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            time_received = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "INSERT INTO alerts (severity, message, sensor_name, location, time_received) VALUES (?, ?, ?, ?, ?)",
                (alert["severity"],
                 alert["message"],
                 alert["sensor_name"],
                 alert["location"],
                 time_received))

            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            print("Error inserting alert:", e)

    def get_all_readings(self):
        """Fetch all sensor readings."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sensor_readings ORDER BY id DESC")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except sqlite3.Error as e:
            print("Error fetching readings:", e)
            return []

    def get_all_alerts(self):
        """Fetch all alerts."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts ORDER BY id DESC")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except sqlite3.Error as e:
            print("Error fetching alerts:", e)
            return []

    def count_alerts_by_severity(self):
        """Count alerts grouped by severity level."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT severity, COUNT(*) FROM alerts GROUP BY severity")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except sqlite3.Error as e:
            print("Error counting alerts:", e)
            return []

    def __str__(self):
        readings = len(self.get_all_readings())
        alerts = len(self.get_all_alerts())
        return "SecurityDatabase(readings={}, alerts={})".format(readings, alerts)
