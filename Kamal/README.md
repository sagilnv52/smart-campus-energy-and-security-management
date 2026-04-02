# Smart Campus Security System

## What this project does

This project simulates a security system for a university campus using MQTT.
Sensors detect motion and door activity, the alert controller evaluates threats,
and the CCTV camera responds accordingly.

## How it works

1. Motion sensor sends readings like "82;DETECTED;after_hours"
2. Door sensor sends readings like "OPEN;45;normal_hours"
3. Alert controller evaluates the data and decides severity:
   - CRITICAL = motion or door open after hours
   - WARNING = motion during day or door open too long
   - OK = no threats
4. Alert controller sends commands to CCTV: RECORD, MONITOR, or IDLE
5. CCTV subscriber receives commands and saves them to SQLite database

## Technologies

- Python
- paho-mqtt
- SQLite3
- HiveMQ public broker

## MQTT Topics

- `campus/security/motion` - motion sensor data
- `campus/security/door` - door sensor data
- `campus/security/cctv` - CCTV commands

## Files

- `motion_publisher.py` - MotionSensor class, publishes motion data
- `door_publisher.py` - DoorSensor class, publishes door data
- `alert_controller.py` - AlertController class, evaluates threats
- `cctv_subscriber.py` - SecurityDatabase class, saves events to SQLite

## Client-Broker Pairs

- Pair 1: kamal_motion_publisher (publishes motion)
- Pair 2: kamal_door_publisher (publishes door state)
- Pair 3: kamal_alert_controller (subscribes + publishes commands)
- Pair 4: kamal_cctv_subscriber (subscribes + saves to database)

## How to run

```
pip install paho-mqtt
python cctv_subscriber.py
python alert_controller.py
python motion_publisher.py
python door_publisher.py
```

## Data Flow

```
motion_publisher --> broker --> alert_controller --> broker --> cctv_subscriber
door_publisher   --> broker --> alert_controller --> broker --> cctv_subscriber
```
