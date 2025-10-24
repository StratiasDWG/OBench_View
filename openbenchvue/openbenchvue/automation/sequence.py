"""
Test Sequence Data Structures

Defines sequence data model and serialization (YAML/JSON).
"""

import logging
import yaml
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .blocks import BaseBlock, BLOCK_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class Sequence:
    """
    Test sequence containing ordered blocks.

    Mimics BenchVue's sequence concept where users build
    automated tests by arranging blocks visually.
    """

    name: str = "Untitled Sequence"
    description: str = ""
    blocks: List[BaseBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_block(self, block: BaseBlock, index: Optional[int] = None):
        """Add block to sequence"""
        if index is None:
            self.blocks.append(block)
        else:
            self.blocks.insert(index, block)

    def remove_block(self, block_or_index):
        """Remove block by reference or index"""
        if isinstance(block_or_index, int):
            del self.blocks[block_or_index]
        else:
            self.blocks.remove(block_or_index)

    def move_block(self, from_index: int, to_index: int):
        """Move block to different position"""
        block = self.blocks.pop(from_index)
        self.blocks.insert(to_index, block)

    def get_block(self, block_id: str) -> Optional[BaseBlock]:
        """Get block by ID"""
        for block in self.blocks:
            if block.block_id == block_id:
                return block
        return None

    def validate(self) -> List[str]:
        """
        Validate entire sequence.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.blocks:
            errors.append("Sequence has no blocks")

        for i, block in enumerate(self.blocks):
            block_errors = block.validate()
            for error in block_errors:
                errors.append(f"Block {i} ({block.name}): {error}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize sequence to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'metadata': self.metadata,
            'blocks': [block.to_dict() for block in self.blocks]
        }

    def to_yaml(self) -> str:
        """Serialize to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    def save(self, file_path: str, format: str = 'yaml'):
        """
        Save sequence to file.

        Args:
            file_path: Path to save to
            format: 'yaml' or 'json'
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w') as f:
                if format == 'json':
                    f.write(self.to_json())
                else:
                    f.write(self.to_yaml())

            logger.info(f"Saved sequence to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save sequence: {e}")
            raise

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Sequence':
        """Deserialize sequence from dictionary"""
        sequence = cls(
            name=data.get('name', 'Untitled Sequence'),
            description=data.get('description', ''),
            metadata=data.get('metadata', {})
        )

        # Reconstruct blocks
        for block_data in data.get('blocks', []):
            block_type = block_data.get('type')

            if block_type in BLOCK_REGISTRY:
                block_class = BLOCK_REGISTRY[block_type]
                block = block_class.from_dict(block_data)
                sequence.add_block(block)
            else:
                logger.warning(f"Unknown block type: {block_type}")

        return sequence

    @classmethod
    def from_yaml(cls, yaml_string: str) -> 'Sequence':
        """Deserialize from YAML string"""
        data = yaml.safe_load(yaml_string)
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, json_string: str) -> 'Sequence':
        """Deserialize from JSON string"""
        data = json.loads(json_string)
        return cls.from_dict(data)

    def __len__(self):
        return len(self.blocks)

    def __iter__(self):
        return iter(self.blocks)

    def __repr__(self):
        return f"Sequence('{self.name}', {len(self.blocks)} blocks)"


class SequenceLoader:
    """
    Utility class for loading/saving sequences.
    """

    @staticmethod
    def load(file_path: str) -> Sequence:
        """
        Load sequence from file.

        Args:
            file_path: Path to sequence file (.yaml or .json)

        Returns:
            Loaded Sequence object
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"Sequence file not found: {file_path}")

            with open(path, 'r') as f:
                content = f.read()

            # Determine format from extension
            if path.suffix.lower() in ['.yaml', '.yml']:
                sequence = Sequence.from_yaml(content)
            elif path.suffix.lower() == '.json':
                sequence = Sequence.from_json(content)
            else:
                # Try YAML first, then JSON
                try:
                    sequence = Sequence.from_yaml(content)
                except:
                    sequence = Sequence.from_json(content)

            logger.info(f"Loaded sequence from {file_path}")
            return sequence

        except Exception as e:
            logger.error(f"Failed to load sequence: {e}")
            raise

    @staticmethod
    def save(sequence: Sequence, file_path: str, format: str = None):
        """
        Save sequence to file.

        Args:
            sequence: Sequence to save
            file_path: Path to save to
            format: 'yaml' or 'json' (auto-detect from extension if None)
        """
        if format is None:
            # Determine from extension
            path = Path(file_path)
            if path.suffix.lower() == '.json':
                format = 'json'
            else:
                format = 'yaml'

        sequence.save(file_path, format)

    @staticmethod
    def create_example_sequence() -> Sequence:
        """Create example sequence for demonstration"""
        from .blocks import (
            CommentBlock, SetVoltageBlock, SetCurrentBlock,
            OutputEnableBlock, DelayBlock, MeasureBlock, LogDataBlock
        )

        sequence = Sequence(
            name="Example Power Supply Test",
            description="Demonstrates basic power supply control and measurement"
        )

        # Comment
        comment = CommentBlock()
        comment.block_id = "comment1"
        comment.set_parameter('text', "Configure power supply for 5V, 1A output")
        sequence.add_block(comment)

        # Set voltage
        set_v = SetVoltageBlock()
        set_v.block_id = "set_voltage1"
        set_v.set_parameter('instrument', 'PSU1')
        set_v.set_parameter('channel', 1)
        set_v.set_parameter('voltage', 5.0)
        sequence.add_block(set_v)

        # Set current
        set_i = SetCurrentBlock()
        set_i.block_id = "set_current1"
        set_i.set_parameter('instrument', 'PSU1')
        set_i.set_parameter('channel', 1)
        set_i.set_parameter('current', 1.0)
        sequence.add_block(set_i)

        # Enable output
        enable = OutputEnableBlock()
        enable.block_id = "enable1"
        enable.set_parameter('instrument', 'PSU1')
        enable.set_parameter('channel', 1)
        enable.set_parameter('enable', True)
        sequence.add_block(enable)

        # Delay
        delay = DelayBlock()
        delay.block_id = "delay1"
        delay.set_parameter('duration', 2.0)
        sequence.add_block(delay)

        # Measure
        measure = MeasureBlock()
        measure.block_id = "measure1"
        measure.set_parameter('instrument', 'DMM1')
        measure.set_parameter('variable', 'voltage')
        sequence.add_block(measure)

        # Log
        log = LogDataBlock()
        log.block_id = "log1"
        log.set_parameter('variable', 'voltage')
        log.set_parameter('label', 'Output Voltage')
        sequence.add_block(log)

        # Disable output
        disable = OutputEnableBlock()
        disable.block_id = "disable1"
        disable.set_parameter('instrument', 'PSU1')
        disable.set_parameter('channel', 1)
        disable.set_parameter('enable', False)
        sequence.add_block(disable)

        return sequence
