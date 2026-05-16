import csv
import os

from datetime import datetime

from config.settings import DATA_DIRECTORY


class DataLogger:
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

    def log(self, temperature, humidity, heat_index=None, dew_point=None, comfort_zone=None):
        """Log sensor data to CSV file with optional comfort metrics."""
        filename = self._get_filename()

        file_exists = os.path.isfile(filename)

        with open(
            filename,
            "a",
            newline=""
        ) as csvfile:

            writer = csv.writer(csvfile)

            if not file_exists:
                # Extended header with comfort metrics
                writer.writerow([
                    "timestamp",
                    "temperature",
                    "humidity",
                    "heat_index",
                    "dew_point",
                    "comfort_zone"
                ])

            writer.writerow([
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                round(temperature, 2),
                round(humidity, 2),
                round(heat_index, 2) if heat_index is not None else "",
                round(dew_point, 2) if dew_point is not None else "",
                comfort_zone if comfort_zone is not None else ""
            ])