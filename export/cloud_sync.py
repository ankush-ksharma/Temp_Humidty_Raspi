"""
Cloud sync module for exporting environmental data.

Supports multiple export backends:
- Google Sheets
- SFTP/SCP backup
- REST API webhooks
- Local backup to USB/network drive
"""

import os
import csv
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import DATA_DIRECTORY

logger = logging.getLogger(__name__)


class DataExporter:
    """Base class for data exporters."""
    
    def __init__(self, enabled=True):
        self.enabled = enabled
    
    def export(self, date=None):
        """
        Export data for a specific date.
        
        Args:
            date: Date to export (default: yesterday)
        
        Returns:
            bool: Success status
        """
        if not self.enabled:
            logger.info(f"{self.__class__.__name__} is disabled")
            return False
        
        if date is None:
            # Default to yesterday (today's file may still be updating)
            date = datetime.now() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        filename = os.path.join(DATA_DIRECTORY, f"{date_str}.csv")
        
        if not os.path.exists(filename):
            logger.warning(f"No data file found for {date_str}")
            return False
        
        try:
            return self._export_file(filename, date_str)
        except Exception as e:
            logger.error(f"Export failed for {date_str}: {e}", exc_info=True)
            return False
    
    def _export_file(self, filename, date_str):
        """
        Override this method in subclasses to implement export logic.
        
        Args:
            filename: Path to CSV file
            date_str: Date string (YYYY-MM-DD)
        
        Returns:
            bool: Success status
        """
        raise NotImplementedError("Subclasses must implement _export_file")


class LocalBackupExporter(DataExporter):
    """Export data to local or network backup directory."""
    
    def __init__(self, backup_dir, enabled=True):
        super().__init__(enabled)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _export_file(self, filename, date_str):
        """Copy CSV file to backup directory."""
        import shutil
        
        dest_file = self.backup_dir / f"{date_str}.csv"
        shutil.copy2(filename, dest_file)
        logger.info(f"Backed up {date_str} to {dest_file}")
        return True


class JSONExporter(DataExporter):
    """Export data as JSON for webhook/API integration."""
    
    def __init__(self, output_dir=None, enabled=True):
        super().__init__(enabled)
        self.output_dir = Path(output_dir) if output_dir else Path(DATA_DIRECTORY) / "json"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _export_file(self, filename, date_str):
        """Convert CSV to JSON."""
        readings = []
        stats = {
            'temps': [],
            'hums': []
        }
        
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
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
                if 'comfort_zone' in row:
                    reading['comfort_zone'] = row['comfort_zone']
                
                readings.append(reading)
                stats['temps'].append(reading['temperature'])
                stats['hums'].append(reading['humidity'])
        
        # Calculate summary
        summary = {
            'date': date_str,
            'readings_count': len(readings),
            'temperature': {
                'min': min(stats['temps']) if stats['temps'] else None,
                'max': max(stats['temps']) if stats['temps'] else None,
                'avg': sum(stats['temps']) / len(stats['temps']) if stats['temps'] else None
            },
            'humidity': {
                'min': min(stats['hums']) if stats['hums'] else None,
                'max': max(stats['hums']) if stats['hums'] else None,
                'avg': sum(stats['hums']) / len(stats['hums']) if stats['hums'] else None
            }
        }
        
        output_data = {
            'summary': summary,
            'readings': readings
        }
        
        output_file = self.output_dir / f"{date_str}.json"
        with open(output_file, 'w') as jsonfile:
            json.dump(output_data, jsonfile, indent=2)
        
        logger.info(f"Exported {date_str} to JSON: {output_file}")
        return True


class WebhookExporter(DataExporter):
    """Export data to a REST API webhook."""
    
    def __init__(self, webhook_url, api_key=None, enabled=True):
        super().__init__(enabled)
        self.webhook_url = webhook_url
        self.api_key = api_key
    
    def _export_file(self, filename, date_str):
        """POST data to webhook endpoint."""
        try:
            import requests
        except ImportError:
            logger.error("requests library not installed. Cannot use WebhookExporter.")
            return False
        
        # Read and prepare data
        readings = []
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                readings.append(dict(row))
        
        payload = {
            'date': date_str,
            'readings': readings
        }
        
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.ok:
            logger.info(f"Successfully posted {date_str} to webhook")
            return True
        else:
            logger.error(f"Webhook failed: {response.status_code} {response.text}")
            return False


def run_daily_export(exporters):
    """
    Run all configured exporters for yesterday's data.
    
    Args:
        exporters: List of DataExporter instances
    
    Returns:
        dict: Results for each exporter
    """
    yesterday = datetime.now() - timedelta(days=1)
    results = {}
    
    logger.info(f"Running daily export for {yesterday.strftime('%Y-%m-%d')}")
    
    for exporter in exporters:
        name = exporter.__class__.__name__
        try:
            success = exporter.export(yesterday)
            results[name] = 'success' if success else 'failed'
        except Exception as e:
            logger.error(f"Exporter {name} crashed: {e}", exc_info=True)
            results[name] = 'error'
    
    logger.info(f"Export results: {results}")
    return results


# Example configuration (can be moved to settings or .env file)
def get_configured_exporters():
    """
    Get list of configured exporters based on settings.
    
    Returns:
        list: Enabled DataExporter instances
    """
    exporters = []
    
    # Local backup (always enabled as fallback)
    exporters.append(LocalBackupExporter(
        backup_dir='data/backup',
        enabled=True
    ))
    
    # JSON export (useful for external processing)
    exporters.append(JSONExporter(
        output_dir='data/json',
        enabled=True
    ))
    
    # Webhook (disabled by default - configure with your endpoint)
    # exporters.append(WebhookExporter(
    #     webhook_url=os.getenv('EXPORT_WEBHOOK_URL'),
    #     api_key=os.getenv('EXPORT_API_KEY'),
    #     enabled=os.getenv('EXPORT_WEBHOOK_ENABLED', 'false').lower() == 'true'
    # ))
    
    return exporters
