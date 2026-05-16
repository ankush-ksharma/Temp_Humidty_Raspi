import time
import threading
import logging
from datetime import datetime

from sensors.dht22_sensor import DHT22SensorProduction as DHT22Sensor
from display.oled_display import OLEDDisplay
from storage.data_logger import DataLogger
from stats.daily_stats import DailyStats
from calculations.comfort_metrics import get_comfort_metrics
from web.app import start_web_server

from config.settings import (
    REFRESH_SECONDS,
    DISPLAY_PAGE_ROTATION_ENABLED,
    DISPLAY_PAGE_ROTATION_INTERVAL,
    DISPLAY_TOTAL_PAGES,
    WEB_SERVER_ENABLED,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
    DATA_DIRECTORY
)

import os
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SharedData:
    """Thread-safe container for sensor data."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "temperature": None,
            "humidity": None,
            "stats": None,
            "comfort_metrics": None,
            "last_update": None,
            "sensor_healthy": True
        }
        self.health_event = threading.Event()
        self.health_event.set()  # Start healthy
    
    def update(self, temperature, humidity, stats, comfort_metrics=None):
        """Thread-safe update of all sensor data."""
        with self._lock:
            self._data["temperature"] = temperature
            self._data["humidity"] = humidity
            self._data["stats"] = stats
            self._data["comfort_metrics"] = comfort_metrics
            self._data["last_update"] = datetime.now()
            self._data["sensor_healthy"] = True
            self.health_event.set()
    
    def get(self):
        """Thread-safe retrieval of sensor data."""
        with self._lock:
            return self._data.copy()
    
    def mark_unhealthy(self):
        """Mark sensor as unhealthy."""
        with self._lock:
            self._data["sensor_healthy"] = False
            self.health_event.clear()


def sensor_worker(shared_data):
    """Background thread that reads sensor and logs data."""
    sensor = DHT22Sensor()
    logger_inst = DataLogger()
    stats_manager = DailyStats()
    
    consecutive_failures = 0
    max_failures = 3

    while True:
        try:
            data = sensor.read()

            if data:
                temperature = data["temperature"]
                humidity = data["humidity"]

                # Calculate comfort metrics
                comfort_metrics = get_comfort_metrics(temperature, humidity)
                
                # Log data with comfort metrics
                logger_inst.log(
                    temperature, 
                    humidity,
                    comfort_metrics['heat_index'],
                    comfort_metrics['dew_point'],
                    comfort_metrics['comfort_zone']
                )
                
                stats = stats_manager.get_stats()

                shared_data.update(temperature, humidity, stats, comfort_metrics)
                consecutive_failures = 0  # Reset failure counter

                logger.info(
                    f"Temp: {temperature:.1f}°C | Humidity: {humidity:.1f}% | "
                    f"Feels: {comfort_metrics['heat_index']:.1f}°C | {comfort_metrics['comfort_zone']}"
                )
            else:
                consecutive_failures += 1
                logger.warning(f"Sensor read failed (attempt {consecutive_failures}/{max_failures})")
                
                if consecutive_failures >= max_failures:
                    shared_data.mark_unhealthy()
                    logger.error("Sensor marked unhealthy after consecutive failures")
        
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Sensor worker error: {e}", exc_info=True)
            
            if consecutive_failures >= max_failures:
                shared_data.mark_unhealthy()

        time.sleep(REFRESH_SECONDS)


def load_notes():
    """Load custom notes from file."""
    notes_file = os.path.join(DATA_DIRECTORY, 'custom_notes.txt')
    
    if os.path.exists(notes_file):
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return content if content else 'Smart Sensors'
        except Exception as e:
            logger.error(f"Error loading notes: {e}")
            return 'Smart Sensors'
    
    return 'Smart Sensors'


def get_recent_history(hours=24, max_points=50):
    """
    Load recent temperature and humidity data from today's CSV.
    
    Args:
        hours: Number of hours to load (default: 24)
        max_points: Maximum number of data points to return
    
    Returns:
        dict with 'temperature' and 'humidity' lists, or None
    """
    try:
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join(DATA_DIRECTORY, f"{date_str}.csv")
        
        if not os.path.exists(filename):
            return None
        
        temp_data = []
        hum_data = []
        
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    temp_data.append(float(row['temperature']))
                    hum_data.append(float(row['humidity']))
                except (ValueError, KeyError):
                    continue
        
        # Limit to max_points by sampling evenly
        if len(temp_data) > max_points:
            step = len(temp_data) // max_points
            temp_data = temp_data[::step][:max_points]
            hum_data = hum_data[::step][:max_points]
        
        if temp_data and hum_data:
            return {
                'temperature': temp_data,
                'humidity': hum_data
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return None


def main():
    """Main application entry point."""
    logger.info("Starting Smart Temperature & Humidity Monitor")
    
    display = OLEDDisplay()

    # Thread-safe shared data container
    shared_data = SharedData()

    # Start sensor thread
    sensor_thread = threading.Thread(target=sensor_worker, args=(shared_data,), name="SensorWorker")
    sensor_thread.daemon = True
    sensor_thread.start()
    logger.info("Sensor worker thread started")

    # Start web server thread if enabled
    if WEB_SERVER_ENABLED:
        web_thread = threading.Thread(
            target=start_web_server,
            args=(shared_data, WEB_SERVER_HOST, WEB_SERVER_PORT),
            name="WebServer"
        )
        web_thread.daemon = True
        web_thread.start()
        logger.info(f"Web server started on http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")

    # Page rotation state
    current_page = 0
    last_page_change = time.time()
    
    # Historical data cache (refresh every 60 seconds)
    historical_data = None
    last_history_update = 0
    
    # Notes cache (refresh every 30 seconds)
    notes_text = load_notes()
    last_notes_update = time.time()

    # Main loop: handles display updates
    while True:
        try:
            data = shared_data.get()
            
            # Handle page rotation
            if DISPLAY_PAGE_ROTATION_ENABLED:
                if time.time() - last_page_change >= DISPLAY_PAGE_ROTATION_INTERVAL:
                    current_page = (current_page + 1) % DISPLAY_TOTAL_PAGES
                    last_page_change = time.time()
                    logger.debug(f"Switched to page {current_page}")
            
            # Update historical data every 60 seconds (only when needed for page 2)
            if current_page == 2 and time.time() - last_history_update > 60:
                historical_data = get_recent_history()
                last_history_update = time.time()
            
            # Update notes every 30 seconds (only when needed for page 4)
            if current_page == 4 and time.time() - last_notes_update > 30:
                notes_text = load_notes()
                last_notes_update = time.time()
            
            if data["temperature"] is not None:
                display.show_data(
                    data["temperature"],
                    data["humidity"],
                    stats=data["stats"],
                    comfort_metrics=data["comfort_metrics"],
                    page=current_page,
                    historical_data=historical_data,
                    notes=notes_text
                )

            time.sleep(1)  # Clock updates every second
        
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            break
        
        except Exception as e:
            logger.error(f"Display error: {e}", exc_info=True)
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    main()