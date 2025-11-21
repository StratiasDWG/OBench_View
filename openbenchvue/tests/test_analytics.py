"""
Tests for analytics modules
"""

import pytest
import numpy as np
from openbenchvue.analytics import (
    StatisticalAnomalyDetector,
    IsolationForestDetector,
    AnomalyType,
    TrendAnalyzer,
    DriftDetector,
    Forecaster,
    MeasurementClusterer,
    PatternRecognizer,
)


class TestAnomalyDetection:
    """Tests for anomaly detection"""

    def test_statistical_spike_detection(self):
        """Test spike detection"""
        detector = StatisticalAnomalyDetector(sensitivity=3.0)

        # Add normal values
        for i in range(50):
            detector.add_measurement(5.0 + np.random.normal(0, 0.1))

        # Add a spike
        anomaly = detector.add_measurement(10.0)

        assert anomaly is not None
        assert anomaly.type in [AnomalyType.SPIKE, AnomalyType.OUTLIER]

    def test_statistical_drop_detection(self):
        """Test drop detection"""
        detector = StatisticalAnomalyDetector(sensitivity=3.0)

        # Add normal values
        for i in range(50):
            detector.add_measurement(5.0 + np.random.normal(0, 0.1))

        # Add a drop
        anomaly = detector.add_measurement(0.0)

        assert anomaly is not None
        assert anomaly.type in [AnomalyType.DROP, AnomalyType.OUTLIER]

    def test_stuck_value_detection(self):
        """Test stuck value detection"""
        detector = StatisticalAnomalyDetector(detect_stuck=True, window_size=20)

        # Add varying values first
        for i in range(10):
            detector.add_measurement(5.0 + i * 0.1)

        # Add stuck values
        anomaly = None
        for i in range(15):
            anomaly = detector.add_measurement(10.0)

        assert anomaly is not None
        assert anomaly.type == AnomalyType.STUCK

    def test_drift_detection(self):
        """Test drift detection"""
        detector = StatisticalAnomalyDetector(window_size=100, sensitivity=2.0)

        # First half: mean around 5
        for i in range(50):
            detector.add_measurement(5.0 + np.random.normal(0, 0.5))

        # Second half: mean around 10 (drift)
        anomaly = None
        for i in range(50):
            anomaly = detector.add_measurement(10.0 + np.random.normal(0, 0.5))

        # Should eventually detect drift
        assert anomaly is not None

    def test_isolation_forest(self):
        """Test Isolation Forest detector"""
        detector = IsolationForestDetector(contamination=0.1)

        # Generate normal data
        normal_data = np.random.normal(5, 1, 100)

        # Fit detector
        detector.fit(normal_data)

        # Add normal values (should not trigger)
        anomaly = detector.add_measurement(5.0)
        # May or may not detect initially

        # Add obvious anomaly
        anomaly = detector.add_measurement(50.0)
        # Note: Isolation Forest may not always detect single point
        # This test is more about ensuring it runs without error

    def test_reset_detector(self):
        """Test detector reset"""
        detector = StatisticalAnomalyDetector()

        for i in range(50):
            detector.add_measurement(5.0)

        detector.reset()

        # Should not have enough samples after reset
        anomaly = detector.add_measurement(100.0)
        assert anomaly is None  # Not enough samples yet


class TestPredictive:
    """Tests for predictive analytics"""

    def test_trend_analysis_increasing(self):
        """Test increasing trend detection"""
        analyzer = TrendAnalyzer(window_size=50, min_slope=0.01)

        # Add increasing values
        for i in range(50):
            analyzer.add_measurement(i * 0.1, timestamp=i)

        trend = analyzer.analyze()

        assert trend is not None
        assert trend.direction == 'increasing'
        assert trend.slope > 0

    def test_trend_analysis_decreasing(self):
        """Test decreasing trend detection"""
        analyzer = TrendAnalyzer(window_size=50, min_slope=0.01)

        # Add decreasing values
        for i in range(50):
            analyzer.add_measurement(10.0 - i * 0.1, timestamp=i)

        trend = analyzer.analyze()

        assert trend is not None
        assert trend.direction == 'decreasing'
        assert trend.slope < 0

    def test_trend_analysis_stable(self):
        """Test stable trend detection"""
        analyzer = TrendAnalyzer(window_size=50, min_slope=0.1)

        # Add stable values
        for i in range(50):
            analyzer.add_measurement(5.0 + np.random.normal(0, 0.01), timestamp=i)

        trend = analyzer.analyze()

        assert trend is not None
        assert trend.direction == 'stable'

    def test_forecasting(self):
        """Test forecasting"""
        analyzer = TrendAnalyzer()

        # Add linear trend
        for i in range(50):
            analyzer.add_measurement(i * 0.5, timestamp=i)

        # Forecast next 10 steps
        times, predictions = analyzer.forecast(10)

        assert len(times) == 10
        assert len(predictions) == 10
        # Predictions should continue the trend
        assert predictions[0] > 24  # Should be around 25

    def test_drift_detector(self):
        """Test drift detection"""
        detector = DriftDetector(reference_window=50, test_window=25)

        # Add reference data (mean around 5)
        for i in range(50):
            detector.add_measurement(5.0 + np.random.normal(0, 0.5))

        # Add test data (mean around 5, no drift)
        for i in range(24):
            result = detector.add_measurement(5.0 + np.random.normal(0, 0.5))

        result = detector.add_measurement(5.0)
        assert result['ready']
        assert not result['drift_detected']

        # Now add drifted data
        detector2 = DriftDetector(reference_window=50, test_window=25)
        for i in range(50):
            detector2.add_measurement(5.0 + np.random.normal(0, 0.5))

        # Add drifted test data (mean around 10)
        for i in range(25):
            result = detector2.add_measurement(10.0 + np.random.normal(0, 0.5))

        assert result['ready']
        assert result['drift_detected']

    def test_forecaster_linear(self):
        """Test linear forecaster"""
        forecaster = Forecaster(method='linear')

        # Add linear trend
        for i in range(50):
            forecaster.add_measurement(i * 2.0, timestamp=i)

        # Forecast
        result = forecaster.forecast(10)

        assert len(result['forecast']) == 10
        assert len(result['lower_bound']) == 10
        assert len(result['upper_bound']) == 10

        # Check forecast is reasonable
        assert result['forecast'][0] > 95  # Should be around 100

    def test_forecaster_moving_average(self):
        """Test moving average forecaster"""
        forecaster = Forecaster(method='moving_average')

        # Add values
        for i in range(50):
            forecaster.add_measurement(5.0 + np.random.normal(0, 0.5), timestamp=i)

        # Forecast
        result = forecaster.forecast(10)

        # Forecast should be around the mean
        assert 4.0 < result['forecast'][0] < 6.0


class TestClustering:
    """Tests for clustering"""

    def test_clustering_basic(self):
        """Test basic clustering"""
        clusterer = MeasurementClusterer(n_clusters=2)

        # Generate two distinct groups
        group1 = np.random.normal(5, 0.5, 50)
        group2 = np.random.normal(15, 0.5, 50)
        data = np.concatenate([group1, group2])

        clusters = clusterer.fit(data)

        assert len(clusters) == 2
        # Centers should be around 5 and 15
        centers = sorted([c.center[0] for c in clusters])
        assert 4 < centers[0] < 6
        assert 14 < centers[1] < 16

    def test_clustering_prediction(self):
        """Test cluster prediction"""
        clusterer = MeasurementClusterer(n_clusters=2)

        # Fit on two groups
        group1 = np.random.normal(5, 0.5, 50)
        group2 = np.random.normal(15, 0.5, 50)
        data = np.concatenate([group1, group2])
        clusterer.fit(data)

        # Predict new points
        predictions = clusterer.predict(np.array([4.5, 15.5]))

        # Should assign to different clusters
        assert predictions[0] != predictions[1]

    def test_pattern_recognition(self):
        """Test pattern recognition"""
        recognizer = PatternRecognizer()

        # Register a sine-like pattern
        pattern = np.sin(np.linspace(0, 2 * np.pi, 20))
        recognizer.register_pattern("sine", pattern)

        # Create data with the pattern
        data = np.concatenate([
            np.random.normal(0, 0.1, 10),
            pattern + np.random.normal(0, 0.05, 20),
            np.random.normal(0, 0.1, 10),
        ])

        # Recognize pattern
        matches = recognizer.recognize(data, tolerance=0.2)

        assert len(matches) > 0
        assert matches[0]['pattern'] == "sine"

    def test_repeating_pattern_detection(self):
        """Test repeating pattern detection"""
        recognizer = PatternRecognizer(min_pattern_length=5)

        # Create repeating pattern
        pattern = np.array([1, 2, 3, 2, 1])
        data = np.tile(pattern, 4)  # Repeat 4 times

        # Detect repeating patterns
        patterns = recognizer.detect_repeating_patterns(data, min_repetitions=2)

        assert len(patterns) > 0
        # Should find the pattern
        found = any(p['pattern_length'] == 5 for p in patterns)
        assert found
