# smart-campus-energy-and-security-management
Smart campus IoT system using MQTT, SQLite, and Streamlit to monitor temperature, energy usage, and security sensors.
# Smart Campus Energy and Security Management

## Overview

This project implements an **IoT-based smart campus monitoring system** using MQTT communication.
The system collects data from different sensors (environmental, energy, and security), stores the data in a database, and displays it on a dashboard.

The goal of the project is to demonstrate **system integration in IoT**, where multiple components communicate through MQTT and are managed from a central system.

Technologies Used
**Python**
**MQTT (Paho MQTT library)**
**SQLite database**
**Streamlit dashboard**

System Architecture

The system works as a pipeline:

Sensors (Publisher)
→ MQTT Broker
→ Subscriber (Data Collector)
→ SQLite Database
→ Streamlit Dashboard

The dashboard can also send **control commands** to devices through MQTT.

Project Components

Publisher (`publisher.py`)

Simulates sensor devices that send data to the MQTT broker.

Example data:

* Temperature values
* Energy consumption information

### Subscriber (`subscriber.py`)

Receives MQTT messages from sensors and:

* Processes the data
* Stores the data in an SQLite database

Database file:
`sensor_data.db`

### Dashboard (`dashboard.py`)

A web dashboard built with **Streamlit** that:

* Displays the latest sensor values
* Shows all stored sensor data
* Sends control commands to devices (HVAC, lights, security)
Installation

1. Install required libraries

```bash
python3 -m pip install paho-mqtt streamlit pandas
```

2. Run the subscriber

```bash
python3 subscriber.py
```

3. Run the publisher

```bash
python3 publisher.py
```

4. Start the dashboard

```bash
python3 -m streamlit run dashboard.py
```

The dashboard will open automatically in your browser.

Example MQTT Topics

| Topic            | Description             |
| ---------------- | ----------------------- |
| home/temperature | Temperature sensor data |
| home/humidity    | Humidity sensor data    |
| home/energy      | Energy usage data       |
| home/security    | Security alerts         |
| home/hvac        | HVAC control commands   |
| home/light       | Light control commands  |

Features

* MQTT communication between devices
* Data storage using SQLite
* Real-time dashboard visualization
* Device control via MQTT commands

Author

Sagi Alyonov**

University IoT System Integration Project
