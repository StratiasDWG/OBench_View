"""
Power Analyzer Driver

Supports power meters and analyzers for power quality measurements.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .base import BaseInstrument, InstrumentType, InstrumentError

logger = logging.getLogger(__name__)


@dataclass
class PowerMeasurement:
    """Power measurement result"""
    voltage_rms: float
    current_rms: float
    power_real: float
    power_apparent: float
    power_reactive: float
    power_factor: float
    frequency: float
    timestamp: float


class PowerAnalyzer(BaseInstrument):
    """
    Power Analyzer/Meter driver.

    Provides power quality measurements:
    - Voltage, current, power (real, reactive, apparent)
    - Power factor, THD
    - Harmonics analysis
    - Integration (Wh, Ah)
    - Efficiency calculations
    """

    INSTRUMENT_TYPE = InstrumentType.POWER_ANALYZER
    SUPPORTED_MODELS = [
        r'PA\d{4}',  # Power analyzer
        r'N\d{4}[AB]',  # Keysight N series power meters
        r'CW\d{3}',  # Generic power meter
    ]

    def __init__(self, resource_string: str, rm=None):
        super().__init__(resource_string, rm)

        self.integration_enabled = False
        self.integration_start_time = None

    def initialize(self):
        """Initialize power analyzer"""
        try:
            self.clear()
            self.reset()

            logger.info("Power analyzer initialized")

        except Exception as e:
            logger.error(f"Power analyzer initialization failed: {e}")
            raise

    def get_capabilities(self) -> Dict[str, Any]:
        """Get power analyzer capabilities"""
        return {
            'measurements': [
                'voltage_rms', 'current_rms',
                'power_real', 'power_apparent', 'power_reactive',
                'power_factor', 'frequency',
                'thd_voltage', 'thd_current',
                'harmonics'
            ],
            'integration': True,
            'harmonic_analysis': True,
            'max_channels': 1,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current analyzer status"""
        return {
            'integration_enabled': self.integration_enabled,
            'errors': []
        }

    def measure_power(self) -> PowerMeasurement:
        """
        Perform comprehensive power measurement.

        Returns:
            PowerMeasurement object with all readings
        """
        try:
            # Query all power parameters
            v_rms = float(self.query("MEAS:VOLT:RMS?"))
            i_rms = float(self.query("MEAS:CURR:RMS?"))
            p_real = float(self.query("MEAS:POW:REAL?"))

            try:
                p_apparent = float(self.query("MEAS:POW:APP?"))
            except:
                p_apparent = v_rms * i_rms

            try:
                p_reactive = float(self.query("MEAS:POW:REAC?"))
            except:
                import math
                p_reactive = math.sqrt(p_apparent**2 - p_real**2)

            try:
                pf = float(self.query("MEAS:PF?"))
            except:
                pf = p_real / p_apparent if p_apparent > 0 else 0

            try:
                freq = float(self.query("MEAS:FREQ?"))
            except:
                freq = 60.0  # Default

            measurement = PowerMeasurement(
                voltage_rms=v_rms,
                current_rms=i_rms,
                power_real=p_real,
                power_apparent=p_apparent,
                power_reactive=p_reactive,
                power_factor=pf,
                frequency=freq,
                timestamp=time.time()
            )

            logger.debug(f"Power measurement: {p_real}W, PF={pf}")
            return measurement

        except Exception as e:
            raise InstrumentError(f"Power measurement failed: {e}")

    def start_integration(self):
        """Start power/energy integration"""
        try:
            self.write("SENS:INT:STAT ON")
            self.integration_enabled = True
            self.integration_start_time = time.time()

            logger.info("Integration started")

        except Exception as e:
            logger.warning(f"Could not start integration: {e}")

    def stop_integration(self):
        """Stop power/energy integration"""
        try:
            self.write("SENS:INT:STAT OFF")
            self.integration_enabled = False

            logger.info("Integration stopped")

        except Exception as e:
            logger.warning(f"Could not stop integration: {e}")

    def get_integration_results(self) -> Dict[str, float]:
        """
        Get integration results.

        Returns:
            Dictionary with Wh, Ah, and duration
        """
        try:
            wh = float(self.query("SENS:INT:POW?"))
            ah = float(self.query("SENS:INT:CURR?"))

            duration = 0
            if self.integration_start_time:
                duration = time.time() - self.integration_start_time

            return {
                'energy_wh': wh,
                'charge_ah': ah,
                'duration_s': duration,
            }

        except Exception as e:
            logger.warning(f"Could not get integration results: {e}")
            return {
                'energy_wh': 0,
                'charge_ah': 0,
                'duration_s': 0,
            }

    def measure_harmonics(self, order: int = 50) -> Dict[int, Tuple[float, float]]:
        """
        Measure voltage and current harmonics.

        Args:
            order: Maximum harmonic order to measure

        Returns:
            Dictionary mapping harmonic number to (voltage, current) amplitudes
        """
        harmonics = {}

        try:
            for n in range(1, order + 1):
                try:
                    v_harm = float(self.query(f"MEAS:HARM:VOLT? {n}"))
                    i_harm = float(self.query(f"MEAS:HARM:CURR? {n}"))
                    harmonics[n] = (v_harm, i_harm)
                except:
                    break

            logger.debug(f"Measured {len(harmonics)} harmonics")

        except Exception as e:
            logger.warning(f"Could not measure harmonics: {e}")

        return harmonics

    def measure_thd(self) -> Tuple[float, float]:
        """
        Measure Total Harmonic Distortion.

        Returns:
            Tuple of (THD voltage %, THD current %)
        """
        try:
            thd_v = float(self.query("MEAS:THD:VOLT?"))
            thd_i = float(self.query("MEAS:THD:CURR?"))

            logger.debug(f"THD: V={thd_v}%, I={thd_i}%")
            return (thd_v, thd_i)

        except Exception as e:
            logger.warning(f"Could not measure THD: {e}")
            return (0.0, 0.0)
