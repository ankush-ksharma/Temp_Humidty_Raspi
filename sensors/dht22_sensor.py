import time
from pigpio_dht import DHT22

class DHT22Sensor:
    def __init__(self, gpio_pin=4):
        self.pin = gpio_pin
        print(f"Initializing DHT22 sensor on GPIO Pin {self.pin}...")
        self.sensor = DHT22(self.pin)
        time.sleep(2.5)  # Initial physical sensor warm-up pause

    def read(self):
        """
        Takes multiple readings from the sensor and returns a normalized result.
        """
        try:
            result = self.sensor.sample(samples=5)
            
            if result and result.get('valid') is True:
                temperature = result.get('temp_c')
                humidity = result.get('humidity')
                
                # Final validation filtering
                if (-40 <= temperature <= 80) and (0 <= humidity <= 100):
                    return {
                        "temperature": round(float(temperature), 1),
                        "humidity": round(float(humidity), 1),
                        "status": "ok"
                    }
        except Exception as e:
            print(f"Error reading sensor: {e}")
        
        return None


if __name__ == "__main__":
    # Point this to BCM pin 4 (Physical Pin 7 on the board)
    sensor = DHT22Sensor(gpio_pin=4)

    print("\nLive Monitoring Stream Online (Press Ctrl+C to exit)...")
    while True:
        data = sensor.read()
        if data:
            print(
                f"[{data['status'].upper()}] "
                f"Temp: {data['temperature']}°C | "
                f"Humidity: {data['humidity']}%"
            )
        else:
            print("[ERROR] Sensor communication failed.")
            
        # Take one reading per minute
        time.sleep(50)
