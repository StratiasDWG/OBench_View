# OpenBenchVue User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Dashboard](#dashboard)
5. [Instrument Control](#instrument-control)
6. [Data Logging](#data-logging)
7. [Test Automation](#test-automation)
8. [Remote Access](#remote-access)
9. [Advanced Topics](#advanced-topics)
10. [Troubleshooting](#troubleshooting)

## Introduction

OpenBenchVue is a comprehensive, open-source platform for instrument control and test automation. It provides an intuitive graphical interface similar to Keysight's PathWave BenchVue, enabling users to:

- Control multiple instruments simultaneously
- Create automated test sequences without programming
- Log and visualize measurement data in real-time
- Export data in various formats
- Access instruments remotely via web interface

## Installation

### Prerequisites

1. **Python 3.10 or higher**
   ```bash
   python --version
   ```

2. **VISA Backend** (choose one):
   - **Keysight IO Libraries Suite** (recommended) - [Download](https://www.keysight.com/find/iolib)
   - **NI-VISA** - [Download](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html)
   - **Pure Python backend** (pyvisa-py) - Limited functionality

### Install OpenBenchVue

```bash
# Clone repository
git clone https://github.com/yourusername/openbenchvue.git
cd openbenchvue

# Install dependencies
pip install -r requirements.txt

# Optional: Install as package
python setup.py install
```

### Verify Installation

```bash
# Check VISA installation
python -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm.list_resources())"

# Launch OpenBenchVue
python -m openbenchvue.main
```

## Getting Started

### Launch Application

**GUI Mode (default):**
```bash
openbenchvue
```

**CLI Mode:**
```bash
# Scan for instruments
openbenchvue --scan

# Run a sequence
openbenchvue --sequence examples/example_sequence.yaml

# Start remote server
openbenchvue --remote --port 5000
```

### First Time Setup

1. Launch OpenBenchVue
2. Go to Dashboard tab
3. Click "Scan for Instruments"
4. Select detected instruments
5. Click "Connect Selected"

## Dashboard

The Dashboard is your starting point for instrument discovery and connection.

### Scanning for Instruments

1. Click **"Scan for Instruments"** button
2. Wait for scan to complete (may take 5-10 seconds)
3. Review detected instruments in the list

Each instrument shows:
- Manufacturer and model
- Instrument type (DMM, Oscilloscope, Power Supply, etc.)
- VISA resource string
- Serial number

### Connecting to Instruments

1. Select one or more instruments from the list
2. Click **"Connect Selected"**
3. Wait for connection confirmation
4. Connected instruments appear in green

**Note:** You can connect to multiple instruments simultaneously.

### Connection Status

- 🟢 Green = Connected
- 🔴 Red = Connection failed
- ⚪ White = Not connected

## Instrument Control

The Instrument Control tab provides device-specific interfaces for each connected instrument.

### Digital Multimeter (DMM)

**Features:**
- Measurement display with large readout
- Function selection (DC/AC voltage, current, resistance, etc.)
- One-click measurements
- Statistics tracking

**Usage:**
1. Select DMM from dropdown
2. Choose measurement function
3. Click "Measure"
4. View result in main display

**Supported Functions:**
- DC Voltage
- AC Voltage
- DC Current
- AC Current
- Resistance (2-wire/4-wire)
- Frequency
- Capacitance

### Power Supply

**Features:**
- Voltage and current control
- Real-time measurements
- Output enable/disable
- Multi-channel support
- Protection settings (OVP/OCP)

**Usage:**
1. Select power supply from dropdown
2. Set voltage: Enter value, click "Apply"
3. Set current limit: Enter value, click "Apply"
4. Enable output: Check "Output Enabled"
5. Monitor real-time measurements

**Safety Tips:**
- Always set current limit before enabling output
- Verify voltage setting before connecting load
- Use OVP/OCP protection when available

### Oscilloscope

**Features:**
- Waveform capture
- Channel configuration
- Trigger settings
- Automated measurements
- Math functions (FFT, etc.)

**Usage:**
1. Select oscilloscope from dropdown
2. Enable desired channels
3. Configure vertical scale and coupling
4. Set timebase
5. Configure trigger
6. Capture waveform

### Function Generator

**Features:**
- Standard waveforms (sine, square, ramp, pulse)
- Frequency and amplitude control
- Modulation (AM, FM, PM)
- Burst mode
- Arbitrary waveforms

**Usage:**
1. Select function generator from dropdown
2. Choose waveform type
3. Set frequency and amplitude
4. Enable output

### Generic SCPI Control

For instruments without dedicated panels, use SCPI commands directly:

1. Enter command in text box
2. Click "Send Command"
3. View response

**Examples:**
```
*IDN?                  # Query identification
MEAS:VOLT:DC?          # Measure DC voltage
SOUR:VOLT 5.0          # Set voltage to 5V
OUTP ON                # Enable output
```

## Data Logging

The Data Logger captures and visualizes measurements in real-time.

### Starting a Logging Session

1. Go to **Data Logger** tab
2. Click **"Start Logging"**
3. Use instrument controls or automation to generate data
4. View real-time plot

### Real-Time Plotting

- Multiple channels plotted simultaneously
- Automatic scaling
- Pan and zoom with toolbar
- Channel colors auto-assigned

### Statistics

View real-time statistics for logged data:
- Number of data points
- Active channels
- Logging duration
- Min/max/mean values

### Stopping Logging

1. Click **"Stop Logging"**
2. Data remains in memory
3. Continue logging or export data

### Exporting Data

1. Click **"Export..."** button
2. Choose format and location
3. Supported formats:
   - **CSV** - Text file with comma-separated values
   - **Excel** - XLSX workbook with formatted data
   - **JSON** - Structured data for custom processing
   - **NumPy** - .npz file for Python analysis
   - **MATLAB** - .mat file for MATLAB

### Data Analysis

Use the built-in processor for advanced analysis:
- FFT and spectral analysis
- Digital filtering (low-pass, high-pass, band-pass)
- Statistical analysis
- Peak detection
- Trend analysis

## Test Automation

The Automation tab enables creating test sequences without programming.

### Creating a Sequence

1. Go to **Automation** tab
2. Select block from palette on left
3. Click **"Add to Sequence"**
4. Repeat to build sequence
5. Configure block parameters (if needed)

### Available Blocks

**Control:**
- **Delay** - Wait for specified duration
- **Loop** - Repeat actions multiple times
- **If Condition** - Conditional execution

**Power Supply:**
- **Set Voltage** - Configure output voltage
- **Set Current** - Configure current limit
- **Output Enable** - Turn output on/off

**Measurement:**
- **Measure** - Perform measurement and store result
- **Assert** - Validate measurement meets criteria

**Data:**
- **Log Data** - Record data point to log

**General:**
- **Comment** - Add documentation to sequence

### Configuring Blocks

1. Select block in sequence list
2. View parameters panel
3. Enter values
4. Select instruments from dropdowns
5. Save changes

### Running a Sequence

1. Build sequence with required blocks
2. Click **"Run Sequence"**
3. Monitor progress
4. View results when complete

### Execution Controls

- **Run** - Execute sequence from start
- **Pause** - Temporarily halt execution
- **Resume** - Continue paused sequence
- **Stop** - Abort execution

### Saving/Loading Sequences

**Save:**
1. File menu → Save Sequence
2. Choose location and format (YAML/JSON)
3. Enter sequence name

**Load:**
1. File menu → Open Sequence
2. Select sequence file
3. Sequence appears in editor

### Example Sequences

Included examples demonstrate:
- Basic power supply control
- DMM measurements with validation
- Loop-based data collection
- Automated test procedures

## Remote Access

Access OpenBenchVue from web browser for remote monitoring.

### Starting Remote Server

**From GUI:**
1. Tools menu → Start Remote Server
2. Note the URL displayed
3. Access from any browser on network

**From CLI:**
```bash
openbenchvue --remote --port 5000
```

### Accessing Dashboard

1. Open web browser
2. Navigate to: `http://<server-ip>:5000`
3. View instrument status and measurements
4. Auto-refresh every 2 seconds

### Features

- View connected instruments
- Real-time measurement updates
- Channel data visualization
- Mobile-friendly interface
- Read-only (safety)

### Security Notes

- Remote server is **read-only** by default
- Bind to `localhost` for local access only
- Use firewall to restrict access
- Consider VPN for internet access

## Advanced Topics

### Custom Instrument Drivers

Create custom drivers for unsupported instruments:

```python
from openbenchvue.instruments.base import BaseInstrument, InstrumentType

class MyInstrument(BaseInstrument):
    INSTRUMENT_TYPE = InstrumentType.GENERIC
    SUPPORTED_MODELS = [r'MY-\d{4}']

    def initialize(self):
        # Custom initialization
        pass

    def get_capabilities(self):
        return {'features': ['measurement']}

    def get_status(self):
        return {'connected': True}
```

Register in `instruments/__init__.py`:
```python
from .my_instrument import MyInstrument
INSTRUMENT_CLASSES.append(MyInstrument)
```

### Custom Automation Blocks

Create custom blocks for specialized operations:

```python
from openbenchvue.automation.blocks import BaseBlock

class MyCustomBlock(BaseBlock):
    name = "My Custom Action"
    category = "Custom"

    def _define_parameters(self):
        self.add_parameter('param1', 'float', 1.0, 'Parameter 1')

    def execute(self, context):
        value = self.get_parameter('param1')
        # Custom logic here
        return {'status': 'success', 'result': value}
```

Register in `automation/blocks.py`:
```python
BLOCK_REGISTRY['MyCustomBlock'] = MyCustomBlock
```

### Plugins and Extensions

OpenBenchVue supports plugins for:
- Custom instrument drivers
- Automation blocks
- Data processors
- Export formats

Place plugins in:
- `~/.openbenchvue/plugins/`
- `./plugins/` (project directory)

### Configuration

Edit `config.yaml` to customize:
- VISA backend selection
- GUI theme and appearance
- Logging settings
- Data buffer sizes
- Automation limits

### API Usage

Use OpenBenchVue as a library:

```python
from openbenchvue.instruments.detector import InstrumentDetector
from openbenchvue.instruments.dmm import DigitalMultimeter

# Detect instruments
detector = InstrumentDetector()
instruments = detector.auto_connect()

# Use instrument
dmm = instruments['DMM_1']
voltage = dmm.measure()
print(f"Voltage: {voltage}V")

dmm.disconnect()
```

## Troubleshooting

### No Instruments Detected

**Possible Causes:**
- VISA not installed or configured
- Instruments not powered on
- Incorrect interface configuration
- Driver not compatible

**Solutions:**
1. Verify VISA installation: `pyvisa-info`
2. Check instrument power and connections
3. Test with Keysight Connection Expert or NI MAX
4. Try different VISA backend in config.yaml
5. Check instrument manual for interface setup

### Connection Timeout

**Solutions:**
- Increase timeout in config.yaml
- Check network settings (for LAN instruments)
- Verify GPIB address
- Restart instrument
- Check for conflicting applications

### GUI Not Launching

**Solutions:**
- Verify PyQt5 installed: `pip install PyQt5`
- Check Python version (3.10+ required)
- Try CLI mode to test functionality
- Check error messages in terminal
- Review log file: `openbenchvue.log`

### Import Errors

**Solutions:**
- Install all dependencies: `pip install -r requirements.txt`
- Use virtual environment to avoid conflicts
- Update packages: `pip install --upgrade <package>`
- Check Python path

### Measurement Errors

**Solutions:**
- Verify instrument range settings
- Check input connections
- Increase NPLC for noisy signals
- Use appropriate measurement function
- Consult instrument manual

### Sequence Execution Fails

**Solutions:**
- Validate sequence before running
- Check block parameters
- Verify instruments are connected
- Enable detailed logging (DEBUG level)
- Review execution log

### Remote Server Issues

**Solutions:**
- Check firewall settings
- Verify port not in use
- Test localhost first
- Check Flask version compatibility
- Review remote server logs

## Getting Help

- **Documentation**: [https://github.com/yourusername/openbenchvue](https://github.com/yourusername/openbenchvue)
- **Issues**: Report bugs on GitHub Issues
- **Community**: Join discussion forum
- **Email**: support@openbenchvue.org

## Appendix

### Supported Instruments

**Digital Multimeters:**
- Keysight 34401A, 34410A, 34461A
- Keysight U1200 series
- Generic SCPI DMMs

**Oscilloscopes:**
- Keysight InfiniiVision (DSOX, MSOX)
- Keysight Infiniium (DSAZ, MSAZ)
- Keysight EDU series

**Power Supplies:**
- Keysight E36xx series
- Keysight N67xx, N79xx series
- Generic SCPI power supplies

**Function Generators:**
- Keysight 33xxx series
- Keysight EDU33xxx series
- Generic SCPI waveform generators

### Keyboard Shortcuts

- `Ctrl+O` - Open sequence
- `Ctrl+S` - Save sequence
- `Ctrl+Q` - Quit application
- `F5` - Scan for instruments

### File Formats

**Sequences:**
- `.yaml` - Human-readable sequence definition
- `.json` - JSON sequence format

**Data Export:**
- `.csv` - Comma-separated values
- `.xlsx` - Excel workbook
- `.json` - Structured JSON
- `.npz` - NumPy compressed arrays
- `.mat` - MATLAB data file

---

*OpenBenchVue - Open Source Instrument Control*
*Version 0.1.0*
