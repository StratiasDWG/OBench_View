"""
Clustering and Pattern Recognition for Measurements

Groups similar measurements and recognizes patterns.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """Represents a cluster of measurements"""
    id: int
    center: np.ndarray
    members: List[int]  # Indices of cluster members
    radius: float  # Maximum distance from center
    density: float  # Members per unit volume


class MeasurementClusterer:
    """
    Clusters measurement data using simple k-means style algorithm
    """

    def __init__(self, n_clusters: int = 3, max_iterations: int = 100):
        """
        Initialize clusterer

        Args:
            n_clusters: Number of clusters to find
            max_iterations: Maximum iterations for clustering
        """
        self.n_clusters = n_clusters
        self.max_iterations = max_iterations
        self.clusters: List[Cluster] = []

    def fit(self, data: np.ndarray) -> List[Cluster]:
        """
        Cluster the data

        Args:
            data: Array of measurements (can be multi-dimensional)

        Returns:
            List of clusters
        """
        if len(data) < self.n_clusters:
            logger.warning("Not enough data points for clustering")
            return []

        # Ensure 2D array
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        # Initialize centers randomly
        indices = np.random.choice(len(data), self.n_clusters, replace=False)
        centers = data[indices].copy()

        for iteration in range(self.max_iterations):
            # Assign points to nearest center
            assignments = self._assign_to_clusters(data, centers)

            # Update centers
            new_centers = np.zeros_like(centers)
            for i in range(self.n_clusters):
                cluster_points = data[assignments == i]
                if len(cluster_points) > 0:
                    new_centers[i] = np.mean(cluster_points, axis=0)
                else:
                    # Keep old center if cluster is empty
                    new_centers[i] = centers[i]

            # Check convergence
            if np.allclose(centers, new_centers):
                break

            centers = new_centers

        # Create cluster objects
        self.clusters = []
        for i in range(self.n_clusters):
            members = np.where(assignments == i)[0].tolist()
            if len(members) > 0:
                cluster_data = data[members]
                distances = np.linalg.norm(cluster_data - centers[i], axis=1)
                radius = np.max(distances) if len(distances) > 0 else 0

                # Estimate density
                volume = (radius ** data.shape[1]) if radius > 0 else 1
                density = len(members) / volume

                self.clusters.append(Cluster(
                    id=i,
                    center=centers[i],
                    members=members,
                    radius=radius,
                    density=density,
                ))

        return self.clusters

    def predict(self, data: np.ndarray) -> np.ndarray:
        """
        Predict cluster assignments for new data

        Args:
            data: Array of measurements

        Returns:
            Array of cluster IDs
        """
        if not self.clusters:
            raise ValueError("Clusterer not fitted yet")

        if data.ndim == 1:
            data = data.reshape(-1, 1)

        centers = np.array([c.center for c in self.clusters])
        return self._assign_to_clusters(data, centers)

    def _assign_to_clusters(self, data: np.ndarray, centers: np.ndarray) -> np.ndarray:
        """Assign data points to nearest cluster center"""
        distances = np.zeros((len(data), len(centers)))
        for i, center in enumerate(centers):
            distances[:, i] = np.linalg.norm(data - center, axis=1)
        return np.argmin(distances, axis=1)


class PatternRecognizer:
    """
    Recognizes common patterns in measurement sequences
    """

    def __init__(self, min_pattern_length: int = 5):
        """
        Initialize pattern recognizer

        Args:
            min_pattern_length: Minimum length of patterns to recognize
        """
        self.min_pattern_length = min_pattern_length
        self._known_patterns: Dict[str, np.ndarray] = {}

    def register_pattern(self, name: str, pattern: np.ndarray):
        """
        Register a known pattern

        Args:
            name: Name of the pattern
            pattern: Array representing the pattern
        """
        self._known_patterns[name] = np.array(pattern)
        logger.info(f"Registered pattern: {name}")

    def recognize(
        self,
        data: np.ndarray,
        tolerance: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Recognize patterns in data

        Args:
            data: Measurement sequence
            tolerance: Matching tolerance (as fraction of pattern amplitude)

        Returns:
            List of recognized pattern matches
        """
        matches = []

        for pattern_name, pattern in self._known_patterns.items():
            # Find matches using sliding window
            pattern_len = len(pattern)
            if len(data) < pattern_len:
                continue

            # Normalize pattern
            pattern_norm = self._normalize(pattern)

            for i in range(len(data) - pattern_len + 1):
                window = data[i:i + pattern_len]
                window_norm = self._normalize(window)

                # Compute similarity (correlation)
                similarity = self._similarity(pattern_norm, window_norm)

                if similarity > (1 - tolerance):
                    matches.append({
                        'pattern': pattern_name,
                        'start_index': i,
                        'end_index': i + pattern_len,
                        'similarity': similarity,
                        'confidence': similarity,
                    })

        return matches

    def detect_repeating_patterns(
        self,
        data: np.ndarray,
        min_repetitions: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Detect repeating patterns in data

        Args:
            data: Measurement sequence
            min_repetitions: Minimum number of repetitions to consider

        Returns:
            List of detected repeating patterns
        """
        patterns = []

        # Try different pattern lengths
        for length in range(self.min_pattern_length, len(data) // min_repetitions):
            # Check if data contains repeating pattern of this length
            repetitions = []

            for start in range(0, len(data) - length * min_repetitions + 1, length):
                candidate = data[start:start + length]
                candidate_norm = self._normalize(candidate)

                # Check for repetitions
                count = 1
                for offset in range(start + length, len(data) - length + 1, length):
                    window = data[offset:offset + length]
                    window_norm = self._normalize(window)

                    if self._similarity(candidate_norm, window_norm) > 0.9:
                        count += 1
                    else:
                        break

                if count >= min_repetitions:
                    repetitions.append({
                        'start_index': start,
                        'pattern_length': length,
                        'repetitions': count,
                        'pattern': candidate,
                    })

            if repetitions:
                # Keep best match for this length
                best = max(repetitions, key=lambda x: x['repetitions'])
                patterns.append(best)

        return patterns

    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize data to zero mean and unit variance"""
        mean = np.mean(data)
        std = np.std(data)
        if std > 0:
            return (data - mean) / std
        return data - mean

    def _similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute similarity between two sequences (normalized correlation)"""
        if len(a) != len(b):
            return 0.0

        correlation = np.corrcoef(a, b)[0, 1]
        return max(0, correlation)  # Only positive correlations
