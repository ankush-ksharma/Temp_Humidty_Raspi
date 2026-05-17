# Smart Temperature & Humidity Sensor

A Raspberry Pi-based IoT project that monitors temperature and humidity using a DHT22 sensor, displays real-time readings on an OLED screen, and logs data for statistical analysis.

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [Software Architecture](#software-architecture)
- [Project Structure](#project-structure)
- [Module Documentation](#module-documentation)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Storage](#data-storage)

---

## Overview

This application continuously monitors environmental conditions using a DHT22 temperature/humidity sensor connected to a Raspberry Pi. It features:

- **Real-time monitoring**: Reads sensor data every 10 seconds (configurable)
- **OLED Display**: Shows current temperature, humidity, time, date, and daily min/max statistics
- **Data Logging**: Stores readings in daily CSV files for historical analysis
- **Multi-threaded Architecture**: Separates sensor reading from display updates for smooth operation

---

## Hardware Requirements

| Component | Description |
|-----------|-------------|
| Raspberry Pi | Any model with GPIO pins (tested on Pi Zero W) |
| DHT22 Sensor | Temperature & humidity sensor connected to GPIO4 |
| SSD1306 OLED Display | 128x64 pixel I2C OLED display (address: 0x3C) |

### Wiring Diagram

```
DHT22 Sensor:
  - VCC → 3.3V (Pin 1)
  - DATA → GPIO4 (Pin 7)
  - GND → Ground (Pin 6)

SSD1306 OLED:
  - VCC → 3.3V (Pin 1)
  - GND → Ground (Pin 6)
  - SCL → GPIO3/SCL (Pin 5)
  - SDA → GPIO2/SDA (Pin 3)
```

---

## Software Architecture

The application uses a **multi-threaded design** to ensure smooth display updates:

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────────┐        ┌──────────────────┐          │
│   │  Sensor Thread   │        │   Main Thread    │          │
│   │  (Background)    │        │   (Display)      │          │
│   ├──────────────────┤        ├──────────────────┤          │
│   │ - Read DHT22     │        │ - Update OLED    │          │
│   │ - Log to CSV     │  ───►  │ - Show time      │          │
│   │ - Calculate stats│ shared │ - Show readings  │          │
│   │ - Every 10 sec   │  data  │ - Every 1 sec    │          │
│   └──────────────────┘        └──────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Why multi-threaded?**
- DHT22 sensor reads can take 2-5 seconds and may require retries
- Display needs to update the clock every second for smooth time display
- Separating concerns prevents sensor delays from affecting the display

---

## Project Structure

```
smartTemHumSensor/
│
├── main.py                 # Application entry point
├── requirements.in         # Direct dependencies
├── requirements.txt        # Compiled dependencies (pip-compile)
│
├── config/
│   ├── __init__.py
│   └── settings.py         # Configuration constants
│
├── sensors/
│   ├── __init__.py
│   └── dht22_sensor.py     # DHT22 sensor interface
│
├── display/
│   ├── __init__.py
│   └── oled_display.py     # OLED display controller
│
├── storage/
│   └── data_logger.py      # CSV data logging
│
├── stats/
│   └── daily_stats.py      # Daily statistics calculator
│
└── data/
    └── YYYY-MM-DD.csv      # Daily data files (auto-generated)
```

---

## Module Documentation

### main.py

The application entry point that orchestrates all components.

**Key Functions:**

| Function | Description |
|----------|-------------|
| `sensor_worker(shared_data)` | Background thread that reads sensor, logs data, and updates shared state every 10 seconds |
| `main()` | Initializes display, starts sensor thread, and runs the display update loop (1 second interval) |

**Shared Data Structure:**
```python
shared_data = {
    "temperature": float,  # Current temperature in °C
    "humidity": float,     # Current humidity in %
    "stats": dict          # Daily min/max statistics
}
```

---

### config/settings.py

Central configuration file for all adjustable parameters.

| Constant | Default | Description |
|----------|---------|-------------|
| `OLED_WIDTH` | 128 | OLED display width in pixels |
| `OLED_HEIGHT` | 64 | OLED display height in pixels |
| `OLED_ADDRESS` | 0x3C | I2C address of the OLED display |
| `REFRESH_SECONDS` | 10 | Sensor reading interval in seconds |
| `DATA_DIRECTORY` | "data" | Directory for storing CSV log files |

---

### sensors/dht22_sensor.py

Handles communication with the DHT22 temperature/humidity sensor.

**Class: `DHT22Sensor`**

| Method | Description |
|--------|-------------|
| `__init__()` | Initializes sensor on GPIO4, waits 3 seconds for warm-up |
| `read()` | Attempts to read temperature/humidity with up to 5 retries, returns `dict` or `None` |

**Return Format:**
```python
{
    "temperature": 25.3,  # Celsius, rounded to 1 decimal
    "humidity": 65.2      # Percentage, rounded to 1 decimal
}
```

**Error Handling:**
- Automatically retries up to 5 times on `RuntimeError` (common with DHT sensors)
- Returns `None` if all attempts fail
- Logs unexpected errors to console

---

### display/oled_display.py

Controls the SSD1306 OLED display using PIL for image rendering.

**Class: `OLEDDisplay`**

| Method | Description |
|--------|-------------|
| `__init__(rotate=True)` | Initializes I2C display, loads fonts, supports 180° rotation |
| `clear()` | Clears the display |
| `show_data(temperature, humidity, stats=None)` | Renders complete display with all data |

**Display Layout (128x64 pixels):**
```
┌────────────────────────────────────┐
│ 02:30:45 PM              15-May   │ ← Header (time + date)
├────────────────────────────────────┤
│                                    │
│            25.3°C                  │ ← Temperature (large font)
│            65.2%                   │ ← Humidity (large font)
│                                    │
├────────────────────────────────────┤
│ T↑26.5↓23.1    H↑70↓58            │ ← Daily min/max stats
└────────────────────────────────────┘
```

**Features:**
- Automatic font fallback if DejaVu fonts are unavailable
- Text centering and right-alignment utilities
- Optional 180° rotation for mounting flexibility

---

### storage/data_logger.py

Handles persistent storage of sensor readings in CSV format.

**Class: `DataLogger`**

| Method | Description |
|--------|-------------|
| `__init__()` | Creates data directory if it doesn't exist |
| `_get_filename()` | Generates filename based on current date (`YYYY-MM-DD.csv`) |
| `log(temperature, humidity)` | Appends a timestamped reading to today's CSV file |

**CSV Format:**
```csv
timestamp,temperature,humidity
2026-05-15 14:30:45,25.32,65.18
2026-05-15 14:30:55,25.35,65.21
```

**Features:**
- Auto-creates header row for new files
- Appends to existing files
- Values rounded to 2 decimal places

---

### stats/daily_stats.py

Calculates daily min/max statistics from logged data.

**Class: `DailyStats`**

| Method | Description |
|--------|-------------|
| `__init__()` | Creates data directory if it doesn't exist |
| `_get_filename()` | Gets today's data file path |
| `get_stats()` | Reads today's CSV and calculates min/max values |

**Return Format:**
```python
{
    "temp_min": 23.1,   # Lowest temperature today
    "temp_max": 26.5,   # Highest temperature today
    "hum_min": 58.0,    # Lowest humidity today
    "hum_max": 70.0     # Highest humidity today
}
```

Returns `None` if no data file exists or file is empty.

---

## Installation

### 1. Enable I2C on Raspberry Pi

```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
sudo reboot
```

### 2. Clone the Repository

```bash
git clone <repository-url>
cd smartTemHumSensor
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
| Package | Purpose |
|---------|---------|
| `adafruit-blinka` | CircuitPython compatibility layer for Raspberry Pi |
| `adafruit-circuitpython-dht` | DHT22 sensor driver |
| `adafruit-circuitpython-ssd1306` | SSD1306 OLED driver |
| `pillow` | Image manipulation for display rendering |
| `RPi.GPIO` | Raspberry Pi GPIO access |

---

## Configuration

Edit `config/settings.py` to customize:

```python
# Display settings
OLED_WIDTH = 128          # Don't change unless using different display
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C       # Use 'i2cdetect -y 1' to verify

# Sensor settings
REFRESH_SECONDS = 10      # How often to read the sensor (seconds)

# Storage settings
DATA_DIRECTORY = "data"   # Where to store CSV files
```

---

## Usage

### Running the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python main.py
```

### Running at Boot (Systemd Service)

Create `/etc/systemd/system/temphum.service`:

```ini
[Unit]
Description=Temperature Humidity Monitor
After=multi-user.target

[Service]
Type=simple
ExecStart=/home/pi/smartTemHumSensor/venv/bin/python /home/pi/smartTemHumSensor/main.py
WorkingDirectory=/home/pi/smartTemHumSensor
User=pi
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable temphum.service
sudo systemctl start temphum.service
```

---

## Data Storage

### File Location
Data files are stored in the `data/` directory with the naming format `YYYY-MM-DD.csv`.

### Example Data
```csv
timestamp,temperature,humidity
2026-05-15 00:00:10,22.50,58.30
2026-05-15 00:00:20,22.48,58.35
2026-05-15 00:00:30,22.51,58.28
```

### Accessing Historical Data
Each day creates a new file, making it easy to:
- Archive historical data
- Analyze trends over time
- Import into spreadsheet applications
- Process with data analysis tools (pandas, etc.)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `I2C Error` | Run `i2cdetect -y 1` to verify OLED is detected at 0x3C |
| `Sensor read failures` | Check DHT22 wiring, ensure pull-up resistor on data line |
| `Display upside down` | Set `rotate=False` in OLEDDisplay initialization |
| `Permission denied` | Run with `sudo` or add user to `gpio` and `i2c` groups |

---

## License

This project is provided as-is for educational purposes.
