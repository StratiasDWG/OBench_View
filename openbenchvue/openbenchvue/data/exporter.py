"""
Data Exporter

Export data to various formats (CSV, Excel, JSON, etc.).
"""

import logging
import csv
import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Data export utilities for multiple formats.

    Provides BenchVue-like export:
    - CSV format
    - Excel format
    - JSON format
    - Custom formats
    """

    @staticmethod
    def to_csv(
        data: Dict[str, tuple],
        file_path: str,
        delimiter: str = ',',
        header: bool = True
    ):
        """
        Export data to CSV file.

        Args:
            data: Dictionary mapping channel names to (time, values) tuples
            file_path: Output file path
            delimiter: CSV delimiter
            header: Include header row
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Get all channel names
            channels = list(data.keys())

            # Find maximum length
            max_length = max(len(data[ch][1]) for ch in channels)

            # Open file and write
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=delimiter)

                # Write header
                if header:
                    # Assume first channel has time data
                    header_row = ['Time'] + channels
                    writer.writerow(header_row)

                # Write data rows
                for i in range(max_length):
                    row = []

                    # Add time from first channel
                    if i < len(data[channels[0]][0]):
                        row.append(data[channels[0]][0][i])
                    else:
                        row.append('')

                    # Add values from each channel
                    for channel in channels:
                        if i < len(data[channel][1]):
                            row.append(data[channel][1][i])
                        else:
                            row.append('')

                    writer.writerow(row)

            logger.info(f"Exported {max_length} rows to CSV: {file_path}")

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise

    @staticmethod
    def to_excel(
        data: Dict[str, tuple],
        file_path: str,
        sheet_name: str = 'Data'
    ):
        """
        Export data to Excel file.

        Args:
            data: Dictionary mapping channel names to (time, values) tuples
            file_path: Output file path
            sheet_name: Excel sheet name
        """
        try:
            import pandas as pd

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Create DataFrame
            channels = list(data.keys())

            # Build data dict for DataFrame
            df_data = {}

            # Add time column from first channel
            df_data['Time'] = data[channels[0]][0]

            # Add value columns
            for channel in channels:
                df_data[channel] = data[channel][1]

            df = pd.DataFrame(df_data)

            # Export to Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            logger.info(f"Exported to Excel: {file_path}")

        except ImportError:
            logger.error("pandas and openpyxl required for Excel export")
            raise
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            raise

    @staticmethod
    def to_json(
        data: Dict[str, tuple],
        file_path: str,
        pretty: bool = True
    ):
        """
        Export data to JSON file.

        Args:
            data: Dictionary mapping channel names to (time, values) tuples
            file_path: Output file path
            pretty: Pretty-print JSON
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Convert numpy arrays to lists
            json_data = {}
            for channel, (time, values) in data.items():
                json_data[channel] = {
                    'time': time.tolist() if isinstance(time, np.ndarray) else list(time),
                    'values': values.tolist() if isinstance(values, np.ndarray) else list(values)
                }

            # Write JSON
            with open(path, 'w') as f:
                if pretty:
                    json.dump(json_data, f, indent=2)
                else:
                    json.dump(json_data, f)

            logger.info(f"Exported to JSON: {file_path}")

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise

    @staticmethod
    def to_numpy(
        data: Dict[str, tuple],
        file_path: str
    ):
        """
        Export data to NumPy .npz file.

        Args:
            data: Dictionary mapping channel names to (time, values) tuples
            file_path: Output file path
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare arrays for saving
            save_dict = {}
            for channel, (time, values) in data.items():
                save_dict[f'{channel}_time'] = time
                save_dict[f'{channel}_values'] = values

            # Save to .npz
            np.savez(path, **save_dict)

            logger.info(f"Exported to NumPy: {file_path}")

        except Exception as e:
            logger.error(f"NumPy export failed: {e}")
            raise

    @staticmethod
    def to_matlab(
        data: Dict[str, tuple],
        file_path: str
    ):
        """
        Export data to MATLAB .mat file.

        Args:
            data: Dictionary mapping channel names to (time, values) tuples
            file_path: Output file path
        """
        try:
            from scipy.io import savemat

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data for MATLAB format
            mat_data = {}
            for channel, (time, values) in data.items():
                mat_data[f'{channel}_time'] = time
                mat_data[f'{channel}_values'] = values

            # Save to .mat
            savemat(path, mat_data)

            logger.info(f"Exported to MATLAB: {file_path}")

        except Exception as e:
            logger.error(f"MATLAB export failed: {e}")
            raise

    @staticmethod
    def export_screenshot(
        figure,
        file_path: str,
        dpi: int = 300,
        format: str = 'png'
    ):
        """
        Export matplotlib figure as image.

        Args:
            figure: Matplotlib figure object
            file_path: Output file path
            dpi: Image resolution
            format: Image format ('png', 'jpg', 'pdf', 'svg')
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            figure.savefig(path, dpi=dpi, format=format, bbox_inches='tight')

            logger.info(f"Exported plot to: {file_path}")

        except Exception as e:
            logger.error(f"Screenshot export failed: {e}")
            raise
