import time
import board
import adafruit_dht


class DHT22Sensor:
    def __init__(
        self,
        pin=board.D4,
        alpha_temp=0.2,
        alpha_humidity=0.2,
        max_retries=3
    ):
        self.sensor = adafruit_dht.DHT22(
            pin,
            use_pulseio=False
        )

        # Exponential Moving Average (EMA) smoothing factors
        # Lower = smoother but slower response
        self.alpha_temp = alpha_temp
        self.alpha_humidity = alpha_humidity

        self.max_retries = max_retries

        # Last filtered valid readings
        self.last_temp = None
        self.last_humidity = None

        # Sensor warm-up - DHT22 needs more time to stabilize
        print("Initializing DHT22 sensor...")
        time.sleep(3)

        # Initial baseline acquisition
        self._initialize_baseline()

    def _initialize_baseline(self):
        """
        Get the first valid reading so EMA has a baseline.
        """
        for attempt in range(15):  # Increased attempts
            try:
                reading = self._raw_read()

                if reading is not None:
                    self.last_temp = reading["temperature"]
                    self.last_humidity = reading["humidity"]

                    print(
                        f"✓ Baseline established: "
                        f"{self.last_temp:.1f}°C, "
                        f"{self.last_humidity:.1f}%"
                    )
                    return

                print(f"Baseline attempt {attempt + 1}/15 failed - no valid reading")
            except Exception as e:
                print(f"Baseline attempt {attempt + 1}/15 failed - {type(e).__name__}: {e}")
            
            # DHT22 requires minimum 2 seconds between reads, use 3 for safety
            time.sleep(3)

        # If we still can't get a reading, provide helpful error message
        raise RuntimeError(
            "Failed to initialize DHT22 sensor after 15 attempts. "
            "Check: 1) Sensor connections (VCC, GND, DATA to GPIO4), "
            "2) Pull-up resistor (4.7K-10K ohm), "
            "3) GPIO permissions, "
            "4) Sensor hardware"
        )

    def _raw_read(self):
        """
        Perform a single validated sensor read with retries.
        """
        for retry in range(self.max_retries):
            try:
                temperature = self.sensor.temperature
                humidity = self.sensor.humidity

                # Validate sensor returned data
                if temperature is None or humidity is None:
                    if retry == self.max_retries - 1:
                        print(f"  → Sensor returned None (retry {retry + 1}/{self.max_retries})")
                    time.sleep(0.5)  # Increased from 0.2s
                    continue

                # Hard sanity checks
                if not (-40 <= temperature <= 80):
                    print(f"  → Rejected invalid temperature: {temperature}°C")
                    time.sleep(0.5)
                    continue

                if not (0 <= humidity <= 100):
                    print(f"  → Rejected invalid humidity: {humidity}%")
                    time.sleep(0.5)
                    continue

                return {
                    "temperature": float(temperature),
                    "humidity": float(humidity)
                }

            except RuntimeError as e:
                # Common transient DHT errors (checksum, timeout)
                if retry == self.max_retries - 1:
                    print(f"  → DHT22 RuntimeError: {e}")
                time.sleep(0.5)

            except Exception as error:
                print(f"  → Unexpected sensor error: {type(error).__name__}: {error}")
                time.sleep(0.5)

        return None

    def _ema(self, previous, new, alpha):
        """
        Exponential Moving Average filter.
        """
        if previous is None:
            return new

        return (alpha * new) + ((1 - alpha) * previous)

    def read(self):
        """
        Public method to get filtered sensor readings.
        """
        reading = self._raw_read()

        # If sensor failed completely, return last known values
        if reading is None:
            if self.last_temp is not None and self.last_humidity is not None:
                return {
                    "temperature": round(self.last_temp, 1),
                    "humidity": round(self.last_humidity, 1),
                    "status": "cached"
                }

            return None

        # Apply EMA smoothing
        filtered_temp = self._ema(
            self.last_temp,
            reading["temperature"],
            self.alpha_temp
        )

        filtered_humidity = self._ema(
            self.last_humidity,
            reading["humidity"],
            self.alpha_humidity
        )

        # Update stored values
        self.last_temp = filtered_temp
        self.last_humidity = filtered_humidity

        return {
            "temperature": round(filtered_temp, 1),
            "humidity": round(filtered_humidity, 1),
            "status": "ok"
        }


if __name__ == "__main__":
    sensor = DHT22Sensor()

    while True:
        data = sensor.read()

        if data:
            print(
                f"Temperature: {data['temperature']}°C | "
                f"Humidity: {data['humidity']}% | "
                f"Status: {data['status']}"
            )
        else:
            print("Sensor read failed")

        # DHT22 maximum update rate ≈ once every 2 seconds
        time.sleep(2)