import time
import gpiod
from dht_gpiod import DHT22

class DHT22SensorGpiod:
    def __init__(
        self,
        pin=4,                # Broadcom (BCM) GPIO Pin number
        alpha_temp=0.4,       # Exponential filter smoothing factors
        alpha_humidity=0.4,
        max_retries=5         # Safe fallback retry allowance
    ):
        self.pin = pin
        self.alpha_temp = alpha_temp
        self.alpha_humidity = alpha_humidity
        self.max_retries = max_retries

        self.last_temp = None
        self.last_humidity = None
        self.last_read_time = 0.0

        print(f"Initializing native Linux gpiod backend on GPIO Pin {self.pin}...")
        
        # Open direct communication link via native Linux kernel channels
        self.sensor = DHT22(self.pin)
        time.sleep(2.5)  # Initial hardware stability warm-up string

        self._initialize_baseline()

    def _enforce_cooldown(self):
        """
        Guarantees the physical hardware has rested for at least 2.5 seconds 
        before starting a retry or new communication pulse.
        """
        elapsed = time.time() - self.last_read_time
        if elapsed < 2.5:
            time.sleep(2.5 - elapsed)

    def _raw_read(self):
        """
        Fetches fresh environmental readings directly from the GPIO line.
        """
        for _ in range(self.max_retries):
            self._enforce_cooldown()
            self.last_read_time = time.time()

            try:
                # Direct hardware read call
                temperature, humidity = self.sensor.read()

                if temperature is not None and humidity is not None:
                    # Filter out rogue electrical noise spikes
                    if (-40 <= temperature <= 80) and (0 <= humidity <= 100):
                        return {
                            "temperature": float(temperature),
                            "humidity": float(humidity)
                        }
            except Exception:
                # Handles transient OS multitasking bit-drops gracefully
                pass

        return None

    def _initialize_baseline(self):
        """
        Acquires the initial raw room environment baseline data 
        so the mathematical filters don't begin at 0.0.
        """
        print("Gathering live baseline environment tracking data...")
        for attempt in range(10):
            reading = self._raw_read()
            if reading is not None:
                self.last_temp = reading["temperature"]
                self.last_humidity = reading["humidity"]
                print(f"Baseline Confirmed: {self.last_temp:.1f}°C | {self.last_humidity:.1f}%")
                return
            print(f"Baseline attempt {attempt + 1}/10 dropped. Retrying...")
            
        raise RuntimeError("Fatal hardware block: Could not verify connection over gpiod framework.")

    def _ema(self, previous, new, alpha):
        if previous is None:
            return new
        return (alpha * new) + ((1 - alpha) * previous)

    def read(self):
        """
        Public API method to fetch and update the smoothed ambient data package.
        """
        reading = self._raw_read()

        if reading is None:
            if self.last_temp is not None and self.last_humidity is not None:
                return {
                    "temperature": round(self.last_temp, 1),
                    "humidity": round(self.last_humidity, 1),
                    "status": "cached"
                }
            return None

        # Process data through Exponential Moving Average smoothing calculations
        filtered_temp = self._ema(self.last_temp, reading["temperature"], self.alpha_temp)
        filtered_humidity = self._ema(self.last_humidity, reading["humidity"], self.alpha_humidity)

        # Update cache tracking properties
        self.last_temp = filtered_temp
        self.last_humidity = filtered_humidity

        return {
            "temperature": round(filtered_temp, 1),
            "humidity": round(filtered_humidity, 1),
            "status": "ok"
        }


if __name__ == "__main__":
    # Assumes your DHT22 module's Data pin is wired to BCM GPIO 4
    sensor = DHT22SensorGpiod(pin=4)

    print("\nLive Monitoring Stream Initialized (Press Ctrl+C to stop)...")
    while True:
        data = sensor.read()
        if data:
            print(
                f"[{data['status'].upper()}] "
                f"Temp: {data['temperature']}°C | "
                f"Humidity: {data['humidity']}%"
            )
        else:
            print("[CRITICAL] Pin reading timed out. Verify your physical wires.")
            
        # The 5-second main application polling delay
        time.sleep(5.0)
