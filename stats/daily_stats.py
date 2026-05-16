import csv
import os

from datetime import datetime

from config.settings import DATA_DIRECTORY


class DailyStats:
    def __init__(self):
        os.makedirs(DATA_DIRECTORY, exist_ok=True)

    def _get_filename(self):
        date_string = datetime.now().strftime(
            "%Y-%m-%d"
        )

        return os.path.join(
            DATA_DIRECTORY,
            f"{date_string}.csv"
        )

    def get_stats(self):
        filename = self._get_filename()

        if not os.path.exists(filename):
            return None

        temperatures = []
        humidities = []

        try:
            with open(filename, "r") as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        temperatures.append(
                            float(row["temperature"])
                        )

                        humidities.append(
                            float(row["humidity"])
                        )
                    except (ValueError, KeyError):
                        # Skip rows with invalid or missing data
                        continue

            if not temperatures:
                return None

            return {
                "temp_min": min(temperatures),
                "temp_max": max(temperatures),
                "hum_min": min(humidities),
                "hum_max": max(humidities)
            }
        
        except Exception as e:
            # Log error but don't crash - return None
            print(f"Error reading stats: {e}")
            return None