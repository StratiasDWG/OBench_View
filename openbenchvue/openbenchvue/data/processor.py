"""
Data Processor

Signal processing and analysis functions for measurement data.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from scipy import signal, fft
from scipy.stats import linregress

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Data processing and analysis utilities.

    Provides BenchVue-like analysis:
    - FFT and spectral analysis
    - Filtering (low-pass, high-pass, band-pass)
    - Statistical analysis
    - Trend analysis
    - Waveform measurements
    """

    @staticmethod
    def fft_analysis(
        time: np.ndarray,
        data: np.ndarray,
        window: str = 'hann'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform FFT analysis.

        Args:
            time: Time array
            data: Data array
            window: Window function ('hann', 'hamming', 'blackman')

        Returns:
            Tuple of (frequencies, magnitudes)
        """
        try:
            # Calculate sample rate
            dt = np.mean(np.diff(time))
            sample_rate = 1.0 / dt

            # Apply window
            window_func = signal.get_window(window, len(data))
            windowed_data = data * window_func

            # Compute FFT
            fft_result = fft.fft(windowed_data)
            frequencies = fft.fftfreq(len(data), dt)

            # Get positive frequencies only
            positive_mask = frequencies > 0
            frequencies = frequencies[positive_mask]
            magnitudes = np.abs(fft_result[positive_mask]) * 2 / len(data)

            logger.debug(f"FFT computed: {len(frequencies)} frequency bins")
            return frequencies, magnitudes

        except Exception as e:
            logger.error(f"FFT analysis failed: {e}")
            raise

    @staticmethod
    def power_spectrum(
        time: np.ndarray,
        data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute power spectral density.

        Args:
            time: Time array
            data: Data array

        Returns:
            Tuple of (frequencies, power)
        """
        try:
            dt = np.mean(np.diff(time))
            sample_rate = 1.0 / dt

            frequencies, power = signal.welch(data, fs=sample_rate)

            return frequencies, power

        except Exception as e:
            logger.error(f"Power spectrum failed: {e}")
            raise

    @staticmethod
    def filter_data(
        data: np.ndarray,
        sample_rate: float,
        filter_type: str = 'lowpass',
        cutoff: float = None,
        order: int = 4
    ) -> np.ndarray:
        """
        Apply digital filter to data.

        Args:
            data: Data array
            sample_rate: Sample rate in Hz
            filter_type: 'lowpass', 'highpass', 'bandpass', or 'bandstop'
            cutoff: Cutoff frequency or [low, high] for bandpass/bandstop
            order: Filter order

        Returns:
            Filtered data array
        """
        try:
            nyquist = sample_rate / 2

            if filter_type in ['lowpass', 'highpass']:
                if cutoff is None:
                    raise ValueError("Cutoff frequency required")
                normalized_cutoff = cutoff / nyquist
                b, a = signal.butter(order, normalized_cutoff, btype=filter_type)

            elif filter_type in ['bandpass', 'bandstop']:
                if not isinstance(cutoff, (list, tuple)) or len(cutoff) != 2:
                    raise ValueError("Bandpass/bandstop requires [low, high] cutoff")
                normalized_cutoff = [f / nyquist for f in cutoff]
                b, a = signal.butter(order, normalized_cutoff, btype=filter_type)

            else:
                raise ValueError(f"Unknown filter type: {filter_type}")

            # Apply filter
            filtered = signal.filtfilt(b, a, data)

            logger.debug(f"Applied {filter_type} filter with cutoff {cutoff}")
            return filtered

        except Exception as e:
            logger.error(f"Filtering failed: {e}")
            raise

    @staticmethod
    def statistics(data: np.ndarray) -> Dict[str, float]:
        """
        Calculate comprehensive statistics.

        Args:
            data: Data array

        Returns:
            Dictionary with statistical measures
        """
        return {
            'count': len(data),
            'mean': float(np.mean(data)),
            'median': float(np.median(data)),
            'std': float(np.std(data)),
            'var': float(np.var(data)),
            'min': float(np.min(data)),
            'max': float(np.max(data)),
            'range': float(np.ptp(data)),
            'rms': float(np.sqrt(np.mean(data**2))),
            'peak_to_peak': float(np.ptp(data)),
        }

    @staticmethod
    def find_peaks(
        data: np.ndarray,
        height: float = None,
        distance: int = None,
        prominence: float = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Find peaks in data.

        Args:
            data: Data array
            height: Minimum peak height
            distance: Minimum distance between peaks
            prominence: Minimum peak prominence

        Returns:
            Tuple of (peak_indices, properties)
        """
        try:
            peaks, properties = signal.find_peaks(
                data,
                height=height,
                distance=distance,
                prominence=prominence
            )

            logger.debug(f"Found {len(peaks)} peaks")
            return peaks, properties

        except Exception as e:
            logger.error(f"Peak finding failed: {e}")
            raise

    @staticmethod
    def trend_analysis(
        time: np.ndarray,
        data: np.ndarray
    ) -> Dict[str, float]:
        """
        Analyze data trend (linear regression).

        Args:
            time: Time array
            data: Data array

        Returns:
            Dictionary with slope, intercept, r-value
        """
        try:
            slope, intercept, r_value, p_value, std_err = linregress(time, data)

            return {
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_value**2),
                'p_value': float(p_value),
                'std_error': float(std_err)
            }

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            raise

    @staticmethod
    def moving_average(
        data: np.ndarray,
        window_size: int
    ) -> np.ndarray:
        """
        Calculate moving average.

        Args:
            data: Data array
            window_size: Window size for averaging

        Returns:
            Smoothed data array
        """
        try:
            window = np.ones(window_size) / window_size
            smoothed = np.convolve(data, window, mode='valid')

            return smoothed

        except Exception as e:
            logger.error(f"Moving average failed: {e}")
            raise

    @staticmethod
    def derivative(
        time: np.ndarray,
        data: np.ndarray
    ) -> np.ndarray:
        """
        Calculate numerical derivative.

        Args:
            time: Time array
            data: Data array

        Returns:
            Derivative array
        """
        try:
            derivative = np.gradient(data, time)
            return derivative

        except Exception as e:
            logger.error(f"Derivative calculation failed: {e}")
            raise

    @staticmethod
    def integrate(
        time: np.ndarray,
        data: np.ndarray
    ) -> float:
        """
        Numerical integration (trapezoidal rule).

        Args:
            time: Time array
            data: Data array

        Returns:
            Integral value
        """
        try:
            result = np.trapz(data, time)
            return float(result)

        except Exception as e:
            logger.error(f"Integration failed: {e}")
            raise

    @staticmethod
    def resample(
        time: np.ndarray,
        data: np.ndarray,
        new_sample_rate: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Resample data to new sample rate.

        Args:
            time: Original time array
            data: Original data array
            new_sample_rate: Target sample rate in Hz

        Returns:
            Tuple of (new_time, new_data)
        """
        try:
            duration = time[-1] - time[0]
            num_samples = int(duration * new_sample_rate)

            new_time = np.linspace(time[0], time[-1], num_samples)
            new_data = np.interp(new_time, time, data)

            logger.debug(f"Resampled from {len(data)} to {len(new_data)} points")
            return new_time, new_data

        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            raise

    @staticmethod
    def correlation(
        data1: np.ndarray,
        data2: np.ndarray
    ) -> float:
        """
        Calculate correlation coefficient.

        Args:
            data1: First data array
            data2: Second data array

        Returns:
            Correlation coefficient (-1 to 1)
        """
        try:
            correlation = np.corrcoef(data1, data2)[0, 1]
            return float(correlation)

        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            raise

    @staticmethod
    def histogram(
        data: np.ndarray,
        bins: int = 50
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate histogram.

        Args:
            data: Data array
            bins: Number of bins

        Returns:
            Tuple of (counts, bin_edges)
        """
        try:
            counts, bin_edges = np.histogram(data, bins=bins)
            return counts, bin_edges

        except Exception as e:
            logger.error(f"Histogram calculation failed: {e}")
            raise
