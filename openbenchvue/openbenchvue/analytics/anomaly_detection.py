"""
Anomaly Detection for Measurement Data

Detects anomalies in measurement streams using statistical and ML methods.

Example:
    # Create detector
    detector = StatisticalAnomalyDetector(window_size=100, sensitivity=3.0)

    # Add measurements
    for value in measurements:
        anomaly = detector.add_measurement(value, timestamp)
        if anomaly:
            print(f"Anomaly detected: {anomaly}")

    # Or use ML-based detector
    detector = IsolationForestDetector()
    detector.fit(historical_data)
    anomalies = detector.detect(new_data)
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from collections import deque
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of anomalies"""
    SPIKE = 'spike'                  # Sudden large deviation
    DROP = 'drop'                    # Sudden decrease
    DRIFT = 'drift'                  # Gradual trend change
    OUTLIER = 'outlier'              # Statistical outlier
    STUCK = 'stuck'                  # Value not changing
    NOISE = 'noise'                  # Excessive noise/variance
    PATTERN_BREAK = 'pattern_break'  # Expected pattern broken


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    type: AnomalyType
    timestamp: float
    value: float
    expected_value: Optional[float] = None
    confidence: float = 1.0  # 0-1
    severity: float = 1.0    # 0-1
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class AnomalyDetector(ABC):
    """Base class for anomaly detectors"""

    @abstractmethod
    def add_measurement(
        self,
        value: float,
        timestamp: Optional[float] = None
    ) -> Optional[Anomaly]:
        """
        Add a measurement and check for anomalies

        Args:
            value: Measurement value
            timestamp: Measurement timestamp

        Returns:
            Anomaly if detected, None otherwise
        """
        pass

    @abstractmethod
    def reset(self):
        """Reset detector state"""
        pass


class StatisticalAnomalyDetector(AnomalyDetector):
    """
    Statistical anomaly detection using moving statistics

    Detects anomalies based on standard deviation, rate of change,
    and other statistical measures.
    """

    def __init__(
        self,
        window_size: int = 100,
        sensitivity: float = 3.0,
        min_samples: int = 10,
        detect_stuck: bool = True,
        detect_noise: bool = True,
    ):
        """
        Initialize statistical detector

        Args:
            window_size: Size of moving window for statistics
            sensitivity: Number of standard deviations for outlier detection
            min_samples: Minimum samples before detecting anomalies
            detect_stuck: Detect stuck/unchanging values
            detect_noise: Detect excessive noise
        """
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.min_samples = min_samples
        self.detect_stuck = detect_stuck
        self.detect_noise = detect_noise

        self._values = deque(maxlen=window_size)
        self._timestamps = deque(maxlen=window_size)
        self._last_value = None
        self._stuck_count = 0

    def add_measurement(
        self,
        value: float,
        timestamp: Optional[float] = None
    ) -> Optional[Anomaly]:
        """Add measurement and check for anomalies"""
        import time
        if timestamp is None:
            timestamp = time.time()

        self._values.append(value)
        self._timestamps.append(timestamp)

        # Need minimum samples
        if len(self._values) < self.min_samples:
            self._last_value = value
            return None

        anomalies = []

        # Compute statistics
        values_array = np.array(self._values)
        mean = np.mean(values_array)
        std = np.std(values_array)

        # Spike/drop detection (Z-score)
        if std > 0:
            z_score = abs(value - mean) / std
            if z_score > self.sensitivity:
                anomaly_type = AnomalyType.SPIKE if value > mean else AnomalyType.DROP
                anomalies.append(Anomaly(
                    type=anomaly_type,
                    timestamp=timestamp,
                    value=value,
                    expected_value=mean,
                    confidence=min(z_score / (self.sensitivity * 2), 1.0),
                    severity=min(z_score / (self.sensitivity * 3), 1.0),
                    context={'z_score': z_score, 'std': std, 'mean': mean}
                ))

        # Stuck value detection
        if self.detect_stuck:
            if self._last_value is not None and abs(value - self._last_value) < 1e-10:
                self._stuck_count += 1
                if self._stuck_count > self.window_size * 0.5:
                    anomalies.append(Anomaly(
                        type=AnomalyType.STUCK,
                        timestamp=timestamp,
                        value=value,
                        confidence=min(self._stuck_count / self.window_size, 1.0),
                        severity=0.5,
                        context={'stuck_count': self._stuck_count}
                    ))
            else:
                self._stuck_count = 0

        # Noise detection (excessive variance)
        if self.detect_noise and len(self._values) >= self.window_size:
            # Check if recent variance is much higher than long-term
            recent_window = int(self.window_size * 0.2)
            recent_std = np.std(values_array[-recent_window:])

            if std > 0 and recent_std / std > 3.0:
                anomalies.append(Anomaly(
                    type=AnomalyType.NOISE,
                    timestamp=timestamp,
                    value=value,
                    confidence=min(recent_std / (std * 3), 1.0),
                    severity=0.6,
                    context={'recent_std': recent_std, 'long_term_std': std}
                ))

        # Drift detection (gradual trend change)
        if len(self._values) >= self.window_size:
            # Split window and compare means
            half = self.window_size // 2
            mean1 = np.mean(values_array[:half])
            mean2 = np.mean(values_array[half:])

            if std > 0:
                drift_score = abs(mean2 - mean1) / std
                if drift_score > self.sensitivity * 0.5:
                    anomalies.append(Anomaly(
                        type=AnomalyType.DRIFT,
                        timestamp=timestamp,
                        value=value,
                        expected_value=mean1,
                        confidence=min(drift_score / self.sensitivity, 1.0),
                        severity=0.7,
                        context={'drift_score': drift_score, 'mean_change': mean2 - mean1}
                    ))

        self._last_value = value

        # Return highest severity anomaly
        if anomalies:
            return max(anomalies, key=lambda a: a.severity)

        return None

    def reset(self):
        """Reset detector state"""
        self._values.clear()
        self._timestamps.clear()
        self._last_value = None
        self._stuck_count = 0


class IsolationForestDetector(AnomalyDetector):
    """
    ML-based anomaly detection using Isolation Forest

    Requires scikit-learn. Uses unsupervised learning to detect
    anomalies in multi-dimensional feature space.
    """

    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        features: Optional[List[str]] = None,
    ):
        """
        Initialize Isolation Forest detector

        Args:
            contamination: Expected proportion of anomalies
            n_estimators: Number of trees in forest
            features: List of feature names to extract
        """
        try:
            from sklearn.ensemble import IsolationForest
            self._model = IsolationForest(
                contamination=contamination,
                n_estimators=n_estimators,
                random_state=42,
            )
            self._sklearn_available = True
        except ImportError:
            logger.warning("scikit-learn not available, using fallback detector")
            self._model = None
            self._sklearn_available = False
            # Fallback to statistical detector
            self._fallback = StatisticalAnomalyDetector()

        self.features = features or ['value', 'rate_of_change', 'rolling_mean']
        self._fitted = False
        self._values = deque(maxlen=1000)
        self._timestamps = deque(maxlen=1000)

    def _extract_features(self, values: np.ndarray) -> np.ndarray:
        """Extract features from raw values"""
        features = []

        # Raw value
        features.append(values)

        # Rate of change
        if len(values) > 1:
            roc = np.diff(values, prepend=values[0])
        else:
            roc = np.zeros_like(values)
        features.append(roc)

        # Rolling mean
        window = min(10, len(values))
        rolling_mean = np.convolve(values, np.ones(window) / window, mode='same')
        features.append(rolling_mean)

        # Rolling std
        rolling_std = np.zeros_like(values)
        for i in range(len(values)):
            start = max(0, i - window + 1)
            rolling_std[i] = np.std(values[start:i+1])
        features.append(rolling_std)

        return np.column_stack(features)

    def fit(self, data: np.ndarray):
        """
        Fit the model on historical data

        Args:
            data: Historical measurement data
        """
        if not self._sklearn_available:
            logger.warning("Cannot fit: scikit-learn not available")
            return

        # Extract features
        X = self._extract_features(data)

        # Fit model
        self._model.fit(X)
        self._fitted = True
        logger.info(f"Fitted Isolation Forest on {len(data)} samples")

    def add_measurement(
        self,
        value: float,
        timestamp: Optional[float] = None
    ) -> Optional[Anomaly]:
        """Add measurement and check for anomalies"""
        import time
        if timestamp is None:
            timestamp = time.time()

        self._values.append(value)
        self._timestamps.append(timestamp)

        # Use fallback if sklearn not available
        if not self._sklearn_available:
            return self._fallback.add_measurement(value, timestamp)

        # Need to be fitted first
        if not self._fitted:
            if len(self._values) >= 100:
                # Auto-fit on collected data
                self.fit(np.array(self._values))
            return None

        # Extract features for current window
        values_array = np.array(self._values)
        X = self._extract_features(values_array)

        # Predict anomaly
        prediction = self._model.predict(X[-1:])

        if prediction[0] == -1:  # Anomaly detected
            # Get anomaly score
            score = -self._model.score_samples(X[-1:] )[0]

            return Anomaly(
                type=AnomalyType.OUTLIER,
                timestamp=timestamp,
                value=value,
                confidence=min(score, 1.0),
                severity=min(score * 1.5, 1.0),
                context={'anomaly_score': score, 'method': 'isolation_forest'}
            )

        return None

    def detect(self, data: np.ndarray) -> List[Anomaly]:
        """
        Detect anomalies in a batch of data

        Args:
            data: Array of measurements

        Returns:
            List of detected anomalies
        """
        if not self._sklearn_available or not self._fitted:
            return []

        # Extract features
        X = self._extract_features(data)

        # Predict
        predictions = self._model.predict(X)
        scores = -self._model.score_samples(X)

        # Create anomaly objects
        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:
                anomalies.append(Anomaly(
                    type=AnomalyType.OUTLIER,
                    timestamp=i,  # Use index as timestamp
                    value=data[i],
                    confidence=min(score, 1.0),
                    severity=min(score * 1.5, 1.0),
                    context={'anomaly_score': score, 'method': 'isolation_forest'}
                ))

        return anomalies

    def reset(self):
        """Reset detector state"""
        self._values.clear()
        self._timestamps.clear()
        self._fitted = False
        if hasattr(self, '_fallback'):
            self._fallback.reset()
