"""
Predictive Analytics for Measurement Data

Trend analysis, drift detection, and forecasting capabilities.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trend:
    """Represents a detected trend"""
    direction: str  # 'increasing', 'decreasing', 'stable'
    slope: float
    confidence: float  # 0-1
    r_squared: float  # Goodness of fit
    forecast: Optional[np.ndarray] = None


class TrendAnalyzer:
    """
    Analyzes trends in measurement data

    Uses linear regression and statistical tests to detect and quantify trends.
    """

    def __init__(self, window_size: int = 100, min_slope: float = 0.001):
        """
        Initialize trend analyzer

        Args:
            window_size: Size of window for trend analysis
            min_slope: Minimum slope to consider as trending
        """
        self.window_size = window_size
        self.min_slope = min_slope
        self._values = deque(maxlen=window_size)
        self._timestamps = deque(maxlen=window_size)

    def add_measurement(self, value: float, timestamp: float):
        """Add a measurement"""
        self._values.append(value)
        self._timestamps.append(timestamp)

    def analyze(self) -> Optional[Trend]:
        """
        Analyze current trend

        Returns:
            Trend object if enough data, None otherwise
        """
        if len(self._values) < 10:
            return None

        # Convert to arrays
        x = np.array(self._timestamps)
        y = np.array(self._values)

        # Normalize time to avoid numerical issues
        x = x - x[0]

        # Linear regression
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs

        # Predictions
        y_pred = slope * x + intercept

        # R-squared
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine direction
        if abs(slope) < self.min_slope:
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        return Trend(
            direction=direction,
            slope=slope,
            confidence=r_squared,
            r_squared=r_squared,
        )

    def forecast(self, steps: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Forecast future values

        Args:
            steps: Number of steps to forecast

        Returns:
            Tuple of (timestamps, predicted_values)
        """
        if len(self._values) < 10:
            return np.array([]), np.array([])

        # Convert to arrays
        x = np.array(self._timestamps)
        y = np.array(self._values)

        # Normalize time
        x_norm = x - x[0]

        # Fit linear model
        coeffs = np.polyfit(x_norm, y, 1)
        slope, intercept = coeffs

        # Generate future timestamps
        last_time = x[-1]
        if len(x) > 1:
            time_step = np.mean(np.diff(x))
        else:
            time_step = 1.0

        future_times = last_time + time_step * np.arange(1, steps + 1)
        future_x_norm = future_times - x[0]

        # Predict
        predictions = slope * future_x_norm + intercept

        return future_times, predictions


class DriftDetector:
    """
    Detects drift in measurement statistics

    Monitors for changes in mean, variance, and distribution.
    """

    def __init__(
        self,
        reference_window: int = 100,
        test_window: int = 50,
        sensitivity: float = 0.05,
    ):
        """
        Initialize drift detector

        Args:
            reference_window: Size of reference window
            test_window: Size of test window
            sensitivity: Sensitivity for statistical tests (p-value threshold)
        """
        self.reference_window = reference_window
        self.test_window = test_window
        self.sensitivity = sensitivity

        self._reference = deque(maxlen=reference_window)
        self._test = deque(maxlen=test_window)
        self._all_values = deque(maxlen=reference_window + test_window)

    def add_measurement(self, value: float) -> Dict[str, Any]:
        """
        Add measurement and check for drift

        Returns:
            Dictionary with drift detection results
        """
        self._all_values.append(value)

        # Update windows
        if len(self._all_values) >= self.reference_window + self.test_window:
            values = list(self._all_values)
            self._reference = deque(values[:self.reference_window], maxlen=self.reference_window)
            self._test = deque(values[-self.test_window:], maxlen=self.test_window)
        elif len(self._all_values) >= self.reference_window:
            # Just starting test window
            self._reference = deque(list(self._all_values)[:self.reference_window], maxlen=self.reference_window)

        if len(self._reference) < self.reference_window or len(self._test) < self.test_window:
            return {'drift_detected': False, 'ready': False}

        # Compute statistics
        ref_array = np.array(self._reference)
        test_array = np.array(self._test)

        ref_mean = np.mean(ref_array)
        test_mean = np.mean(test_array)
        ref_std = np.std(ref_array)
        test_std = np.std(test_array)

        # Mean shift detection (Welch's t-test approximation)
        if ref_std > 0 and test_std > 0:
            t_stat = abs(test_mean - ref_mean) / np.sqrt(
                (ref_std ** 2 / len(ref_array)) +
                (test_std ** 2 / len(test_array))
            )
            # Simple threshold (proper t-test would use degrees of freedom)
            mean_drift = t_stat > 2.0  # Roughly p < 0.05
        else:
            mean_drift = False

        # Variance change detection
        if ref_std > 0:
            variance_ratio = test_std / ref_std
            variance_drift = variance_ratio > 2.0 or variance_ratio < 0.5
        else:
            variance_drift = False

        drift_detected = mean_drift or variance_drift

        return {
            'drift_detected': drift_detected,
            'ready': True,
            'mean_drift': mean_drift,
            'variance_drift': variance_drift,
            'reference_mean': ref_mean,
            'test_mean': test_mean,
            'mean_change': test_mean - ref_mean,
            'reference_std': ref_std,
            'test_std': test_std,
            'variance_ratio': test_std / ref_std if ref_std > 0 else None,
        }


class Forecaster:
    """
    Forecasts future measurements using simple time series methods
    """

    def __init__(self, method: str = 'linear', window_size: int = 100):
        """
        Initialize forecaster

        Args:
            method: Forecasting method ('linear', 'exponential', 'moving_average')
            window_size: Size of historical window
        """
        self.method = method
        self.window_size = window_size
        self._values = deque(maxlen=window_size)
        self._timestamps = deque(maxlen=window_size)

    def add_measurement(self, value: float, timestamp: float):
        """Add a measurement"""
        self._values.append(value)
        self._timestamps.append(timestamp)

    def forecast(
        self,
        steps: int,
        confidence_interval: float = 0.95
    ) -> Dict[str, np.ndarray]:
        """
        Forecast future values

        Args:
            steps: Number of steps to forecast
            confidence_interval: Confidence level for interval (0-1)

        Returns:
            Dictionary with 'timestamps', 'forecast', 'lower_bound', 'upper_bound'
        """
        if len(self._values) < 10:
            return {
                'timestamps': np.array([]),
                'forecast': np.array([]),
                'lower_bound': np.array([]),
                'upper_bound': np.array([]),
            }

        values = np.array(self._values)
        timestamps = np.array(self._timestamps)

        # Determine time step
        if len(timestamps) > 1:
            time_step = np.mean(np.diff(timestamps))
        else:
            time_step = 1.0

        # Generate future timestamps
        last_time = timestamps[-1]
        future_times = last_time + time_step * np.arange(1, steps + 1)

        if self.method == 'linear':
            # Linear regression forecast
            x_norm = timestamps - timestamps[0]
            coeffs = np.polyfit(x_norm, values, 1)
            slope, intercept = coeffs

            future_x_norm = future_times - timestamps[0]
            forecast = slope * future_x_norm + intercept

            # Estimate uncertainty from residuals
            fitted = slope * x_norm + intercept
            residuals = values - fitted
            std_error = np.std(residuals)

        elif self.method == 'moving_average':
            # Simple moving average
            window = min(10, len(values))
            last_avg = np.mean(values[-window:])
            forecast = np.full(steps, last_avg)

            # Uncertainty from recent variance
            std_error = np.std(values[-window:])

        elif self.method == 'exponential':
            # Exponential smoothing
            alpha = 0.3  # Smoothing factor
            forecast_values = []
            last_smooth = values[-1]

            for _ in range(steps):
                forecast_values.append(last_smooth)

            forecast = np.array(forecast_values)
            std_error = np.std(values) * 0.5

        else:
            # Default to last value
            forecast = np.full(steps, values[-1])
            std_error = np.std(values)

        # Confidence intervals (assuming normal distribution)
        z_score = 1.96 if confidence_interval >= 0.95 else 1.645
        margin = z_score * std_error * np.sqrt(1 + np.arange(steps) / len(values))

        return {
            'timestamps': future_times,
            'forecast': forecast,
            'lower_bound': forecast - margin,
            'upper_bound': forecast + margin,
        }
