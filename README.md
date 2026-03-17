# Smart Campus Energy and Security Management System

## Software-Only MQTT Module

This project is the software-only part of an IoT system for smart campus monitoring, energy tracking, and HVAC control.

The system uses Python and the `paho-mqtt` library to simulate:

- temperature sensor data
- humidity sensor data
- energy consumption data

The generated sensor values are published to an MQTT broker, and the HVAC system is automatically controlled according to the received temperature values.

## Technologies Used

- Python
- paho-mqtt
- MQTT protocol
- HiveMQ public broker

## MQTT Broker Settings

- Broker: `broker.hivemq.com`
- Port: `1883`

## Main MQTT Topics

- `campus/room1/temperature`
- `campus/room1/humidity`
- `campus/room1/energy`
- `campus/room1/hvac`

## Extra Status Topics for Startup Dependency

In this upgraded version, extra MQTT status topics are used so that the files depend on each other in startup order.

- `campus/room1/status/hvac_subscriber`
- `campus/room1/status/hvac_controller`

These topics are only used to manage readiness between the files.

## Project Files

### `temperature_publisher.py`

- Simulates temperature values using random numbers
- Waits until the HVAC controller is ready
- Publishes temperature data every 5 seconds
- Sends data to `campus/room1/temperature`

### `humidity_publisher.py`

- Simulates humidity values using random numbers
- Waits until the HVAC controller is ready
- Publishes humidity data every 5 seconds
- Sends data to `campus/room1/humidity`

### `energy_publisher.py`

- Simulates energy consumption values using random numbers
- Waits until the HVAC controller is ready
- Publishes energy data every 5 seconds
- Sends data to `campus/room1/energy`

### `hvac_controller.py`

- Waits until the HVAC subscriber is ready
- Subscribes to `campus/room1/temperature`
- Reads incoming temperature values
- Applies HVAC control logic:
  - If temperature is below 20, publish `HEAT_ON`
  - If temperature is above 26, publish `COOL_ON`
  - Otherwise, publish `OFF`
- Sends commands to `campus/room1/hvac`
- Publishes its readiness status for the publishers

### `hvac_subscriber.py`

- Starts first in the system
- Subscribes to `campus/room1/hvac`
- Receives HVAC commands
- Prints the received command
- Displays:
  - `Heating system ON`
  - `Cooling system ON`
  - `HVAC system OFF`
- Publishes its readiness status for the controller

## Startup Dependency Logic

This upgraded version is designed so that the files depend on each other in a logical startup sequence.

1. `hvac_subscriber.py` starts first and publishes a `READY` message.
2. `hvac_controller.py` waits for the subscriber `READY` message.
3. After the controller becomes ready, it publishes its own `READY` message.
4. `temperature_publisher.py`, `humidity_publisher.py`, and `energy_publisher.py` wait for the controller `READY` message.
5. After that, the publishers begin sending sensor data.

This makes the order meaningful and easier to explain during project presentation.

## System Workflow

1. The HVAC subscriber starts and announces that it is ready.
2. The HVAC controller starts after the subscriber is ready.
3. The controller waits for temperature values.
4. The temperature publisher starts after the controller is ready.
5. The humidity publisher and energy publisher also start after the controller is ready.
6. Temperature values are checked by the HVAC controller.
7. The HVAC controller publishes `HEAT_ON`, `COOL_ON`, or `OFF`.
8. The HVAC subscriber receives the command and prints the HVAC state.

## Data Flow

`temperature publisher / humidity publisher / energy publisher -> MQTT broker -> HVAC controller / HVAC subscriber`

## Installation

Install the required library:

```bash
pip install paho-mqtt
