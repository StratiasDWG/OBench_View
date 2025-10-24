"""
Advanced Data Processor

Sophisticated signal processing and analytics:
- Real-time FFT with windowing
- Adaptive decimation
- Streaming statistics
- Waveform analysis
- Pattern detection
- Data quality metrics
"""

import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from scipy import signal, fft
from scipy.stats import kurtosis, skew
from collections import deque
import threading

logger = logging.getLogger(__name__)


class StreamingProcessor:
    """
    Real-time streaming data processor.

    Processes data as it arrives without storing entire dataset.
    """

    def __init__(self, buffer_size: int = 1000):
        """
        Initialize streaming processor.

        Args:
            buffer_size: Size of rolling buffer
        """
        self.buffer_size = buffer_size
        self._buffer = deque(maxlen=buffer_size)
        self._count = 0

        # Streaming statistics
        self._sum = 0.0
        self._sum_sq = 0.0
        self._min = float('inf')
        self._max = float('-inf')

        self._lock = threading.Lock()

    def add_sample(self, value: float):
        """
        Add sample to streaming processor.

        Args:
            value: Sample value
        """
        with self._lock:
            self._buffer.append(value)
            self._count += 1

            # Update streaming statistics
            self._sum += value
            self._sum_sq += value ** 2
            self._min = min(self._min, value)
            self._max = max(self._max, value)

    def get_statistics(self) -> Dict[str, float]:
        """
        Get current streaming statistics.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            if self._count == 0:
                return {
                    'count': 0,
                    'mean': 0,
                    'std': 0,
                    'min': 0,
                    'max': 0,
                    'rms': 0,
                }

            mean = self._sum / self._count
            variance = (self._sum_sq / self._count) - (mean ** 2)
            std = np.sqrt(max(0, variance))
            rms = np.sqrt(self._sum_sq / self._count)

            return {
                'count': self._count,
                'mean': float(mean),
                'std': float(std),
                'min': float(self._min),
                'max': float(self._max),
                'rms': float(rms),
                'variance': float(variance),
            }

    def get_buffer(self) -> np.ndarray:
        """Get current buffer as numpy array"""
        with self._lock:
            return np.array(list(self._buffer))

    def reset(self):
        """Reset processor"""
        with self._lock:
            self._buffer.clear()
            self._count = 0
            self._sum = 0.0
            self._sum_sq = 0.0
            self._min = float('inf')
            self._max = float('-inf')


class AdaptiveDecimator:
    """
    Adaptive decimation for reducing data rate while preserving features.

    Uses peak detection to keep important points.
    """

    def __init__(self, target_rate: float = 1000):
        """
        Initialize decimator.

        Args:
            target_rate: Target output rate (points/second)
        """
        self.target_rate = target_rate
        self._input_buffer = []
        self._input_times = []

    def add_points(self, time: np.ndarray, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Add points and decimate adaptively.

        Args:
            time: Time array
            data: Data array

        Returns:
            Tuple of (decimated_time, decimated_data)
        """
        # Add to buffer
        self._input_buffer.extend(data)
        self._input_times.extend(time)

        # Calculate current rate
        if len(self._input_times) < 2:
            return np.array([]), np.array([])

        duration = self._input_times[-1] - self._input_times[0]
        if duration == 0:
            return np.array([]), np.array([])

        current_rate = len(self._input_buffer) / duration

        # Determine decimation factor
        decimation_factor = max(1, int(current_rate / self.target_rate))

        if decimation_factor == 1:
            # No decimation needed
            result_time = np.array(self._input_times)
            result_data = np.array(self._input_buffer)
            self._input_buffer = []
            self._input_times = []
            return result_time, result_data

        # Adaptive decimation: keep peaks and min/max
        data_array = np.array(self._input_buffer)
        time_array = np.array(self._input_times)

        # Find peaks
        peaks, _ = signal.find_peaks(data_array, distance=decimation_factor)
        valleys, _ = signal.find_peaks(-data_array, distance=decimation_factor)

        # Combine peaks, valleys, and decimated points
        important_indices = set(peaks) | set(valleys)

        # Add regularly decimated points
        regular_indices = set(range(0, len(data_array), decimation_factor))

        # Combine all important indices
        keep_indices = sorted(important_indices | regular_indices)

        # Extract decimated data
        decimated_time = time_array[keep_indices]
        decimated_data = data_array[keep_indices]

        # Clear buffers
        self._input_buffer = []
        self._input_times = []

        return decimated_time, decimated_data


class RealTimeFFT:
    """
    Real-time FFT processor with windowing and overlap.
    """

    def __init__(self, fft_size: int = 1024, window: str = 'hann', overlap: float = 0.5):
        """
        Initialize FFT processor.

        Args:
            fft_size: FFT size (must be power of 2)
            window: Window function name
            overlap: Overlap ratio (0 to 1)
        """
        self.fft_size = fft_size
        self.window = signal.get_window(window, fft_size)
        self.overlap = overlap
        self.overlap_size = int(fft_size * overlap)

        self._buffer = deque(maxlen=fft_size)
        self._lock = threading.Lock()

    def add_samples(self, data: np.ndarray):
        """
        Add samples to FFT buffer.

        Args:
            data: Input samples
        """
        with self._lock:
            self._buffer.extend(data)

    def compute_fft(self, sample_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute FFT of buffered data.

        Args:
            sample_rate: Sample rate in Hz

        Returns:
            Tuple of (frequencies, magnitudes)
        """
        with self._lock:
            if len(self._buffer) < self.fft_size:
                return np.array([]), np.array([])

            # Get data from buffer
            data = np.array(list(self._buffer))[:self.fft_size]

            # Apply window
            windowed = data * self.window

            # Compute FFT
            fft_result = fft.fft(windowed)
            frequencies = fft.fftfreq(self.fft_size, 1/sample_rate)

            # Get positive frequencies
            positive_mask = frequencies > 0
            frequencies = frequencies[positive_mask]
            magnitudes = np.abs(fft_result[positive_mask]) * 2 / self.fft_size

            return frequencies, magnitudes

    def compute_power_spectrum(self, sample_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute power spectral density.

        Args:
            sample_rate: Sample rate in Hz

        Returns:
            Tuple of (frequencies, power)
        """
        with self._lock:
            if len(self._buffer) < self.fft_size:
                return np.array([]), np.array([])

            data = np.array(list(self._buffer))[:self.fft_size]

            # Compute PSD using Welch method
            frequencies, power = signal.welch(
                data,
                fs=sample_rate,
                window=self.window,
                nperseg=self.fft_size,
                noverlap=self.overlap_size
            )

            return frequencies, power


class WaveformAnalyzer:
    """
    Advanced waveform analysis.

    Extracts features and characteristics from waveforms.
    """

    @staticmethod
    def analyze_waveform(time: np.ndarray, data: np.ndarray) -> Dict[str, Any]:
        """
        Comprehensive waveform analysis.

        Args:
            time: Time array
            data: Data array

        Returns:
            Dictionary with analysis results
        """
        if len(data) < 2:
            return {}

        analysis = {}

        # Basic statistics
        analysis['mean'] = float(np.mean(data))
        analysis['std'] = float(np.std(data))
        analysis['min'] = float(np.min(data))
        analysis['max'] = float(np.max(data))
        analysis['peak_to_peak'] = float(np.ptp(data))
        analysis['rms'] = float(np.sqrt(np.mean(data**2)))

        # Distribution statistics
        analysis['skewness'] = float(skew(data))
        analysis['kurtosis'] = float(kurtosis(data))

        # AC component (remove DC)
        ac_data = data - np.mean(data)
        analysis['ac_rms'] = float(np.sqrt(np.mean(ac_data**2)))

        # Crest factor
        if analysis['rms'] > 0:
            analysis['crest_factor'] = float(np.max(np.abs(data)) / analysis['rms'])
        else:
            analysis['crest_factor'] = 0.0

        # Zero crossings
        zero_crossings = np.where(np.diff(np.sign(data)))[0]
        analysis['zero_crossings'] = len(zero_crossings)

        # Estimate frequency from zero crossings
        if len(zero_crossings) > 1 and len(time) > 1:
            duration = time[-1] - time[0]
            analysis['estimated_frequency'] = float(len(zero_crossings) / (2 * duration))
        else:
            analysis['estimated_frequency'] = 0.0

        # Peak detection
        peaks, peak_props = signal.find_peaks(data, prominence=np.ptp(data)*0.1)
        analysis['num_peaks'] = len(peaks)

        if len(peaks) > 0:
            analysis['peak_amplitudes'] = data[peaks].tolist()[:10]  # First 10

        # Rise/fall time estimation
        try:
            # Find 10% and 90% points
            data_range = np.ptp(data)
            low_threshold = np.min(data) + 0.1 * data_range
            high_threshold = np.min(data) + 0.9 * data_range

            rising_edges = []
            falling_edges = []

            for i in range(len(data) - 1):
                if data[i] < low_threshold and data[i+1] >= low_threshold:
                    # Rising edge start
                    for j in range(i, len(data)):
                        if data[j] >= high_threshold:
                            rise_time = time[j] - time[i]
                            rising_edges.append(rise_time)
                            break

                if data[i] > high_threshold and data[i+1] <= high_threshold:
                    # Falling edge start
                    for j in range(i, len(data)):
                        if data[j] <= low_threshold:
                            fall_time = time[j] - time[i]
                            falling_edges.append(fall_time)
                            break

            if rising_edges:
                analysis['rise_time'] = float(np.mean(rising_edges))
            if falling_edges:
                analysis['fall_time'] = float(np.mean(falling_edges))

        except Exception as e:
            logger.debug(f"Rise/fall time calculation failed: {e}")

        return analysis

    @staticmethod
    def detect_patterns(data: np.ndarray, pattern_type: str = 'sine') -> Dict[str, Any]:
        """
        Detect specific waveform patterns.

        Args:
            data: Data array
            pattern_type: Pattern to detect ('sine', 'square', 'ramp', 'pulse')

        Returns:
            Dictionary with pattern detection results
        """
        results = {'pattern': pattern_type, 'detected': False, 'confidence': 0.0}

        if len(data) < 10:
            return results

        # Normalize data
        data_norm = (data - np.mean(data)) / (np.std(data) + 1e-10)

        if pattern_type == 'sine':
            # Fit sine wave
            from scipy.optimize import curve_fit

            def sine_func(x, amplitude, frequency, phase, offset):
                return amplitude * np.sin(2 * np.pi * frequency * x + phase) + offset

            try:
                x = np.arange(len(data_norm))
                popt, _ = curve_fit(
                    sine_func, x, data_norm,
                    p0=[1.0, 0.01, 0.0, 0.0],
                    maxfev=1000
                )

                # Compute R² to measure fit quality
                fitted = sine_func(x, *popt)
                residuals = data_norm - fitted
                ss_res = np.sum(residuals**2)
                ss_tot = np.sum((data_norm - np.mean(data_norm))**2)

                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                results['detected'] = r_squared > 0.8
                results['confidence'] = float(r_squared)
                results['amplitude'] = float(popt[0])
                results['frequency'] = float(popt[1])
                results['phase'] = float(popt[2])

            except Exception as e:
                logger.debug(f"Sine fitting failed: {e}")

        elif pattern_type == 'square':
            # Detect square wave by counting rapid transitions
            diff = np.diff(data_norm)
            large_transitions = np.abs(diff) > np.std(diff) * 2
            num_transitions = np.sum(large_transitions)

            # Square wave should have periodic transitions
            results['detected'] = num_transitions > 4
            results['confidence'] = min(1.0, num_transitions / 10)

        return results


class DataQualityAnalyzer:
    """
    Analyze data quality and detect issues.
    """

    @staticmethod
    def analyze_quality(time: np.ndarray, data: np.ndarray) -> Dict[str, Any]:
        """
        Analyze data quality.

        Args:
            time: Time array
            data: Data array

        Returns:
            Dictionary with quality metrics
        """
        quality = {
            'total_points': len(data),
            'issues': [],
            'quality_score': 100.0
        }

        if len(data) == 0:
            quality['quality_score'] = 0.0
            quality['issues'].append('No data')
            return quality

        # Check for NaN/Inf
        num_nan = np.sum(np.isnan(data))
        num_inf = np.sum(np.isinf(data))

        if num_nan > 0:
            quality['issues'].append(f'{num_nan} NaN values')
            quality['quality_score'] -= 20

        if num_inf > 0:
            quality['issues'].append(f'{num_inf} Inf values')
            quality['quality_score'] -= 20

        # Check for constant values (dead signal)
        if np.std(data) < 1e-10:
            quality['issues'].append('Constant signal (no variation)')
            quality['quality_score'] -= 30

        # Check for clipping
        data_range = np.ptp(data)
        if data_range > 0:
            high_clip = np.sum(data >= (np.max(data) - 0.01 * data_range))
            low_clip = np.sum(data <= (np.min(data) + 0.01 * data_range))

            if high_clip > len(data) * 0.05:
                quality['issues'].append('Possible high clipping')
                quality['quality_score'] -= 15

            if low_clip > len(data) * 0.05:
                quality['issues'].append('Possible low clipping')
                quality['quality_score'] -= 15

        # Check sampling consistency
        if len(time) > 1:
            dt = np.diff(time)
            if np.std(dt) > np.mean(dt) * 0.1:
                quality['issues'].append('Inconsistent sampling rate')
                quality['quality_score'] -= 10

        # Check for outliers (using IQR method)
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        if iqr > 0:
            outliers = ((data < q1 - 3*iqr) | (data > q3 + 3*iqr))
            num_outliers = np.sum(outliers)

            if num_outliers > 0:
                outlier_pct = (num_outliers / len(data)) * 100
                if outlier_pct > 5:
                    quality['issues'].append(f'{outlier_pct:.1f}% outliers')
                    quality['quality_score'] -= 10

        quality['quality_score'] = max(0.0, quality['quality_score'])

        return quality
