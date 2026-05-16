/**
 * Dashboard JavaScript for Environmental Monitor
 * Handles live data updates via AJAX
 */

// Update interval in milliseconds (10 seconds)
const UPDATE_INTERVAL = 10000;
let updateTimer = null;

/**
 * Format timestamp to readable format
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

/**
 * Update status indicator
 */
function updateStatus(isHealthy, lastUpdate) {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const lastUpdateEl = document.getElementById('last-update');

    if (isHealthy) {
        statusDot.classList.remove('offline');
        statusText.textContent = 'Online';
        statusText.style.color = '#28a745';
    } else {
        statusDot.classList.add('offline');
        statusText.textContent = 'Offline';
        statusText.style.color = '#dc3545';
    }

    lastUpdateEl.textContent = `Last update: ${formatTimestamp(lastUpdate)}`;
}

/**
 * Update sensor data on the page
 */
function updateDisplay(data) {
    // Temperature
    document.getElementById('temperature').textContent = 
        data.temperature !== null ? data.temperature.toFixed(1) : '--';

    // Humidity
    document.getElementById('humidity').textContent = 
        data.humidity !== null ? data.humidity.toFixed(1) : '--';

    // Comfort metrics
    if (data.comfort_metrics) {
        const cm = data.comfort_metrics;
        
        document.getElementById('heat-index').textContent = 
            cm.heat_index !== null ? cm.heat_index.toFixed(1) : '--';
        
        document.getElementById('dew-point').textContent = 
            cm.dew_point !== null ? cm.dew_point.toFixed(1) : '--';
        
        document.getElementById('comfort-icon').textContent = 
            cm.comfort_icon || '☀️';
        
        document.getElementById('comfort-zone').textContent = 
            cm.comfort_zone || 'Unknown';
        
        document.getElementById('comfort-description').textContent = 
            cm.comfort_description || 'No data';
    }

    // Daily statistics
    if (data.stats) {
        const stats = data.stats;
        
        document.getElementById('temp-range').textContent = 
            `${stats.temp_min.toFixed(1)}°C to ${stats.temp_max.toFixed(1)}°C`;
        
        document.getElementById('hum-range').textContent = 
            `${stats.hum_min.toFixed(0)}% to ${stats.hum_max.toFixed(0)}%`;
    } else {
        document.getElementById('temp-range').textContent = 'No data yet';
        document.getElementById('hum-range').textContent = 'No data yet';
    }

    // Update status
    updateStatus(data.sensor_healthy, data.timestamp);
}

/**
 * Fetch current data from API
 */
async function fetchCurrentData() {
    try {
        const response = await fetch('/api/current');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        updateDisplay(data);
        
    } catch (error) {
        console.error('Error fetching data:', error);
        updateStatus(false, null);
        
        // Show error in console but don't alert user
        // (errors will be obvious from the "Offline" status)
    }
}

/**
 * Start automatic updates
 */
function startAutoUpdate() {
    // Initial fetch
    fetchCurrentData();
    
    // Set up recurring updates
    updateTimer = setInterval(fetchCurrentData, UPDATE_INTERVAL);
}

/**
 * Stop automatic updates
 */
function stopAutoUpdate() {
    if (updateTimer) {
        clearInterval(updateTimer);
        updateTimer = null;
    }
}

/**
 * Initialize dashboard when page loads
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Environmental Monitor Dashboard initialized');
    startAutoUpdate();
});

/**
 * Clean up when page unloads
 */
window.addEventListener('beforeunload', () => {
    stopAutoUpdate();
});

/**
 * Handle visibility changes (pause updates when tab is hidden)
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden, pausing updates');
        stopAutoUpdate();
    } else {
        console.log('Page visible, resuming updates');
        startAutoUpdate();
    }
});
