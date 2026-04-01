# security_publisher.py
# Main publisher script for the Security subsystem
#
# Creates 3 separate MQTT clients - one per sensor type:
#   Client 1 (Pair 1): Motion sensors   -> publishes to motion topic
#   Client 2 (Pair 2): Door/window      -> publishes to door_window topic
#   Client 3 (Pair 3): CCTV cameras     -> publishes to cctv topic
#
# Each client is its own broker connection = 3 client-broker pairs
# Combined with the subscriber (Pair 4) this gives 4 pairs total
#
# Data flow:
#   Sensors -> AlertSystem -> MQTT Broker -> SecurityDatabase
#
# Author: Kamal
# Project: Smart Campus Energy and Security Management (KZ4005CMD)
# Date: April 2026

import paho.mqtt.client as mqtt
import json
import time

from config import (BROKER_ADDRESS, PORT, SENSOR_INTERVAL,
                    TOPIC_MOTION, TOPIC_DOOR_WINDOW, TOPIC_CCTV, TOPIC_SECURITY_LOG,
                    CLIENT_MOTION_PUB, CLIENT_DOOR_PUB, CLIENT_CCTV_PUB)
from motion_sensor import MotionSensor
from door_window_sensor import DoorWindowSensor
from cctv_camera import CCTVCamera
from alert_system import AlertSystem
from database import SecurityDatabase


# ---- MQTT Callbacks ----
# Same pattern as on_connect from class tutorials

def on_connect_motion(client, userdata, flags, rc):
    if rc == 0:
        print("[MOTION CLIENT] Connected successfully! Code:", rc)
    else:
        print("[MOTION CLIENT] Bad connection. Code:", rc)


def on_connect_door(client, userdata, flags, rc):
    if rc == 0:
        print("[DOOR CLIENT] Connected successfully! Code:", rc)
    else:
        print("[DOOR CLIENT] Bad connection. Code:", rc)


def on_connect_cctv(client, userdata, flags, rc):
    if rc == 0:
        print("[CCTV CLIENT] Connected successfully! Code:", rc)
    else:
        print("[CCTV CLIENT] Bad connection. Code:", rc)


# ---- Main program ----

def main():
    # Create shared objects
    alert_system = AlertSystem()
    db = SecurityDatabase()

    # ---- Create 3 MQTT clients (3 client-broker pairs) ----

    # Pair 1: Motion publisher
    motion_client = mqtt.Client(CLIENT_MOTION_PUB)
    motion_client.on_connect = on_connect_motion

    # Pair 2: Door/window publisher
    door_client = mqtt.Client(CLIENT_DOOR_PUB)
    door_client.on_connect = on_connect_door

    # Pair 3: CCTV publisher
    cctv_client = mqtt.Client(CLIENT_CCTV_PUB)
    cctv_client.on_connect = on_connect_cctv

    # Connect all clients to broker
    try:
        motion_client.connect(BROKER_ADDRESS, PORT)
        door_client.connect(BROKER_ADDRESS, PORT)
        cctv_client.connect(BROKER_ADDRESS, PORT)
    except:
        print("Connection to broker failed. Check your network.")
        return

    # Start network loops for all clients
    motion_client.loop_start()
    door_client.loop_start()
    cctv_client.loop_start()
    time.sleep(1)  # Wait for connections

    # ---- Create sensor objects (OOP) ----

    # Motion sensors
    pir_corridor = MotionSensor("PIR-Corridor-A", "Block-A Corridor-1")
    pir_lab = MotionSensor("PIR-Lab-B", "Block-B Lab-201")
    motion_sensors = [pir_corridor, pir_lab]

    # Door/window sensors
    door_main = DoorWindowSensor("Door-Main-Entrance", "Block-A Ground Floor", "door")
    window_lab = DoorWindowSensor("Window-Lab-B", "Block-B Lab-201", "window")
    dw_sensors = [door_main, window_lab]

    # CCTV cameras
    cctv_entrance = CCTVCamera("CCTV-Entrance-North", "Block-A Main Entrance")
    cctv_lab = CCTVCamera("CCTV-Lab-B", "Block-B Lab-201")
    cameras = [cctv_entrance, cctv_lab]

    print("\nAll 3 publisher clients connected. Starting sensor loop...\n")

    try:
        cycle = 1
        while True:
            print("=" * 50)
            print("  CYCLE {}".format(cycle))
            print("=" * 50)

            # ---- Pair 1: Motion sensors publish ----
            for sensor in motion_sensors:
                reading = sensor.read()
                payload = json.dumps(reading)

                # Publish on motion client
                motion_client.publish(TOPIC_MOTION, payload)
                db.insert_reading(reading)

                status = "DETECTED" if reading["detected"] else "clear"
                print("  [MOTION] {}: {:.2f} ({})".format(
                    sensor.name, reading["value"], status))

                # Evaluate alert
                alert = alert_system.evaluate_motion(reading)
                if alert is not None:
                    motion_client.publish(TOPIC_SECURITY_LOG, json.dumps(alert))
                    db.insert_alert(alert)
                    print("  !! ALERT [{}] {}".format(alert["severity"], alert["message"]))

                    # Trigger CCTV if serious
                    if alert_system.should_trigger_cctv(alert):
                        cameras[0].start_recording("motion_alert")
                        cam_data = cameras[0].get_status()
                        cctv_client.publish(TOPIC_CCTV, json.dumps(cam_data))

            # ---- Pair 2: Door/window sensors publish ----
            for sensor in dw_sensors:
                reading = sensor.read()
                payload = json.dumps(reading)

                # Publish on door client
                door_client.publish(TOPIC_DOOR_WINDOW, payload)
                db.insert_reading(reading)

                state = "OPEN" if reading["is_open"] else "closed"
                print("  [DOOR/WIN] {}: {} ({}s)".format(
                    sensor.name, state, reading["open_duration_sec"]))

                # Evaluate alert
                alert = alert_system.evaluate_door_window(reading)
                if alert is not None and alert["severity"] != "INFO":
                    door_client.publish(TOPIC_SECURITY_LOG, json.dumps(alert))
                    db.insert_alert(alert)
                    print("  !! ALERT [{}] {}".format(alert["severity"], alert["message"]))

                    if alert_system.should_trigger_cctv(alert):
                        cameras[0].start_recording("door_window_alert")
                        cam_data = cameras[0].get_status()
                        cctv_client.publish(TOPIC_CCTV, json.dumps(cam_data))

            # ---- Pair 3: Camera status publish ----
            for cam in cameras:
                cam_data = cam.get_status()
                if cam_data["is_recording"]:
                    cctv_client.publish(TOPIC_CCTV, json.dumps(cam_data))
                    print("  [CCTV] {}: recording ({}s)".format(
                        cam.name, cam_data["elapsed_sec"]))

            print("  -- sleeping {}s --\n".format(SENSOR_INTERVAL))
            cycle += 1
            time.sleep(SENSOR_INTERVAL)

    except KeyboardInterrupt:
        print("\nShutting down...")

    # ---- Print database summary ----
    print("\n" + "=" * 50)
    print("  DATABASE SUMMARY")
    print("=" * 50)
    all_readings = db.get_all_readings()
    all_alerts = db.get_all_alerts()
    print("  Total readings: {}".format(len(all_readings)))
    print("  Total alerts: {}".format(len(all_alerts)))
    severity_counts = db.count_alerts_by_severity()
    for severity, count in severity_counts:
        print("    {}: {}".format(severity, count))

    # Cleanup all clients
    for cam in cameras:
        cam.stop_recording()
    motion_client.loop_stop()
    door_client.loop_stop()
    cctv_client.loop_stop()
    motion_client.disconnect()
    door_client.disconnect()
    cctv_client.disconnect()
    print("\nAll clients disconnected.")


if __name__ == "__main__":
    main()
