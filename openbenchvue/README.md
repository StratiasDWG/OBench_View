# OpenBenchVue

An open-source Python-based clone of Keysight's PathWave BenchVue software for instrument control, test automation, and data visualization.

## Overview

OpenBenchVue is a comprehensive PC-based application for controlling test and measurement instruments. It provides:

- **Intuitive GUI**: Modern PyQt5-based interface with auto-discovery and instrument control
- **Multi-Instrument Support**: Control multiple instruments simultaneously (DMM, Oscilloscopes, Power Supplies, Function Generators, etc.)
- **Visual Test Automation**: Drag-and-drop sequence builder for creating automated tests without programming
- **Real-Time Visualization**: Live plotting and analysis using Matplotlib
- **Data Logging & Export**: Save measurements to CSV, Excel, or custom formats
- **Remote Access**: Optional web-based dashboard for monitoring via browser
- **Extensible Architecture**: Plugin system for adding custom instrument drivers

## Features

### Instrument Control
- **Digital Multimeters (DMM)**: DC/AC voltage, current, resistance, capacitance measurements
- **Oscilloscopes**: Waveform capture, triggering, measurements (rise time, frequency, etc.)
- **Power Supplies**: Voltage/current output, multi-channel control, sequencing
- **Function Generators**: Sine/square/ramp waveforms, modulation, burst modes
- **Power Analyzers**: Power logging, efficiency calculations, I/V tracing
- **Generic SCPI**: Send raw commands to any SCPI-compatible instrument

### Automation
- Visual sequence builder with drag-and-drop blocks
- Support for loops, conditionals, delays, and complex logic
- Save/load sequences as YAML files
- Runtime execution with progress tracking and error handling

### Data Management
- Real-time data streaming with non-blocking I/O
- Advanced signal processing (FFT, filtering, statistics)
- Multi-instrument data correlation and synchronization
- Export to CSV, Excel, PNG, or JSON formats

### Remote Access
- Flask-based web server for remote monitoring
- View measurements and plots from any browser on local network
- Read-only dashboard for mobile devices

## Installation

### Prerequisites

1. **Python 3.10 or higher**
2. **VISA Backend**: Install one of the following:
   - Keysight IO Libraries Suite (recommended)
   - National Instruments NI-VISA
   - Or use pure Python backend (pyvisa-py)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Quick Start

```bash
python -m openbenchvue.main
```

Or if installed as a package:

```bash
python setup.py install
openbenchvue
```

## Usage

### Connecting to Instruments

1. Launch OpenBenchVue
2. Click "Scan for Instruments" on the dashboard
3. Select detected instruments and click "Connect"
4. Use instrument-specific tabs to control devices

### Creating Test Sequences

1. Navigate to "Automation" tab
2. Drag blocks from the palette (Set Voltage, Measure, Delay, etc.)
3. Configure block parameters
4. Click "Run Sequence" to execute
5. Save sequence for later use

### Data Logging

1. Open "Data Logger" panel
2. Select channels/measurements to log
3. Set sampling rate and duration
4. Click "Start Logging"
5. Export data when complete

### Remote Access

1. Enable "Remote Server" in settings
2. Note the displayed IP address and port
3. Access from browser: `http://<ip>:<port>`

## Project Structure

```
openbenchvue/
├── openbenchvue/
│   ├── main.py                  # Application entry point
│   ├── gui/                     # GUI components
│   │   ├── main_window.py       # Main application window
│   │   ├── dashboard.py         # Instrument discovery dashboard
│   │   ├── instrument_panels.py # Device control panels
│   │   ├── sequence_builder.py  # Visual automation editor
│   │   ├── data_viewer.py       # Plotting and visualization
│   │   └── widgets.py           # Reusable UI components
│   ├── instruments/             # Instrument drivers
│   │   ├── base.py              # Abstract base classes
│   │   ├── dmm.py               # Digital multimeter
│   │   ├── oscilloscope.py      # Oscilloscope
│   │   ├── power_supply.py      # Power supply
│   │   ├── function_generator.py# Function/waveform generator
│   │   ├── power_analyzer.py    # Power meter/analyzer
│   │   └── detector.py          # Auto-detection logic
│   ├── automation/              # Test automation
│   │   ├── sequence.py          # Sequence data structures
│   │   ├── executor.py          # Runtime execution engine
│   │   └── blocks.py            # Automation block definitions
│   ├── data/                    # Data handling
│   │   ├── logger.py            # Data logging
│   │   ├── processor.py         # Signal processing
│   │   └── exporter.py          # Export utilities
│   ├── remote/                  # Remote access
│   │   └── server.py            # Flask web server
│   └── utils/
│       └── config.py            # Configuration management
├── examples/
│   └── example_sequence.yaml    # Sample test sequence
└── docs/
    └── user_guide.md            # Comprehensive user guide
```

## Architecture

### Instrument Communication
- Uses PyVISA for VISA-compliant instrument control
- Supports USB, GPIB, LAN (VXI-11, Socket), and RS-232 interfaces
- Threaded I/O for non-blocking communication
- Automatic reconnection on timeout/disconnect

### GUI Design
- PyQt5 for modern, responsive interface
- Matplotlib integration for embedded plots
- QThread for background tasks
- Signal/slot mechanism for thread-safe updates

### Automation Engine
- Visual block-based programming
- Generates executable Python code from sequences
- YAML serialization for portability
- Runtime interpreter with error recovery

### Data Pipeline
- NumPy/SciPy for numerical processing
- Pandas for structured data management
- Real-time streaming with circular buffers
- Configurable decimation for performance

## Configuration

Edit `config.yaml` to customize:

```yaml
visa:
  backend: '@iolib'  # '@py' for pyvisa-py, '@iolib' for Keysight/NI
  timeout: 5000      # ms

gui:
  theme: 'light'     # 'light' or 'dark'
  update_rate: 100   # ms

remote:
  enabled: false
  host: '0.0.0.0'
  port: 5000

logging:
  level: 'INFO'
  file: 'openbenchvue.log'
```

## Extending OpenBenchVue

### Adding Custom Instruments

Create a new driver in `openbenchvue/instruments/`:

```python
from openbenchvue.instruments.base import BaseInstrument

class MyInstrument(BaseInstrument):
    """Custom instrument driver"""

    SUPPORTED_MODELS = ['MY-1000', 'MY-2000']

    def identify(self) -> dict:
        """Return instrument identification"""
        idn = self.query("*IDN?")
        # Parse and return dict

    def configure(self, **params):
        """Configure instrument parameters"""
        pass

    def measure(self):
        """Perform measurement"""
        pass
```

Register in `instruments/__init__.py`:

```python
from .my_instrument import MyInstrument
INSTRUMENT_CLASSES.append(MyInstrument)
```

### Creating Custom Automation Blocks

```python
from openbenchvue.automation.blocks import BaseBlock

class CustomBlock(BaseBlock):
    """Custom automation block"""

    name = "My Custom Action"
    category = "Custom"

    def __init__(self):
        super().__init__()
        self.add_parameter('param1', 'string', 'Default')

    def execute(self, context):
        """Execute block logic"""
        param1 = self.get_parameter('param1')
        # Implement custom logic
        return {'status': 'success'}
```

## Troubleshooting

### No Instruments Detected
- Ensure VISA backend is installed (Keysight IO Libraries or NI-VISA)
- Check instrument connections (USB cable, network, GPIB address)
- Verify instruments are powered on
- Run `pyvisa-info` to diagnose VISA installation

### GUI Freezing
- Ensure instruments are responding (check timeouts)
- Reduce data logging rate
- Check for network latency (LAN instruments)

### Communication Errors
- Verify correct VISA resource string
- Increase timeout in config
- Check for conflicting applications (other programs using instrument)
- Try different VISA backend

### Import Errors
- Install all dependencies: `pip install -r requirements.txt`
- Ensure Python 3.10+
- Use virtual environment to avoid conflicts

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

Please follow PEP 8 style guidelines and include docstrings.

## License

MIT License - See LICENSE file for details

## Disclaimer

OpenBenchVue is an independent open-source project and is not affiliated with, endorsed by, or sponsored by Keysight Technologies. BenchVue and PathWave are trademarks of Keysight Technologies.

This software is provided for educational and research purposes. Users are responsible for ensuring proper instrument operation and safety.

## Credits

Developed with:
- PyVISA - Instrument communication
- PyQt5 - GUI framework
- Matplotlib - Data visualization
- NumPy/SciPy - Scientific computing
- Pandas - Data analysis
- Flask - Web interface

## Support

- Report issues on GitHub
- Consult `docs/user_guide.md` for detailed instructions
- Community forums and discussions

## Roadmap

Future enhancements:
- [ ] Cloud data sync
- [ ] Mobile app (Android/iOS)
- [ ] Advanced analysis plugins (harmonic analysis, eye diagrams)
- [ ] Multi-user collaboration
- [ ] Instrument simulation mode for offline development
- [ ] Integration with LabVIEW/MATLAB
- [ ] Database backend for large datasets
- [ ] Machine learning-based anomaly detection

## Version History

### v0.1.0 (Initial Release)
- Core instrument support (DMM, Scope, PSU, FGen)
- Basic GUI with dashboard
- Visual sequence builder
- Data logging and export
- Remote web interface
- Auto-detection

---

**Happy Testing!**
