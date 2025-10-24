# Contributing to OpenBenchVue

Thank you for your interest in contributing to OpenBenchVue! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and professional in all interactions. We welcome contributions from everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, VISA backend)
   - Log files if applicable

### Suggesting Features

1. Check existing feature requests
2. Create an issue describing:
   - Use case and motivation
   - Proposed implementation (if applicable)
   - How it relates to existing features

### Contributing Code

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/openbenchvue.git
   cd openbenchvue
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow PEP 8 style guidelines
   - Add docstrings to functions and classes
   - Include type hints where appropriate
   - Write unit tests for new functionality

4. **Test your changes**
   ```bash
   pytest tests/
   pylint openbenchvue/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: Brief description of changes"
   ```

6. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Coding Standards

### Style Guide

- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use descriptive variable names

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings:
  ```python
  def function(arg1: str, arg2: int) -> bool:
      """
      Brief description.

      Longer description if needed.

      Args:
          arg1: Description of arg1
          arg2: Description of arg2

      Returns:
          Description of return value

      Raises:
          ValueError: When condition occurs
      """
  ```

### Testing

- Write unit tests for new features
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage
- Test with multiple Python versions (3.10, 3.11, 3.12)

### Commit Messages

Use clear, descriptive commit messages:
- `Add: New feature description`
- `Fix: Bug description`
- `Update: Component changes`
- `Refactor: Code improvement`
- `Docs: Documentation changes`

## Adding New Instrument Drivers

To add support for a new instrument:

1. **Create driver file** in `openbenchvue/instruments/`
   ```python
   from .base import BaseInstrument, InstrumentType

   class NewInstrument(BaseInstrument):
       INSTRUMENT_TYPE = InstrumentType.XXX
       SUPPORTED_MODELS = [r'MODEL-\d{4}']

       def initialize(self):
           # Initialization code
           pass

       def get_capabilities(self):
           # Return capabilities dict
           pass

       def get_status(self):
           # Return status dict
           pass
   ```

2. **Register driver** in `instruments/__init__.py`

3. **Add tests** in `tests/test_instruments.py`

4. **Update documentation** in README.md and user guide

5. **Test with actual hardware** if possible

## Adding Automation Blocks

To add custom automation blocks:

1. **Create block class** in `automation/blocks.py`
   ```python
   class NewBlock(BaseBlock):
       name = "Block Name"
       category = "Category"
       description = "What this block does"

       def _define_parameters(self):
           self.add_parameter('param', 'type', default, 'Label')

       def execute(self, context):
           # Block logic
           return {'status': 'success'}
   ```

2. **Register block** in `BLOCK_REGISTRY`

3. **Add tests**

4. **Update documentation**

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- VISA backend (for testing with instruments)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/openbenchvue.git
cd openbenchvue

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-qt pytest-cov pylint black mypy
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openbenchvue --cov-report=html

# Run specific test file
pytest tests/test_instruments.py

# Run specific test
pytest tests/test_instruments.py::test_dmm_measure
```

### Code Quality

```bash
# Format code
black openbenchvue/

# Lint code
pylint openbenchvue/

# Type checking
mypy openbenchvue/
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation for changes
3. Add entry to CHANGELOG.md
4. Request review from maintainers
5. Address review comments
6. Maintainer will merge when approved

## Project Structure

```
openbenchvue/
├── openbenchvue/           # Main package
│   ├── instruments/        # Instrument drivers
│   ├── automation/         # Test automation
│   ├── data/               # Data handling
│   ├── gui/                # GUI components
│   ├── remote/             # Remote server
│   └── utils/              # Utilities
├── tests/                  # Unit tests
├── examples/               # Example sequences
├── docs/                   # Documentation
└── setup.py               # Package setup
```

## Areas Needing Contribution

### High Priority

- [ ] Additional instrument drivers
- [ ] Enhanced GUI components
- [ ] Mobile app for remote access
- [ ] Database backend for large datasets
- [ ] Advanced analysis plugins

### Medium Priority

- [ ] Dark theme for GUI
- [ ] Multi-language support
- [ ] Cloud data sync
- [ ] Improved error handling
- [ ] Performance optimizations

### Documentation

- [ ] Video tutorials
- [ ] API documentation
- [ ] Instrument-specific guides
- [ ] Troubleshooting database

## Questions?

- Open an issue for questions
- Join our discussion forum
- Email: developers@openbenchvue.org

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to OpenBenchVue!
