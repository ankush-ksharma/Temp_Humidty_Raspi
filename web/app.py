"""
Flask web application for environmental monitoring dashboard.

Provides REST API endpoints and web interface for viewing
real-time sensor data and historical trends.
"""

import os
import csv
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

from config.settings import DATA_DIRECTORY

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-in-production'

# Global reference to shared data (set by start_web_server)
_shared_data = None


def set_shared_data(shared_data):
    """Set reference to shared sensor data."""
    global _shared_data
    _shared_data = shared_data


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/history')
def history():
    """Historical data page with charts."""
    return render_template('history.html')


@app.route('/api/docs')
def api_docs():
    """API documentation page."""
    return render_template('api_docs.html')


@app.route('/notes', methods=['GET'])
def notes():
    """Custom notes page."""
    notes_text = _load_notes()
    return render_template('notes.html', notes=notes_text)


@app.route('/notes/save', methods=['POST'])
def save_notes():
    """Save custom notes."""
    from flask import request
    
    notes_text = request.form.get('notes', '')
    
    try:
        _save_notes(notes_text)
        return jsonify({'success': True, 'message': 'Notes saved successfully'})
    except Exception as e:
        logger.error(f"Error saving notes: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def _load_notes():
    """Load custom notes from file."""
    notes_file = os.path.join('data', 'custom_notes.txt')
    
    if os.path.exists(notes_file):
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading notes: {e}")
            return ''
    
    return ''


def _save_notes(notes_text):
    """Save custom notes to file."""
    notes_file = os.path.join('data', 'custom_notes.txt')
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    with open(notes_file, 'w', encoding='utf-8') as f:
        f.write(notes_text)


@app.route('/api/current')
def api_current():
    """
    Get current sensor readings.
    
    Returns:
        JSON with temperature, humidity, comfort metrics, stats
    """
    if _shared_data is None:
        return jsonify({'error': 'Sensor data not available'}), 503
    
    data = _shared_data.get()
    
    response = {
        'timestamp': data['last_update'].isoformat() if data['last_update'] else None,
        'temperature': data['temperature'],
        'humidity': data['humidity'],
        'sensor_healthy': data['sensor_healthy'],
        'stats': data['stats'],
        'comfort_metrics': data['comfort_metrics']
    }
    
    return jsonify(response)


@app.route('/api/history')
def api_history():
    """
    Get historical sensor data from CSV files.
    
    Query parameters:
        date: YYYY-MM-DD (default: today)
        limit: Maximum number of records (default: all)
    
    Returns:
        JSON array of readings
    """
    # Get date parameter or default to today
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    limit = request.args.get('limit', type=int)
    
    try:
        # Validate date format
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    filename = os.path.join(DATA_DIRECTORY, f"{date_str}.csv")
    
    if not os.path.exists(filename):
        return jsonify({'error': f'No data available for {date_str}'}), 404
    
    try:
        readings = []
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert to proper types
                reading = {
                    'timestamp': row['timestamp'],
                    'temperature': float(row['temperature']),
                    'humidity': float(row['humidity'])
                }
                
                # Add comfort metrics if available
                if 'heat_index' in row and row['heat_index']:
                    reading['heat_index'] = float(row['heat_index'])
                if 'dew_point' in row and row['dew_point']:
                    reading['dew_point'] = float(row['dew_point'])
                if 'comfort_zone' in row and row['comfort_zone']:
                    reading['comfort_zone'] = row['comfort_zone']
                
                readings.append(reading)
        
        # Apply limit if specified
        if limit and limit > 0:
            readings = readings[-limit:]
        
        return jsonify({
            'date': date_str,
            'count': len(readings),
            'readings': readings
        })
    
    except Exception as e:
        logger.error(f"Error reading CSV: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/summary')
def api_summary():
    """
    Get summary statistics for a date range.
    
    Query parameters:
        start: Start date YYYY-MM-DD (default: 7 days ago)
        end: End date YYYY-MM-DD (default: today)
    
    Returns:
        JSON with daily summaries
    """
    # Default to last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Parse query parameters
    start_str = request.args.get('start', start_date.strftime('%Y-%m-%d'))
    end_str = request.args.get('end', end_date.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    if start_date > end_date:
        return jsonify({'error': 'Start date must be before end date'}), 400
    
    summaries = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        filename = os.path.join(DATA_DIRECTORY, f"{date_str}.csv")
        
        if os.path.exists(filename):
            try:
                temps = []
                hums = []
                
                with open(filename, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        temps.append(float(row['temperature']))
                        hums.append(float(row['humidity']))
                
                if temps and hums:
                    summary = {
                        'date': date_str,
                        'temp_min': min(temps),
                        'temp_max': max(temps),
                        'temp_avg': sum(temps) / len(temps),
                        'hum_min': min(hums),
                        'hum_max': max(hums),
                        'hum_avg': sum(hums) / len(hums),
                        'readings_count': len(temps)
                    }
                    summaries.append(summary)
            
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
        
        current_date += timedelta(days=1)
    
    return jsonify({
        'start_date': start_str,
        'end_date': end_str,
        'summaries': summaries
    })


@app.route('/api/available-dates')
def api_available_dates():
    """
    Get list of dates where data is available.
    
    Returns:
        JSON with array of available dates (YYYY-MM-DD format)
    """
    try:
        available_dates = []
        
        # Ensure data directory exists
        if not os.path.exists(DATA_DIRECTORY):
            return jsonify({'dates': []})
        
        # List all CSV files in data directory
        for filename in os.listdir(DATA_DIRECTORY):
            if filename.endswith('.csv') and not filename.startswith('.'):
                # Extract date from filename (YYYY-MM-DD.csv)
                date_str = filename[:-4]  # Remove .csv extension
                try:
                    # Validate it's a proper date
                    datetime.strptime(date_str, '%Y-%m-%d')
                    available_dates.append(date_str)
                except ValueError:
                    continue
        
        # Sort dates in descending order (most recent first)
        available_dates.sort(reverse=True)
        
        return jsonify({
            'dates': available_dates,
            'count': len(available_dates)
        })
    
    except Exception as e:
        logger.error(f"Error getting available dates: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/health')
def api_health():
    """
    Health check endpoint.
    
    Returns:
        JSON with system health status
    """
    if _shared_data is None:
        return jsonify({
            'status': 'unhealthy',
            'message': 'Sensor data not initialized'
        }), 503
    
    data = _shared_data.get()
    
    # Check if sensor is healthy and data is recent
    is_healthy = data['sensor_healthy']
    
    if data['last_update']:
        time_since_update = (datetime.now() - data['last_update']).total_seconds()
        is_healthy = is_healthy and time_since_update < 60  # Data within last minute
    else:
        is_healthy = False
    
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'sensor_healthy': data['sensor_healthy'],
        'last_update': data['last_update'].isoformat() if data['last_update'] else None,
        'data_available': data['temperature'] is not None
    })


def start_web_server(shared_data, host='0.0.0.0', port=5000):
    """
    Start Flask web server in current thread.
    
    Args:
        shared_data: SharedData instance
        host: Host to bind to (default: 0.0.0.0 for all interfaces)
        port: Port to listen on (default: 5000)
    """
    set_shared_data(shared_data)
    logger.info(f"Starting web server on {host}:{port}")
    
    # Run Flask app
    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,  # Important for threading
        threaded=True
    )
