"""
Smart Campus MQTT integrated system.

This single file combines the parts from the team project:
- Sherkhan: environmental monitoring and HVAC control
- Medet: energy monitoring and smart plug control
- Kamal: security alerts and CCTV control
- Sagi: MQTT integration, SQLite storage, and dashboard

Run examples:
    python smart_campus_mqtt.py --role all
    python smart_campus_mqtt.py --role controller
    python smart_campus_mqtt.py --role environment-publisher
    python smart_campus_mqtt.py --role subscriber
    streamlit run smart_campus_mqtt.py -- --role dashboard
"""

from __future__ import annotations

import argparse
import json
import random
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Callable

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:
    mqtt = None


BROKER = "broker.hivemq.com"
PORT = 1883
DB_NAME = "sensor_data.db"

TOPICS = {
    "temperature": "campus/room1/temperature",
    "humidity": "campus/room1/humidity",
    "hvac": "campus/room1/hvac",
    "energy": "campus/energy/data",
    "energy_motion": "campus/energy/motion",
    "energy_alerts": "campus/energy/alerts",
    "energy_commands": "campus/energy/commands",
    "energy_confirmations": "campus/energy/confirmations",
    "security_motion": "campus/security/motion",
    "security_door": "campus/security/door",
    "security_alerts": "campus/security/alerts",
    "cctv": "campus/security/cctv",
}

SENSOR_TOPICS = [
    TOPICS["temperature"],
    TOPICS["humidity"],
    TOPICS["energy"],
    TOPICS["energy_motion"],
    TOPICS["energy_alerts"],
    TOPICS["energy_commands"],
    TOPICS["energy_confirmations"],
    TOPICS["security_motion"],
    TOPICS["security_door"],
    TOPICS["security_alerts"],
    TOPICS["cctv"],
    TOPICS["hvac"],
]

HVAC_LOW_C = 20.0
HVAC_HIGH_C = 26.0
MOTION_THRESHOLD = 70
DOOR_OPEN_LIMIT_SECONDS = 30
HIGH_POWER_THRESHOLD_W = 500
DEVICE_LEFT_ON_THRESHOLD_W = 50
AFTER_HOURS_START = 22
AFTER_HOURS_END = 6

DEVICES = {
    "lab1_computer": {"location": "lab1", "base_w": 150, "variance": 50},
    "lab1_printer": {"location": "lab1", "base_w": 30, "variance": 20},
    "lab2_projector": {"location": "lab2", "base_w": 250, "variance": 30},
    "library_lights": {"location": "library", "base_w": 200, "variance": 40},
    "server_room_ac": {"location": "server", "base_w": 800, "variance": 100},
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def is_after_hours() -> bool:
    hour = datetime.now().hour
    return hour >= AFTER_HOURS_START or hour < AFTER_HOURS_END


def mqtt_client(client_id: str, userdata: Any | None = None) -> mqtt.Client:
    if mqtt is None:
        raise RuntimeError("Missing dependency: install it with 'pip install paho-mqtt'")
    try:
        return mqtt.Client(client_id=client_id, userdata=userdata)
    except TypeError:
        return mqtt.Client(client_id, userdata=userdata)


def decode_payload(message: mqtt.MQTTMessage) -> Any:
    raw = message.payload.decode(errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def publish_json(client: mqtt.Client, topic: str, payload: dict[str, Any], qos: int = 1) -> None:
    client.publish(topic, json.dumps(payload), qos=qos)


def broker_is_available(broker: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((broker, port), timeout=timeout):
            return True
    except OSError as error:
        log(f"MQTT broker is not reachable: {broker}:{port} ({error})")
        return False


def connect_mqtt(client: mqtt.Client, broker: str, port: int) -> bool:
    try:
        client.connect(broker, port, 60)
        return True
    except OSError as error:
        log(f"Cannot connect to MQTT broker {broker}:{port}: {error}")
        log("Check internet connection, broker address, or run: python3 smart_campus_mqtt.py --role demo")
        return False


@dataclass
class DoorState:
    is_open: bool = False
    opened_at: datetime | None = None


class SmartCampusDatabase:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self._lock = threading.Lock()
        try:
            self._create_tables()
        except sqlite3.OperationalError:
            fallback_dir = Path(gettempdir()) / "smart_campus_mqtt"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.db_name = str(fallback_dir / Path(db_name).name)
            self._create_tables()
            log(f"SQLite database fallback path: {self.db_name}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def _create_tables(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def insert_sensor_data(self, topic: str, value: Any) -> None:
        value_text = value if isinstance(value, str) else json.dumps(value)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO sensor_data (topic, value) VALUES (?, ?)",
                (topic, value_text),
            )

    def insert_security_event(self, command: str, severity: str, source: str, message: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO security_events (command, severity, source, message)
                VALUES (?, ?, ?, ?)
                """,
                (command, severity, source, message),
            )


class IntegrationSubscriber:
    def __init__(self, broker: str, port: int, db: SmartCampusDatabase):
        self.client = mqtt_client("smart_campus_integration_subscriber")
        self.broker = broker
        self.port = port
        self.db = db
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int, *args: Any) -> None:
        if rc != 0:
            log(f"Integration subscriber connection failed: {rc}")
            return
        for topic in SENSOR_TOPICS:
            client.subscribe(topic, qos=1)
        log(f"Integration subscriber stores {len(SENSOR_TOPICS)} MQTT topics in {self.db.db_name}")

    def on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        payload = decode_payload(message)
        self.db.insert_sensor_data(message.topic, payload)
        log(f"DB saved | {message.topic}: {payload}")

    def start(self) -> None:
        if not connect_mqtt(self.client, self.broker, self.port):
            return
        self.client.loop_forever()


class HVACController:
    def __init__(self, broker: str, port: int):
        self.client = mqtt_client("smart_campus_hvac_controller")
        self.broker = broker
        self.port = port
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    @staticmethod
    def decide_command(temperature: float) -> str:
        if temperature < HVAC_LOW_C:
            return "HEAT_ON"
        if temperature > HVAC_HIGH_C:
            return "COOL_ON"
        return "OFF"

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int, *args: Any) -> None:
        if rc != 0:
            log(f"HVAC controller connection failed: {rc}")
            return
        client.subscribe(TOPICS["temperature"], qos=1)
        client.subscribe(TOPICS["hvac"], qos=1)
        log("HVAC controller subscribed to temperature and HVAC command topics")

    def on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        payload = decode_payload(message)
        if message.topic == TOPICS["hvac"]:
            log(f"HVAC actuator received command: {payload}")
            return

        try:
            temperature = float(payload["value"] if isinstance(payload, dict) else payload)
        except (TypeError, ValueError, KeyError):
            log(f"Invalid temperature payload: {payload}")
            return

        command = self.decide_command(temperature)
        publish_json(
            client,
            TOPICS["hvac"],
            {"command": command, "temperature_c": temperature, "timestamp": now_iso()},
        )
        log(f"Temperature {temperature} C -> HVAC {command}")

    def start(self) -> None:
        if not connect_mqtt(self.client, self.broker, self.port):
            return
        self.client.loop_forever()


class EnergyMonitor:
    def __init__(self, broker: str, port: int):
        self.client = mqtt_client("smart_campus_energy_monitor")
        self.broker = broker
        self.port = port
        self.latest_motion: dict[str, bool] = {}
        self.device_states: dict[str, str] = {}
        self.total_alerts = 0
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int, *args: Any) -> None:
        if rc != 0:
            log(f"Energy monitor connection failed: {rc}")
            return
        for topic in (TOPICS["energy"], TOPICS["energy_motion"], TOPICS["energy_commands"], TOPICS["energy_alerts"]):
            client.subscribe(topic, qos=1)
        log("Energy monitor subscribed to energy, motion, command, and alert topics")

    def publish_alert(self, client: mqtt.Client, alert: dict[str, Any]) -> None:
        self.total_alerts += 1
        publish_json(client, TOPICS["energy_alerts"], alert)
        if alert["severity"] == "CRITICAL":
            publish_json(client, TOPICS["security_alerts"], alert)
        log(f"Energy alert [{alert['severity']}]: {alert['message']}")

    def on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        payload = decode_payload(message)
        if not isinstance(payload, dict):
            return

        if message.topic == TOPICS["energy_motion"]:
            self.latest_motion[payload.get("location", "unknown")] = bool(payload.get("motion_detected"))
            return

        if message.topic == TOPICS["energy_commands"]:
            device_id = str(payload.get("device_id", "unknown"))
            action = str(payload.get("action", "unknown"))
            self.device_states[device_id] = action
            publish_json(
                client,
                TOPICS["energy_confirmations"],
                {"device_id": device_id, "action": action, "success": True, "timestamp": now_iso()},
            )
            log(f"Smart plug command applied: {device_id} -> {action}")
            return

        if message.topic != TOPICS["energy"]:
            return

        device = str(payload.get("device_id", "unknown"))
        location = str(payload.get("location", "unknown"))
        power = float(payload.get("power_w", 0))
        motion = self.latest_motion.get(location, True)

        if is_after_hours() and power > HIGH_POWER_THRESHOLD_W:
            alert = {
                "type": "HIGH_POWER_AFTER_HOURS",
                "severity": "CRITICAL",
                "device": device,
                "location": location,
                "power_w": power,
                "message": f"{device} consuming {power}W after hours",
                "timestamp": now_iso(),
            }
            self.publish_alert(client, alert)
            publish_json(
                client,
                TOPICS["energy_commands"],
                {"device_id": device, "action": "OFF", "reason": "High power after hours", "timestamp": now_iso()},
            )
            return

        if power > DEVICE_LEFT_ON_THRESHOLD_W and not motion:
            self.publish_alert(
                client,
                {
                    "type": "DEVICE_LEFT_ON",
                    "severity": "WARNING",
                    "device": device,
                    "location": location,
                    "power_w": power,
                    "message": f"{device} is ON but no motion was detected in {location}",
                    "timestamp": now_iso(),
                },
            )
            return

        log(f"Energy OK | {device}: {power}W at {location}")

    def start(self) -> None:
        if not connect_mqtt(self.client, self.broker, self.port):
            return
        self.client.loop_forever()


class SecurityController:
    def __init__(self, broker: str, port: int, db: SmartCampusDatabase):
        self.client = mqtt_client("smart_campus_security_controller")
        self.broker = broker
        self.port = port
        self.db = db
        self.total_alerts = 0
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int, *args: Any) -> None:
        if rc != 0:
            log(f"Security controller connection failed: {rc}")
            return
        for topic in (TOPICS["security_motion"], TOPICS["security_door"], TOPICS["security_alerts"], TOPICS["cctv"]):
            client.subscribe(topic, qos=1)
        log("Security controller subscribed to motion, door, security alert, and CCTV topics")

    def send_cctv_command(self, client: mqtt.Client, command: str, severity: str, source: str, text: str) -> None:
        payload = {
            "command": command,
            "severity": severity,
            "source": source,
            "message": text,
            "timestamp": now_iso(),
        }
        publish_json(client, TOPICS["cctv"], payload)
        self.db.insert_security_event(command, severity, source, text)
        if severity != "OK":
            self.total_alerts += 1
        log(f"CCTV {command} [{severity}] from {source}: {text}")

    def on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        payload = decode_payload(message)
        if message.topic == TOPICS["cctv"]:
            if isinstance(payload, dict):
                log(f"CCTV actuator: {payload.get('command')} from {payload.get('source')}")
            return

        if not isinstance(payload, dict):
            return

        if message.topic == TOPICS["security_motion"]:
            value = int(payload.get("value", 0))
            period = str(payload.get("period", "normal_hours"))
            if value >= MOTION_THRESHOLD and period == "after_hours":
                self.send_cctv_command(client, "RECORD", "CRITICAL", "motion", "Motion detected after hours")
            elif value >= MOTION_THRESHOLD:
                self.send_cctv_command(client, "MONITOR", "WARNING", "motion", "Motion detected during normal hours")
            else:
                self.send_cctv_command(client, "IDLE", "OK", "motion", "No motion threat")
            return

        if message.topic == TOPICS["security_door"]:
            state = str(payload.get("state", "CLOSED"))
            duration = int(payload.get("duration_s", 0))
            period = str(payload.get("period", "normal_hours"))
            if state == "OPEN" and period == "after_hours":
                self.send_cctv_command(client, "RECORD", "CRITICAL", "door", "Door opened after hours")
            elif state == "OPEN" and duration > DOOR_OPEN_LIMIT_SECONDS:
                self.send_cctv_command(client, "MONITOR", "WARNING", "door", "Door has been open too long")
            else:
                self.send_cctv_command(client, "IDLE", "OK", "door", "Door state normal")
            return

        if message.topic == TOPICS["security_alerts"]:
            severity = str(payload.get("severity", "WARNING"))
            command = "RECORD" if severity == "CRITICAL" else "MONITOR"
            self.send_cctv_command(client, command, severity, "energy", str(payload.get("message", "Energy alert")))

    def start(self) -> None:
        if not connect_mqtt(self.client, self.broker, self.port):
            return
        self.client.loop_forever()


def publish_environment_data(client: mqtt.Client, interval: int) -> None:
    while True:
        temperature = round(random.uniform(16.0, 30.0), 2)
        humidity = round(random.uniform(30.0, 80.0), 2)
        publish_json(client, TOPICS["temperature"], {"sensor": "temperature", "value": temperature, "unit": "C", "timestamp": now_iso()})
        publish_json(client, TOPICS["humidity"], {"sensor": "humidity", "value": humidity, "unit": "%", "timestamp": now_iso()})
        log(f"Environment published | temperature={temperature}C humidity={humidity}%")
        time.sleep(interval)


def publish_energy_data(client: mqtt.Client, interval: int) -> None:
    while True:
        locations_sent: set[str] = set()
        for device_id, profile in DEVICES.items():
            power = round(profile["base_w"] + random.uniform(-profile["variance"], profile["variance"]), 2)
            voltage = round(220 + random.uniform(-5, 5), 1)
            energy = {
                "device_id": device_id,
                "location": profile["location"],
                "power_w": power,
                "voltage_v": voltage,
                "current_a": round(power / voltage, 3),
                "energy_kwh": round(power / 1000, 4),
                "status": "ON",
                "timestamp": now_iso(),
            }
            publish_json(client, TOPICS["energy"], energy)
            log(f"Energy published | {device_id}: {power}W")

            location = str(profile["location"])
            if location not in locations_sent:
                motion = random.random() < (0.1 if is_after_hours() else 0.8)
                publish_json(client, TOPICS["energy_motion"], {"location": location, "motion_detected": motion, "timestamp": now_iso()})
                locations_sent.add(location)
        time.sleep(interval)


def publish_security_data(client: mqtt.Client, interval: int) -> None:
    door = DoorState()
    while True:
        if random.randint(1, 10) <= 2:
            door.is_open = not door.is_open
            door.opened_at = datetime.now() if door.is_open else None

        duration = 0
        if door.is_open and door.opened_at is not None:
            duration = int((datetime.now() - door.opened_at).total_seconds())

        period = "after_hours" if is_after_hours() else "normal_hours"
        motion_value = random.randint(70, 100) if random.randint(1, 100) <= 15 else random.randint(0, 50)
        publish_json(
            client,
            TOPICS["security_motion"],
            {"sensor": "PIR-Corridor-A", "value": motion_value, "status": "DETECTED" if motion_value >= MOTION_THRESHOLD else "clear", "period": period, "timestamp": now_iso()},
        )
        publish_json(
            client,
            TOPICS["security_door"],
            {"sensor": "Door-Main-Entrance", "state": "OPEN" if door.is_open else "CLOSED", "duration_s": duration, "period": period, "timestamp": now_iso()},
        )
        log(f"Security published | motion={motion_value} door={'OPEN' if door.is_open else 'CLOSED'}")
        time.sleep(interval)


def start_publisher(role: str, broker: str, port: int, interval: int) -> None:
    client = mqtt_client(f"smart_campus_{role}")
    if not connect_mqtt(client, broker, port):
        return
    client.loop_start()
    try:
        if role == "environment-publisher":
            publish_environment_data(client, interval)
        elif role == "energy-publisher":
            publish_energy_data(client, interval)
        elif role == "security-publisher":
            publish_security_data(client, interval)
        else:
            raise ValueError(f"Unknown publisher role: {role}")
    finally:
        client.loop_stop()
        client.disconnect()


def run_all(broker: str, port: int, interval: int, db: SmartCampusDatabase) -> None:
    if not broker_is_available(broker, port):
        log("Live MQTT mode cannot start, so a short offline demo will run instead.")
        run_demo(db, interval=1, cycles=5)
        return
    if mqtt is None:
        log("paho-mqtt is not installed. Run: pip install paho-mqtt")
        log("A short offline demo will run instead.")
        run_demo(db, interval=1, cycles=5)
        return

    components: list[Callable[[], None]] = [
        lambda: IntegrationSubscriber(broker, port, db).start(),
        lambda: HVACController(broker, port).start(),
        lambda: EnergyMonitor(broker, port).start(),
        lambda: SecurityController(broker, port, db).start(),
        lambda: start_publisher("environment-publisher", broker, port, interval),
        lambda: start_publisher("energy-publisher", broker, port, interval),
        lambda: start_publisher("security-publisher", broker, port, interval),
    ]

    for component in components:
        thread = threading.Thread(target=component, daemon=True)
        thread.start()

    log("All Smart Campus MQTT components are running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Smart Campus system stopped")


def run_demo(db: SmartCampusDatabase, interval: int, cycles: int = 5) -> None:
    door = DoorState()
    log("Offline demo started. This mode does not need internet or MQTT broker.")

    for cycle in range(1, cycles + 1):
        temperature = round(random.uniform(16.0, 30.0), 2)
        humidity = round(random.uniform(30.0, 80.0), 2)
        hvac_command = HVACController.decide_command(temperature)

        device_id = "server_room_ac"
        power = round(random.uniform(450.0, 950.0), 2)
        energy_severity = "CRITICAL" if is_after_hours() and power > HIGH_POWER_THRESHOLD_W else "OK"

        if random.randint(1, 10) <= 3:
            door.is_open = not door.is_open
            door.opened_at = datetime.now() if door.is_open else None

        duration = 0
        if door.is_open and door.opened_at is not None:
            duration = int((datetime.now() - door.opened_at).total_seconds())

        period = "after_hours" if is_after_hours() else "normal_hours"
        motion_value = random.randint(70, 100) if random.randint(1, 100) <= 25 else random.randint(0, 50)
        cctv_command = "RECORD" if motion_value >= MOTION_THRESHOLD and period == "after_hours" else "MONITOR" if motion_value >= MOTION_THRESHOLD else "IDLE"

        db.insert_sensor_data(TOPICS["temperature"], {"value": temperature, "unit": "C", "timestamp": now_iso()})
        db.insert_sensor_data(TOPICS["humidity"], {"value": humidity, "unit": "%", "timestamp": now_iso()})
        db.insert_sensor_data(TOPICS["energy"], {"device_id": device_id, "power_w": power, "timestamp": now_iso()})
        db.insert_sensor_data(TOPICS["security_motion"], {"value": motion_value, "period": period, "timestamp": now_iso()})
        db.insert_security_event(cctv_command, "OK" if cctv_command == "IDLE" else "WARNING", "demo", "Offline simulated CCTV event")

        log(
            f"Demo cycle {cycle}: temp={temperature}C -> HVAC {hvac_command}; "
            f"humidity={humidity}%; {device_id}={power}W [{energy_severity}]; "
            f"motion={motion_value}; door={'OPEN' if door.is_open else 'CLOSED'} {duration}s; CCTV={cctv_command}"
        )
        time.sleep(interval)

    log(f"Offline demo finished. Data was written to: {db.db_name}")


def run_dashboard(db_name: str) -> None:
    import pandas as pd
    import streamlit as st

    st.title("Smart Campus MQTT Dashboard")
    st.caption("Latest environmental, energy, security, and HVAC MQTT events")

    with sqlite3.connect(db_name) as connection:
        data = pd.read_sql_query("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 300", connection)
        security = pd.read_sql_query("SELECT * FROM security_events ORDER BY timestamp DESC LIMIT 100", connection)

    if data.empty:
        st.warning("No sensor data available yet.")
    else:
        st.subheader("Latest Sensor Events")
        st.dataframe(data, use_container_width=True)

    if not security.empty:
        st.subheader("Security Events")
        st.dataframe(security, use_container_width=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Smart Campus MQTT integrated system.")
    parser.add_argument(
        "--role",
        choices=[
            "all",
            "demo",
            "environment-publisher",
            "energy-publisher",
            "security-publisher",
            "controller",
            "subscriber",
            "dashboard",
        ],
        default="all",
    )
    parser.add_argument("--broker", default=BROKER)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--db", default=DB_NAME)
    parser.add_argument("--interval", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SmartCampusDatabase(args.db)
    live_mqtt_roles = {"environment-publisher", "energy-publisher", "security-publisher", "controller", "subscriber"}
    if args.role in live_mqtt_roles and mqtt is None:
        log("paho-mqtt is not installed. Run: pip install paho-mqtt")
        log("For an offline check, run: python3 smart_campus_mqtt.py --role demo")
        return

    if args.role == "all":
        run_all(args.broker, args.port, args.interval, db)
    elif args.role == "demo":
        run_demo(db, args.interval)
    elif args.role in {"environment-publisher", "energy-publisher", "security-publisher"}:
        start_publisher(args.role, args.broker, args.port, args.interval)
    elif args.role == "controller":
        components: list[Callable[[], None]] = [
            lambda: HVACController(args.broker, args.port).start(),
            lambda: EnergyMonitor(args.broker, args.port).start(),
            lambda: SecurityController(args.broker, args.port, db).start(),
        ]
        for component in components:
            threading.Thread(target=component, daemon=True).start()
        log("Controllers are running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log("Controllers stopped")
    elif args.role == "subscriber":
        IntegrationSubscriber(args.broker, args.port, db).start()
    elif args.role == "dashboard":
        run_dashboard(db.db_name)


if __name__ == "__main__":
    main()
