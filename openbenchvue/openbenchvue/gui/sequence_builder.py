"""
Sequence Builder Widget

Visual test sequence creation interface.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QSplitter, QLabel, QMessageBox,
    QInputDialog
)
from PyQt5.QtCore import Qt

from ..automation.sequence import Sequence, SequenceLoader
from ..automation.blocks import BLOCK_REGISTRY, get_block_categories
from ..automation.executor import SequenceExecutor, ExecutionContext

logger = logging.getLogger(__name__)


class SequenceBuilderWidget(QWidget):
    """
    Visual sequence builder.

    Provides BenchVue-like automation interface:
    - Block palette
    - Sequence editor
    - Execution controls
    - Save/load sequences
    """

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.sequence = Sequence()
        self.executor = None

        self._create_ui()

    def _create_ui(self):
        """Create sequence builder UI"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Test Automation</h3>"))
        header_layout.addStretch()

        self.run_button = QPushButton("▶ Run Sequence")
        self.run_button.clicked.connect(self._run_sequence)
        header_layout.addWidget(self.run_button)

        layout.addLayout(header_layout)

        # Splitter for blocks and sequence
        splitter = QSplitter(Qt.Horizontal)

        # Block palette
        palette_widget = QWidget()
        palette_layout = QVBoxLayout(palette_widget)
        palette_layout.addWidget(QLabel("<b>Block Palette</b>"))

        self.block_palette = QListWidget()
        self._populate_palette()
        palette_layout.addWidget(self.block_palette)

        add_button = QPushButton("+ Add to Sequence")
        add_button.clicked.connect(self._add_block)
        palette_layout.addWidget(add_button)

        palette_widget.setMaximumWidth(250)
        splitter.addWidget(palette_widget)

        # Sequence editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.addWidget(QLabel("<b>Sequence</b>"))

        self.sequence_list = QListWidget()
        editor_layout.addWidget(self.sequence_list)

        button_layout = QHBoxLayout()
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._remove_block)
        button_layout.addWidget(remove_button)

        move_up_button = QPushButton("↑ Move Up")
        move_up_button.clicked.connect(self._move_up)
        button_layout.addWidget(move_up_button)

        move_down_button = QPushButton("↓ Move Down")
        move_down_button.clicked.connect(self._move_down)
        button_layout.addWidget(move_down_button)

        button_layout.addStretch()

        editor_layout.addLayout(button_layout)

        splitter.addWidget(editor_widget)

        layout.addWidget(splitter)

        # Status
        self.status_label = QLabel("Ready to build sequence")
        layout.addWidget(self.status_label)

    def _populate_palette(self):
        """Populate block palette"""
        categories = get_block_categories()

        for category, blocks in categories.items():
            # Add category header
            self.block_palette.addItem(f"--- {category} ---")

            # Add blocks
            for block_name in blocks:
                # Find block class
                for class_name, block_class in BLOCK_REGISTRY.items():
                    if block_class.name == block_name:
                        item_text = f"{block_class.icon} {block_class.name}"
                        self.block_palette.addItem(item_text)
                        break

    def _add_block(self):
        """Add selected block to sequence"""
        selected = self.block_palette.currentItem()
        if not selected:
            return

        block_text = selected.text()
        if block_text.startswith("---"):
            return  # Category header

        # Extract block name (remove icon)
        block_name = block_text.split(" ", 1)[1] if " " in block_text else block_text

        # Find and create block
        for block_class in BLOCK_REGISTRY.values():
            if block_class.name == block_name:
                block = block_class()
                block.block_id = f"block_{len(self.sequence)}"
                self.sequence.add_block(block)

                # Add to list
                self.sequence_list.addItem(f"{block.icon} {block.name} ({block.block_id})")

                logger.info(f"Added block: {block.name}")
                break

        self._update_status()

    def _remove_block(self):
        """Remove selected block from sequence"""
        selected_row = self.sequence_list.currentRow()
        if selected_row >= 0:
            self.sequence.remove_block(selected_row)
            self.sequence_list.takeItem(selected_row)
            logger.info(f"Removed block at index {selected_row}")
            self._update_status()

    def _move_up(self):
        """Move block up"""
        row = self.sequence_list.currentRow()
        if row > 0:
            self.sequence.move_block(row, row - 1)
            item = self.sequence_list.takeItem(row)
            self.sequence_list.insertItem(row - 1, item)
            self.sequence_list.setCurrentRow(row - 1)

    def _move_down(self):
        """Move block down"""
        row = self.sequence_list.currentRow()
        if row < self.sequence_list.count() - 1:
            self.sequence.move_block(row, row + 1)
            item = self.sequence_list.takeItem(row)
            self.sequence_list.insertItem(row + 1, item)
            self.sequence_list.setCurrentRow(row + 1)

    def _run_sequence(self):
        """Run the sequence"""
        if len(self.sequence) == 0:
            QMessageBox.warning(self, "Empty Sequence", "Sequence has no blocks to execute.")
            return

        # Validate
        errors = self.sequence.validate()
        if errors:
            QMessageBox.warning(
                self,
                "Validation Errors",
                "Sequence has validation errors:\n\n" + "\n".join(errors)
            )
            return

        # Create execution context
        context = ExecutionContext(instruments=self.main_window.instruments)

        # Create executor
        self.executor = SequenceExecutor(self.sequence, context)

        # Execute
        self.status_label.setText("Executing sequence...")
        self.run_button.setEnabled(False)

        try:
            result = self.executor.start()

            # Show results
            if result.success:
                QMessageBox.information(
                    self,
                    "Execution Complete",
                    f"Sequence executed successfully!\n\n"
                    f"Blocks: {result.blocks_executed}\n"
                    f"Duration: {result.duration:.2f}s"
                )
                self.status_label.setText(f"Execution complete: {result.duration:.2f}s")
            else:
                error_msg = "\n".join(result.errors) if result.errors else "Unknown error"
                QMessageBox.warning(
                    self,
                    "Execution Failed",
                    f"Sequence execution failed:\n\n{error_msg}"
                )
                self.status_label.setText("Execution failed")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Execution error:\n{e}")
            logger.error(f"Execution error: {e}")

        finally:
            self.run_button.setEnabled(True)

    def _update_status(self):
        """Update status label"""
        self.status_label.setText(f"Sequence: {len(self.sequence)} blocks")

    def load_sequence(self, file_path: str):
        """Load sequence from file"""
        try:
            self.sequence = SequenceLoader.load(file_path)

            # Rebuild list
            self.sequence_list.clear()
            for block in self.sequence:
                self.sequence_list.addItem(f"{block.icon} {block.name} ({block.block_id})")

            self._update_status()
            logger.info(f"Loaded sequence: {file_path}")

        except Exception as e:
            logger.error(f"Failed to load sequence: {e}")
            raise

    def save_sequence(self, file_path: str):
        """Save sequence to file"""
        try:
            # Get sequence name
            name, ok = QInputDialog.getText(
                self,
                "Sequence Name",
                "Enter sequence name:",
                text=self.sequence.name
            )

            if ok and name:
                self.sequence.name = name

            SequenceLoader.save(self.sequence, file_path)
            logger.info(f"Saved sequence: {file_path}")

        except Exception as e:
            logger.error(f"Failed to save sequence: {e}")
            raise
