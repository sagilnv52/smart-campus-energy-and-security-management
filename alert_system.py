# alert_system.py
# AlertSystem class - evaluates sensor readings and decides severity
# Keeps a history of all alerts in memory
# Decides whether to trigger CCTV recording
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

from datetime import datetime


class AlertSystem:
    """Evaluates sensor readings and produces security alerts."""

    def __init__(self):
        # Store all alerts in a list
        self.alert_history = []

    def evaluate_motion(self, reading):
        """
        Check if a motion reading should trigger a security alert.
        
        Rules:
        - Motion after hours   -> CRITICAL (possible intrusion)
        - Motion during day    -> WARNING (monitoring)
        - No motion            -> None (no alert)
        """
        if not reading["detected"]:
            return None

        if reading["after_hours"]:
            severity = "CRITICAL"
            message = "Motion detected at {} (confidence: {:.0%}). AFTER HOURS - possible intrusion.".format(
                reading["location"], reading["value"])
        else:
            severity = "WARNING"
            message = "Motion detected at {} (confidence: {:.0%}). Normal hours - monitoring.".format(
                reading["location"], reading["value"])

        alert = {
            "severity": severity,
            "message": message,
            "sensor_name": reading["sensor_name"],
            "location": reading["location"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Save to history
        self.alert_history.append(alert)
        return alert

    def evaluate_door_window(self, reading):
        """
        Check if a door/window event should trigger an alert.
        
        Rules:
        - Opened after hours         -> CRITICAL
        - Open longer than limit     -> WARNING
        - Normal opening during day  -> INFO
        - Closed                     -> None
        """
        if not reading["is_open"]:
            return None

        if reading["after_hours"]:
            severity = "CRITICAL"
            message = "{} opened after hours at {}. Possible unauthorised entry.".format(
                reading["entry_type"].capitalize(), reading["location"])
        elif reading["violation"]:
            severity = "WARNING"
            message = "{} at {} open for {}s - exceeds limit.".format(
                reading["entry_type"].capitalize(),
                reading["location"],
                reading["open_duration_sec"])
        else:
            severity = "INFO"
            message = "{} opened at {}.".format(
                reading["entry_type"].capitalize(), reading["location"])

        alert = {
            "severity": severity,
            "message": message,
            "sensor_name": reading["sensor_name"],
            "location": reading["location"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.alert_history.append(alert)
        return alert

    def should_trigger_cctv(self, alert):
        """Only WARNING and CRITICAL alerts trigger CCTV."""
        if alert is None:
            return False
        if alert["severity"] == "WARNING" or alert["severity"] == "CRITICAL":
            return True
        return False

    def get_recent_alerts(self, count=10):
        """Get the last N alerts from history."""
        return self.alert_history[-count:]

    def __str__(self):
        return "AlertSystem(total_alerts={})".format(len(self.alert_history))
