"""
Flask Remote Server

Web-based interface for remote monitoring and control.
"""

import logging
import threading
import json
from typing import Dict, Any
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

logger = logging.getLogger(__name__)


# Simple HTML template for remote dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OpenBenchVue Remote Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .instrument-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-connected { background-color: #4caf50; }
        .status-disconnected { background-color: #f44336; }
        .measurement {
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 10px;
            background: #e3f2fd;
            border-radius: 4px;
        }
        .measurement-label {
            font-size: 0.9em;
            color: #666;
        }
        .measurement-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #1976d2;
        }
        button {
            background: #2196f3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover {
            background: #1976d2;
        }
        .refresh-info {
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>🔧 OpenBenchVue Remote Dashboard</h1>
    <p>Remote monitoring interface for connected instruments</p>

    <div id="instruments"></div>

    <div class="refresh-info">
        Last updated: <span id="last-update">Never</span> |
        <button onclick="refreshData()">Refresh Now</button>
        <button onclick="toggleAutoRefresh()">Auto-Refresh: <span id="auto-status">ON</span></button>
    </div>

    <script>
        let autoRefresh = true;
        let refreshInterval;

        function formatValue(value, precision = 3) {
            if (typeof value === 'number') {
                return value.toFixed(precision);
            }
            return value;
        }

        function refreshData() {
            fetch('/api/instruments')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('instruments');
                    container.innerHTML = '';

                    if (data.instruments.length === 0) {
                        container.innerHTML = '<p>No instruments connected</p>';
                        return;
                    }

                    data.instruments.forEach(inst => {
                        const card = document.createElement('div');
                        card.className = 'instrument-card';

                        const statusClass = inst.connected ? 'status-connected' : 'status-disconnected';
                        const statusText = inst.connected ? 'Connected' : 'Disconnected';

                        let html = `
                            <h3>
                                <span class="status-indicator ${statusClass}"></span>
                                ${inst.name} (${inst.type})
                            </h3>
                            <p><strong>Model:</strong> ${inst.model} | <strong>Resource:</strong> ${inst.resource}</p>
                        `;

                        if (inst.status && Object.keys(inst.status).length > 0) {
                            html += '<div style="margin-top: 15px;">';
                            for (const [key, value] of Object.entries(inst.status)) {
                                if (typeof value === 'object' && !Array.isArray(value)) {
                                    continue; // Skip nested objects for simplicity
                                }
                                html += `
                                    <div class="measurement">
                                        <div class="measurement-label">${key.replace(/_/g, ' ').toUpperCase()}</div>
                                        <div class="measurement-value">${formatValue(value)}</div>
                                    </div>
                                `;
                            }
                            html += '</div>';
                        }

                        card.innerHTML = html;
                        container.appendChild(card);
                    });

                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    document.getElementById('instruments').innerHTML = '<p>Error loading data</p>';
                });
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            document.getElementById('auto-status').textContent = autoRefresh ? 'ON' : 'OFF';

            if (autoRefresh) {
                startAutoRefresh();
            } else {
                clearInterval(refreshInterval);
            }
        }

        function startAutoRefresh() {
            refreshInterval = setInterval(refreshData, 2000); // Refresh every 2 seconds
        }

        // Initial load
        refreshData();
        if (autoRefresh) {
            startAutoRefresh();
        }
    </script>
</body>
</html>
"""


class RemoteServer:
    """
    Flask-based remote server for web access.

    Provides BenchVue-like remote monitoring:
    - View instrument status via web browser
    - Real-time data updates
    - Read-only dashboard (safety)
    - Mobile-friendly interface
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        """
        Initialize remote server.

        Args:
            host: Server host address
            port: Server port
        """
        self.host = host
        self.port = port

        # Create Flask app
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for API access

        # Disable Flask default logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        # Data storage
        self.instruments: Dict[str, Any] = {}
        self.data_logger = None

        # Server thread
        self._server_thread = None
        self._running = False

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template_string(DASHBOARD_TEMPLATE)

        @self.app.route('/api/instruments')
        def get_instruments():
            """Get list of instruments with status"""
            instruments_list = []

            for name, instrument in self.instruments.items():
                try:
                    info = {
                        'name': name,
                        'type': instrument.INSTRUMENT_TYPE.value if hasattr(instrument, 'INSTRUMENT_TYPE') else 'Unknown',
                        'connected': instrument.connected if hasattr(instrument, 'connected') else False,
                        'resource': instrument.resource_string if hasattr(instrument, 'resource_string') else 'Unknown',
                        'model': 'Unknown',
                        'status': {}
                    }

                    # Get identity
                    if hasattr(instrument, 'identity') and instrument.identity:
                        info['model'] = f"{instrument.identity.manufacturer} {instrument.identity.model}"

                    # Get status if connected
                    if info['connected'] and hasattr(instrument, 'get_status'):
                        try:
                            info['status'] = instrument.get_status()
                        except:
                            pass

                    instruments_list.append(info)

                except Exception as e:
                    logger.error(f"Error getting info for {name}: {e}")

            return jsonify({
                'instruments': instruments_list,
                'count': len(instruments_list)
            })

        @self.app.route('/api/data')
        def get_data():
            """Get logged data"""
            if not self.data_logger:
                return jsonify({'error': 'No data logger configured'})

            try:
                channels = self.data_logger.get_channels()
                data = {}

                for channel in channels:
                    times, values = self.data_logger.get_channel_data(channel)
                    # Return last 100 points to keep response size reasonable
                    data[channel] = {
                        'time': times[-100:].tolist() if len(times) > 0 else [],
                        'values': values[-100:].tolist() if len(values) > 0 else []
                    }

                return jsonify({
                    'channels': channels,
                    'data': data,
                    'count': len(self.data_logger)
                })

            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/status')
        def server_status():
            """Get server status"""
            return jsonify({
                'status': 'running',
                'instruments_connected': len(self.instruments),
                'data_logger_active': self.data_logger.is_logging() if self.data_logger else False
            })

    def set_instruments(self, instruments: Dict[str, Any]):
        """
        Set instruments to monitor.

        Args:
            instruments: Dictionary mapping names to instrument instances
        """
        self.instruments = instruments
        logger.info(f"Remote server monitoring {len(instruments)} instruments")

    def set_data_logger(self, data_logger):
        """
        Set data logger for remote data access.

        Args:
            data_logger: DataLogger instance
        """
        self.data_logger = data_logger
        logger.info("Data logger connected to remote server")

    def start(self):
        """Start remote server in background thread"""
        if self._running:
            logger.warning("Remote server already running")
            return

        def _run_server():
            try:
                logger.info(f"Starting remote server on http://{self.host}:{self.port}")
                self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Remote server error: {e}")

        self._running = True
        self._server_thread = threading.Thread(target=_run_server, daemon=True)
        self._server_thread.start()

        logger.info(f"Remote server started. Access dashboard at http://localhost:{self.port}")

    def stop(self):
        """Stop remote server"""
        # Note: Flask doesn't have a clean way to stop from within
        # In production, would use Werkzeug shutdown or run in separate process
        self._running = False
        logger.info("Remote server stop requested")

    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running

    def get_url(self) -> str:
        """Get server URL"""
        return f"http://{self.host if self.host != '0.0.0.0' else 'localhost'}:{self.port}"
