# -*- coding: utf-8 -*-

from datetime import datetime
import time

import board
import adafruit_ssd1306

from PIL import (
    Image,
    ImageDraw,
    ImageFont
)

from config.settings import (
    OLED_WIDTH,
    OLED_HEIGHT,
    OLED_ADDRESS
)


class OLEDDisplay:
    """
    Clean OLED display controller for SSD1306.
    Optimized for readability on 128x64 displays.
    """

    MIN_UPDATE_INTERVAL = 0.5
    BURN_IN_SHIFT_INTERVAL = 300

    def __init__(self, rotate=True):

        i2c = board.I2C()

        self.oled = adafruit_ssd1306.SSD1306_I2C(
            OLED_WIDTH,
            OLED_HEIGHT,
            i2c,
            addr=OLED_ADDRESS
        )

        self.rotate = rotate

        self.image = Image.new(
            "1",
            (OLED_WIDTH, OLED_HEIGHT)
        )

        self.draw = ImageDraw.Draw(self.image)

        self.last_update_time = 0

        self.current_page = 0
        self.total_pages = 5

        self.pixel_shift = 0
        self.last_shift_time = time.time()

        self._text_width_cache = {}

        self._load_fonts()

        self.clear()

    # =====================================================
    # FONT LOADING
    # =====================================================

    def _load_fonts(self):

        font_path = "/usr/share/fonts/truetype/dejavu/"

        try:
            self.large_font = ImageFont.truetype(
                f"{font_path}DejaVuSans-Bold.ttf",
                18
            )

            self.medium_font = ImageFont.truetype(
                f"{font_path}DejaVuSans.ttf",
                12
            )

            self.small_font = ImageFont.truetype(
                f"{font_path}DejaVuSans.ttf",
                9
            )

        except Exception:

            self.large_font = ImageFont.load_default()
            self.medium_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()

    # =====================================================
    # CORE METHODS
    # =====================================================

    def clear(self):

        self.oled.fill(0)
        self.oled.show()

    def _clear_canvas(self):

        self.draw.rectangle(
            (0, 0, OLED_WIDTH, OLED_HEIGHT),
            fill=0
        )

    def _update_display(self):

        if self.rotate:
            output = self.image.rotate(180)
        else:
            output = self.image

        self.oled.image(output)
        self.oled.show()

    # =====================================================
    # UTILITIES
    # =====================================================

    def _get_text_width(self, text, font):

        cache_key = (text, id(font))

        if cache_key in self._text_width_cache:
            return self._text_width_cache[cache_key]

        bbox = self.draw.textbbox(
            (0, 0),
            text,
            font=font
        )

        width = bbox[2] - bbox[0]

        self._text_width_cache[cache_key] = width

        return width

    def _draw_centered_text(self, text, y, font):

        width = self._get_text_width(text, font)

        x = (OLED_WIDTH - width) // 2

        self.draw.text(
            (x + self.pixel_shift, y),
            text,
            font=font,
            fill=255
        )

    def _draw_right_text(
        self,
        text,
        y,
        font,
        padding=2
    ):

        width = self._get_text_width(text, font)

        x = OLED_WIDTH - width - padding

        self.draw.text(
            (x + self.pixel_shift, y),
            text,
            font=font,
            fill=255
        )

    def _wrap_text(self, text, max_width, font):

        words = text.split()

        lines = []
        current = []

        for word in words:

            test = " ".join(current + [word])

            if self._get_text_width(test, font) <= max_width:
                current.append(word)

            else:
                if current:
                    lines.append(" ".join(current))

                current = [word]

        if current:
            lines.append(" ".join(current))

        return lines

    # =====================================================
    # OLED BURN-IN PROTECTION
    # =====================================================

    def _update_burn_in_protection(self):

        now = time.time()

        if (
            now - self.last_shift_time
            > self.BURN_IN_SHIFT_INTERVAL
        ):

            self.pixel_shift = (
                0 if self.pixel_shift else 1
            )

            self.last_shift_time = now

    # =====================================================
    # HEADER
    # =====================================================

    def _draw_header(self, title=""):

        now = datetime.now()

        time_text = now.strftime("%I:%M %p")

        self.draw.text(
            (2 + self.pixel_shift, 0),
            time_text,
            font=self.small_font,
            fill=255
        )

        if title:
            self._draw_right_text(
                title,
                0,
                self.small_font
            )

    # =====================================================
    # PAGE: CURRENT
    # =====================================================

    def _draw_page_current(
        self,
        temperature,
        humidity,
        stats
    ):

        temp_text = f"{temperature:.1f}°C"

        self._draw_centered_text(
            temp_text,
            14,
            self.large_font
        )

        hum_text = f"{humidity:.0f}% RH"

        self._draw_centered_text(
            hum_text,
            40,
            self.medium_font
        )

        if stats:

            low_text = (
                f"L:{stats['temp_min']:.1f}"
            )

            high_text = (
                f"H:{stats['temp_max']:.1f}"
            )

            self.draw.text(
                (4 + self.pixel_shift, 54),
                low_text,
                font=self.small_font,
                fill=255
            )

            self._draw_right_text(
                high_text,
                54,
                self.small_font,
                padding=4
            )

    # =====================================================
    # PAGE: COMFORT
    # =====================================================

    def _draw_page_comfort(
        self,
        temperature,
        comfort_metrics
    ):

        if not comfort_metrics:

            self._draw_centered_text(
                "No Data",
                28,
                self.large_font
            )

            return

        comfort = comfort_metrics.get(
            "comfort_zone",
            "Normal"
        )

        self._draw_centered_text(
            comfort,
            14,
            self.medium_font
        )

        heat_index = comfort_metrics.get(
            "heat_index",
            temperature
        )

        self._draw_centered_text(
            f"Feels {heat_index:.1f}°C",
            32,
            self.medium_font
        )

        dew = comfort_metrics.get(
            "dew_point",
            0
        )

        self._draw_centered_text(
            f"Dew {dew:.1f}°C",
            50,
            self.small_font
        )

    # =====================================================
    # PAGE: TRENDS
    # =====================================================

    def _draw_page_trends(self, historical_data):

        if not historical_data:

            self._draw_centered_text(
                "No Data",
                28,
                self.medium_font
            )

            return

        temp_data = historical_data.get('temperature', [])
        hum_data = historical_data.get('humidity', [])

        if not temp_data or not hum_data:

            self._draw_centered_text(
                "No Data",
                28,
                self.medium_font
            )

            return

        # Temperature label
        self.draw.text(
            (2 + self.pixel_shift, 12),
            "Temp",
            font=self.small_font,
            fill=255
        )

        # Draw temperature trend line
        self._draw_trend_line(
            temp_data,
            y_start=12,
            height=18,
            x_offset=30
        )

        # Humidity label
        self.draw.text(
            (2 + self.pixel_shift, 38),
            "Hum",
            font=self.small_font,
            fill=255
        )

        # Draw humidity trend line
        self._draw_trend_line(
            hum_data,
            y_start=38,
            height=18,
            x_offset=30
        )

    def _draw_trend_line(self, data, y_start, height, x_offset):
        """
        Draw a trend line graph for the given data.
        """
        if not data or len(data) < 2:
            return

        # Available width for graph
        graph_width = OLED_WIDTH - x_offset - 4

        # Normalize data to fit in the height
        min_val = min(data)
        max_val = max(data)
        
        if max_val == min_val:
            # Flat line if no variation
            y = y_start + height // 2
            self.draw.line(
                [
                    (x_offset + self.pixel_shift, y),
                    (OLED_WIDTH - 4 + self.pixel_shift, y)
                ],
                fill=255,
                width=1
            )
            return

        # Sample data to fit graph width (max ~90 points)
        step = max(1, len(data) // graph_width)
        sampled = data[::step]

        # Calculate points
        points = []
        for i, value in enumerate(sampled):
            x = x_offset + (i * graph_width // (len(sampled) - 1))
            # Invert y because screen coordinates go down
            normalized = (value - min_val) / (max_val - min_val)
            y = y_start + height - int(normalized * height)
            points.append((x + self.pixel_shift, y))

        # Draw line connecting points
        if len(points) > 1:
            self.draw.line(points, fill=255, width=1)

        # Draw current value
        current_val = data[-1]
        val_text = f"{current_val:.1f}"
        self._draw_right_text(
            val_text,
            y_start + height + 2,
            self.small_font,
            padding=2
        )

    # =====================================================
    # PAGE: STATS
    # =====================================================

    def _draw_page_stats(self, stats):

        if not stats:

            self._draw_centered_text(
                "No Stats",
                28,
                self.large_font
            )

            return

        self.draw.text(
            (4 + self.pixel_shift, 14),
            "Temperature",
            font=self.small_font,
            fill=255
        )

        temp_range = (
            f"{stats['temp_min']:.1f}"
            f" - "
            f"{stats['temp_max']:.1f}°C"
        )

        self._draw_centered_text(
            temp_range,
            24,
            self.medium_font
        )

        self.draw.text(
            (4 + self.pixel_shift, 42),
            "Humidity",
            font=self.small_font,
            fill=255
        )

        hum_range = (
            f"{stats['hum_min']:.0f}"
            f" - "
            f"{stats['hum_max']:.0f}%"
        )

        self._draw_centered_text(
            hum_range,
            52,
            self.medium_font
        )

    # =====================================================
    # PAGE: NOTES
    # =====================================================

    def _draw_page_notes(self, notes):

        if not notes:
            notes = "Smart Sensor"

        lines = self._wrap_text(
            notes,
            120,
            self.small_font
        )

        y = 16

        for line in lines[:4]:

            self._draw_centered_text(
                line,
                y,
                self.small_font
            )

            y += 11

    # =====================================================
    # ERROR PAGE
    # =====================================================

    def _draw_error_page(self, message):

        self._draw_centered_text(
            "ERROR",
            18,
            self.medium_font
        )

        self._draw_centered_text(
            message,
            38,
            self.small_font
        )

    # =====================================================
    # PAGE CONTROL
    # =====================================================

    def next_page(self):

        self.current_page = (
            (self.current_page + 1)
            % self.total_pages
        )

    def set_page(self, page):

        if 0 <= page < self.total_pages:
            self.current_page = page

    # =====================================================
    # MAIN RENDER METHOD
    # =====================================================

    def show_data(
        self,
        temperature,
        humidity,
        stats=None,
        comfort_metrics=None,
        historical_data=None,
        notes="Smart Sensor",
        page=None,
        force=False
    ):

        now = time.time()

        if (
            not force
            and
            (
                now - self.last_update_time
                < self.MIN_UPDATE_INTERVAL
            )
        ):
            return

        self.last_update_time = now

        self._update_burn_in_protection()

        if page is None:
            page = self.current_page

        self._clear_canvas()

        page_titles = {
            0: "Current",
            1: "Comfort",
            2: "Trends",
            3: "Stats",
            4: "Notes"
        }

        self._draw_header(
            page_titles.get(page, "")
        )

        try:

            if page == 0:

                self._draw_page_current(
                    temperature,
                    humidity,
                    stats
                )

            elif page == 1:

                self._draw_page_comfort(
                    temperature,
                    comfort_metrics
                )

            elif page == 2:

                self._draw_page_trends(
                    historical_data
                )

            elif page == 3:

                self._draw_page_stats(
                    stats
                )

            elif page == 4:

                self._draw_page_notes(
                    notes
                )

            else:

                self._draw_error_page(
                    "Invalid Page"
                )

        except Exception as error:

            self._clear_canvas()

            self._draw_error_page(
                str(error)[:18]
            )

        self._update_display()