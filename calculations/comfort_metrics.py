"""
Comfort metrics calculations for environmental monitoring.

Implements meteorological formulas for heat index, dew point,
and comfort zone classification based on ASHRAE standards.
"""

import math


def calculate_heat_index(temperature_c, humidity):
    """
    Calculate heat index (feels-like temperature) using NOAA formula.
    
    The heat index combines air temperature and relative humidity to determine
    the human-perceived equivalent temperature.
    
    Args:
        temperature_c: Temperature in Celsius
        humidity: Relative humidity as percentage (0-100)
    
    Returns:
        Heat index in Celsius (rounded to 1 decimal)
    
    Note:
        Formula is most accurate for temperatures above 27°C (80°F).
        Below this, returns actual temperature.
    """
    # Convert to Fahrenheit for the formula
    temperature_f = (temperature_c * 9/5) + 32
    
    # Heat index formula is only valid for temp >= 80°F
    if temperature_f < 80:
        return round(temperature_c, 1)
    
    # Rothfusz regression (NOAA formula)
    T = temperature_f
    RH = humidity
    
    HI = (-42.379 + 
          2.04901523 * T + 
          10.14333127 * RH - 
          0.22475541 * T * RH - 
          0.00683783 * T * T - 
          0.05481717 * RH * RH + 
          0.00122874 * T * T * RH + 
          0.00085282 * T * RH * RH - 
          0.00000199 * T * T * RH * RH)
    
    # Adjustments for specific conditions
    if RH < 13 and 80 <= T <= 112:
        adjustment = ((13 - RH) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
        HI -= adjustment
    elif RH > 85 and 80 <= T <= 87:
        adjustment = ((RH - 85) / 10) * ((87 - T) / 5)
        HI += adjustment
    
    # Convert back to Celsius
    heat_index_c = (HI - 32) * 5/9
    
    return round(heat_index_c, 1)


def calculate_dew_point(temperature_c, humidity):
    """
    Calculate dew point temperature using Magnus formula.
    
    Dew point is the temperature at which water vapor in the air
    begins to condense into liquid water (dew).
    
    Args:
        temperature_c: Temperature in Celsius
        humidity: Relative humidity as percentage (0-100)
    
    Returns:
        Dew point in Celsius (rounded to 1 decimal)
    
    Note:
        Valid for temperatures between -40°C and 50°C
    """
    # Magnus formula constants
    a = 17.27
    b = 237.7  # °C
    
    # Calculate alpha
    alpha = ((a * temperature_c) / (b + temperature_c)) + math.log(humidity / 100.0)
    
    # Calculate dew point
    dew_point = (b * alpha) / (a - alpha)
    
    return round(dew_point, 1)


def classify_comfort_zone(temperature_c, humidity, heat_index=None):
    """
    Classify environmental conditions into comfort zones.
    
    Based on ASHRAE (American Society of Heating, Refrigerating and 
    Air-Conditioning Engineers) comfort standards:
    - Comfortable: 20-26°C with 30-60% humidity
    - Hot: >26°C
    - Cold: <20°C
    - Humid: >60% humidity (regardless of temperature)
    - Dry: <30% humidity (regardless of temperature)
    
    Args:
        temperature_c: Temperature in Celsius
        humidity: Relative humidity as percentage (0-100)
        heat_index: Optional pre-calculated heat index (uses temperature if None)
    
    Returns:
        tuple: (zone_name, icon, description)
        
    Examples:
        >>> classify_comfort_zone(23, 45)
        ('Comfortable', '☀️', 'Ideal conditions')
        >>> classify_comfort_zone(28, 70)
        ('Hot & Humid', '🔥💧', 'Very uncomfortable')
    """
    feels_like = heat_index if heat_index is not None else temperature_c
    
    # Priority order: check extremes first
    
    # Very humid conditions
    if humidity > 70:
        if feels_like > 26:
            return ('Hot & Humid', '🔥💧', 'Very uncomfortable')
        elif feels_like < 20:
            return ('Cold & Humid', '❄️💧', 'Damp and cold')
        else:
            return ('Humid', '💧', 'Moisture level high')
    
    # Very dry conditions
    if humidity < 30:
        if feels_like > 26:
            return ('Hot & Dry', '🔥', 'Low humidity')
        elif feels_like < 20:
            return ('Cold & Dry', '❄️', 'Cold and dry')
        else:
            return ('Dry', '🏜️', 'Low humidity')
    
    # Moderate humidity (30-70%)
    if feels_like > 28:
        return ('Hot', '🔥', 'Too warm')
    elif feels_like > 26:
        return ('Warm', '🌡️', 'Slightly warm')
    elif feels_like < 18:
        return ('Cold', '❄️', 'Too cold')
    elif feels_like < 20:
        return ('Cool', '🌬️', 'Slightly cool')
    else:
        # Sweet spot: 20-26°C with 30-70% humidity
        return ('Comfortable', '☀️', 'Ideal conditions')


def get_comfort_metrics(temperature_c, humidity):
    """
    Calculate all comfort metrics in one call.
    
    Args:
        temperature_c: Temperature in Celsius
        humidity: Relative humidity as percentage (0-100)
    
    Returns:
        dict with keys:
            - heat_index: Heat index in Celsius
            - dew_point: Dew point in Celsius
            - comfort_zone: Zone name (str)
            - comfort_icon: Unicode icon (str)
            - comfort_description: Description (str)
    
    Example:
        >>> metrics = get_comfort_metrics(25.5, 55)
        >>> print(metrics['comfort_zone'])
        'Comfortable'
    """
    heat_index = calculate_heat_index(temperature_c, humidity)
    dew_point = calculate_dew_point(temperature_c, humidity)
    zone, icon, description = classify_comfort_zone(temperature_c, humidity, heat_index)
    
    return {
        'heat_index': heat_index,
        'dew_point': dew_point,
        'comfort_zone': zone,
        'comfort_icon': icon,
        'comfort_description': description
    }


def get_mold_risk(temperature_c, humidity, dew_point=None):
    """
    Assess mold growth risk based on temperature and humidity.
    
    Mold typically grows when:
    - Relative humidity > 60% for extended periods
    - Temperature between 15-30°C (optimal 20-25°C)
    - Dew point > 15°C indicates high moisture
    
    Args:
        temperature_c: Temperature in Celsius
        humidity: Relative humidity as percentage (0-100)
        dew_point: Optional pre-calculated dew point
    
    Returns:
        tuple: (risk_level, description)
        - risk_level: 'Low', 'Medium', 'High', 'Very High'
        - description: Explanation string
    """
    if dew_point is None:
        dew_point = calculate_dew_point(temperature_c, humidity)
    
    # Very High Risk
    if humidity > 70 and 20 <= temperature_c <= 25:
        return ('Very High', 'Optimal mold growth conditions')
    
    # High Risk
    if humidity > 65 and 15 <= temperature_c <= 30:
        return ('High', 'Favorable for mold growth')
    
    # Medium Risk
    if humidity > 60 or dew_point > 15:
        return ('Medium', 'Monitor closely')
    
    # Low Risk
    return ('Low', 'Conditions not favorable for mold')
