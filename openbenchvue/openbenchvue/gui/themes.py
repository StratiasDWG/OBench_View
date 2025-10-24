"""
GUI Themes and Styling

Professional themes with dark mode support.
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt


class Theme:
    """Base theme class"""

    @staticmethod
    def apply(app: QApplication):
        """Apply theme to application"""
        raise NotImplementedError


class LightTheme(Theme):
    """Light theme with professional colors"""

    COLORS = {
        'primary': '#2196F3',
        'primary_dark': '#1976D2',
        'primary_light': '#BBDEFB',
        'accent': '#FF9800',
        'background': '#FAFAFA',
        'surface': '#FFFFFF',
        'error': '#F44336',
        'text': '#212121',
        'text_secondary': '#757575',
        'border': '#E0E0E0',
        'success': '#4CAF50',
        'warning': '#FFC107',
    }

    @staticmethod
    def apply(app: QApplication):
        """Apply light theme"""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.Window, QColor(LightTheme.COLORS['background']))
        palette.setColor(QPalette.WindowText, QColor(LightTheme.COLORS['text']))

        # Base colors
        palette.setColor(QPalette.Base, QColor(LightTheme.COLORS['surface']))
        palette.setColor(QPalette.AlternateBase, QColor('#F5F5F5'))

        # Text colors
        palette.setColor(QPalette.Text, QColor(LightTheme.COLORS['text']))
        palette.setColor(QPalette.BrightText, QColor('#000000'))

        # Button colors
        palette.setColor(QPalette.Button, QColor('#E0E0E0'))
        palette.setColor(QPalette.ButtonText, QColor(LightTheme.COLORS['text']))

        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(LightTheme.COLORS['primary']))
        palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))

        # Disabled colors
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor('#9E9E9E'))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#9E9E9E'))

        app.setPalette(palette)

        # Apply stylesheet
        stylesheet = f"""
            QMainWindow {{
                background-color: {LightTheme.COLORS['background']};
            }}

            QWidget {{
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 10pt;
            }}

            QPushButton {{
                background-color: {LightTheme.COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: {LightTheme.COLORS['primary_dark']};
            }}

            QPushButton:pressed {{
                background-color: #0D47A1;
            }}

            QPushButton:disabled {{
                background-color: #BDBDBD;
                color: #757575;
            }}

            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
                background-color: white;
                border: 2px solid {LightTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px;
            }}

            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border: 2px solid {LightTheme.COLORS['primary']};
            }}

            QGroupBox {{
                border: 2px solid {LightTheme.COLORS['border']};
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {LightTheme.COLORS['primary']};
            }}

            QTabWidget::pane {{
                border: 1px solid {LightTheme.COLORS['border']};
                border-radius: 4px;
            }}

            QTabBar::tab {{
                background-color: {LightTheme.COLORS['surface']};
                border: 1px solid {LightTheme.COLORS['border']};
                padding: 8px 20px;
                margin-right: 2px;
            }}

            QTabBar::tab:selected {{
                background-color: {LightTheme.COLORS['primary']};
                color: white;
            }}

            QTabBar::tab:hover {{
                background-color: {LightTheme.COLORS['primary_light']};
            }}

            QListWidget {{
                background-color: white;
                border: 1px solid {LightTheme.COLORS['border']};
                border-radius: 4px;
                padding: 4px;
            }}

            QListWidget::item:selected {{
                background-color: {LightTheme.COLORS['primary']};
                color: white;
            }}

            QListWidget::item:hover {{
                background-color: {LightTheme.COLORS['primary_light']};
            }}

            QProgressBar {{
                border: 2px solid {LightTheme.COLORS['border']};
                border-radius: 4px;
                text-align: center;
            }}

            QProgressBar::chunk {{
                background-color: {LightTheme.COLORS['primary']};
            }}

            QStatusBar {{
                background-color: {LightTheme.COLORS['surface']};
                border-top: 1px solid {LightTheme.COLORS['border']};
            }}

            QMenuBar {{
                background-color: {LightTheme.COLORS['surface']};
                border-bottom: 1px solid {LightTheme.COLORS['border']};
            }}

            QMenuBar::item:selected {{
                background-color: {LightTheme.COLORS['primary_light']};
            }}

            QMenu {{
                background-color: {LightTheme.COLORS['surface']};
                border: 1px solid {LightTheme.COLORS['border']};
            }}

            QMenu::item:selected {{
                background-color: {LightTheme.COLORS['primary']};
                color: white;
            }}

            QToolTip {{
                background-color: #424242;
                color: white;
                border: 1px solid #616161;
                padding: 6px;
                border-radius: 4px;
            }}
        """

        app.setStyleSheet(stylesheet)


class DarkTheme(Theme):
    """Dark theme for reduced eye strain"""

    COLORS = {
        'primary': '#1E88E5',
        'primary_dark': '#1565C0',
        'primary_light': '#64B5F6',
        'accent': '#FF9800',
        'background': '#121212',
        'surface': '#1E1E1E',
        'surface_variant': '#2C2C2C',
        'error': '#CF6679',
        'text': '#E0E0E0',
        'text_secondary': '#B0B0B0',
        'border': '#3A3A3A',
        'success': '#66BB6A',
        'warning': '#FFA726',
    }

    @staticmethod
    def apply(app: QApplication):
        """Apply dark theme"""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.Window, QColor(DarkTheme.COLORS['background']))
        palette.setColor(QPalette.WindowText, QColor(DarkTheme.COLORS['text']))

        # Base colors
        palette.setColor(QPalette.Base, QColor(DarkTheme.COLORS['surface']))
        palette.setColor(QPalette.AlternateBase, QColor(DarkTheme.COLORS['surface_variant']))

        # Text colors
        palette.setColor(QPalette.Text, QColor(DarkTheme.COLORS['text']))
        palette.setColor(QPalette.BrightText, QColor('#FFFFFF'))

        # Button colors
        palette.setColor(QPalette.Button, QColor(DarkTheme.COLORS['surface_variant']))
        palette.setColor(QPalette.ButtonText, QColor(DarkTheme.COLORS['text']))

        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(DarkTheme.COLORS['primary']))
        palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))

        # Disabled colors
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor('#616161'))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#616161'))

        # Link colors
        palette.setColor(QPalette.Link, QColor(DarkTheme.COLORS['primary_light']))

        app.setPalette(palette)

        # Apply stylesheet
        stylesheet = f"""
            QMainWindow {{
                background-color: {DarkTheme.COLORS['background']};
            }}

            QWidget {{
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 10pt;
                color: {DarkTheme.COLORS['text']};
            }}

            QPushButton {{
                background-color: {DarkTheme.COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: {DarkTheme.COLORS['primary_dark']};
            }}

            QPushButton:pressed {{
                background-color: #0D47A1;
            }}

            QPushButton:disabled {{
                background-color: #424242;
                color: #757575;
            }}

            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {{
                background-color: {DarkTheme.COLORS['surface_variant']};
                border: 2px solid {DarkTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px;
                color: {DarkTheme.COLORS['text']};
            }}

            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border: 2px solid {DarkTheme.COLORS['primary']};
            }}

            QGroupBox {{
                border: 2px solid {DarkTheme.COLORS['border']};
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                color: {DarkTheme.COLORS['text']};
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {DarkTheme.COLORS['primary_light']};
            }}

            QTabWidget::pane {{
                border: 1px solid {DarkTheme.COLORS['border']};
                border-radius: 4px;
                background-color: {DarkTheme.COLORS['surface']};
            }}

            QTabBar::tab {{
                background-color: {DarkTheme.COLORS['surface_variant']};
                border: 1px solid {DarkTheme.COLORS['border']};
                padding: 8px 20px;
                margin-right: 2px;
                color: {DarkTheme.COLORS['text']};
            }}

            QTabBar::tab:selected {{
                background-color: {DarkTheme.COLORS['primary']};
                color: white;
            }}

            QTabBar::tab:hover {{
                background-color: {DarkTheme.COLORS['surface']};
            }}

            QListWidget {{
                background-color: {DarkTheme.COLORS['surface']};
                border: 1px solid {DarkTheme.COLORS['border']};
                border-radius: 4px;
                padding: 4px;
                color: {DarkTheme.COLORS['text']};
            }}

            QListWidget::item:selected {{
                background-color: {DarkTheme.COLORS['primary']};
                color: white;
            }}

            QListWidget::item:hover {{
                background-color: {DarkTheme.COLORS['surface_variant']};
            }}

            QProgressBar {{
                border: 2px solid {DarkTheme.COLORS['border']};
                border-radius: 4px;
                text-align: center;
                background-color: {DarkTheme.COLORS['surface_variant']};
                color: {DarkTheme.COLORS['text']};
            }}

            QProgressBar::chunk {{
                background-color: {DarkTheme.COLORS['primary']};
            }}

            QStatusBar {{
                background-color: {DarkTheme.COLORS['surface']};
                border-top: 1px solid {DarkTheme.COLORS['border']};
                color: {DarkTheme.COLORS['text']};
            }}

            QMenuBar {{
                background-color: {DarkTheme.COLORS['surface']};
                border-bottom: 1px solid {DarkTheme.COLORS['border']};
                color: {DarkTheme.COLORS['text']};
            }}

            QMenuBar::item:selected {{
                background-color: {DarkTheme.COLORS['surface_variant']};
            }}

            QMenu {{
                background-color: {DarkTheme.COLORS['surface']};
                border: 1px solid {DarkTheme.COLORS['border']};
                color: {DarkTheme.COLORS['text']};
            }}

            QMenu::item:selected {{
                background-color: {DarkTheme.COLORS['primary']};
                color: white;
            }}

            QToolTip {{
                background-color: {DarkTheme.COLORS['surface_variant']};
                color: {DarkTheme.COLORS['text']};
                border: 1px solid {DarkTheme.COLORS['border']};
                padding: 6px;
                border-radius: 4px;
            }}

            QScrollBar:vertical {{
                background-color: {DarkTheme.COLORS['surface']};
                width: 14px;
                border-radius: 7px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {DarkTheme.COLORS['surface_variant']};
                border-radius: 7px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {DarkTheme.COLORS['border']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

        app.setStyleSheet(stylesheet)


class HighContrastTheme(Theme):
    """High contrast theme for accessibility"""

    COLORS = {
        'primary': '#00BCD4',
        'background': '#000000',
        'surface': '#1A1A1A',
        'text': '#FFFFFF',
        'border': '#FFFFFF',
        'error': '#FF0000',
        'success': '#00FF00',
        'warning': '#FFFF00',
    }

    @staticmethod
    def apply(app: QApplication):
        """Apply high contrast theme"""
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(HighContrastTheme.COLORS['background']))
        palette.setColor(QPalette.WindowText, QColor(HighContrastTheme.COLORS['text']))
        palette.setColor(QPalette.Base, QColor(HighContrastTheme.COLORS['surface']))
        palette.setColor(QPalette.Text, QColor(HighContrastTheme.COLORS['text']))
        palette.setColor(QPalette.Button, QColor('#333333'))
        palette.setColor(QPalette.ButtonText, QColor(HighContrastTheme.COLORS['text']))
        palette.setColor(QPalette.Highlight, QColor(HighContrastTheme.COLORS['primary']))
        palette.setColor(QPalette.HighlightedText, QColor('#000000'))

        app.setPalette(palette)

        stylesheet = f"""
            * {{
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 10pt;
                color: {HighContrastTheme.COLORS['text']};
            }}

            QPushButton {{
                background-color: {HighContrastTheme.COLORS['primary']};
                color: black;
                border: 2px solid white;
                padding: 8px 16px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: #00ACC1;
            }}

            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {HighContrastTheme.COLORS['surface']};
                border: 2px solid white;
                padding: 6px;
            }}

            QGroupBox {{
                border: 3px solid white;
                margin-top: 12px;
                font-weight: bold;
            }}

            QListWidget {{
                background-color: {HighContrastTheme.COLORS['surface']};
                border: 2px solid white;
            }}
        """

        app.setStyleSheet(stylesheet)


def get_theme(name: str) -> Theme:
    """
    Get theme by name.

    Args:
        name: Theme name ('light', 'dark', 'high_contrast')

    Returns:
        Theme class
    """
    themes = {
        'light': LightTheme,
        'dark': DarkTheme,
        'high_contrast': HighContrastTheme,
    }

    return themes.get(name.lower(), LightTheme)


def apply_theme(app: QApplication, theme_name: str):
    """
    Apply theme to application.

    Args:
        app: QApplication instance
        theme_name: Theme name
    """
    theme_class = get_theme(theme_name)
    theme_class.apply(app)
