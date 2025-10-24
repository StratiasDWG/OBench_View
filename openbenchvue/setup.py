"""
OpenBenchVue Setup Script
Install OpenBenchVue as a Python package
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

setup(
    name='openbenchvue',
    version='0.1.0',
    description='Open-source Python clone of Keysight PathWave BenchVue for instrument control and test automation',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='OpenBenchVue Contributors',
    author_email='openbenchvue@example.com',
    url='https://github.com/yourusername/openbenchvue',
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'pyvisa>=1.13.0',
        'pyvisa-py>=0.7.0',
        'PyQt5>=5.15.0',
        'numpy>=1.24.0',
        'scipy>=1.10.0',
        'pandas>=2.0.0',
        'matplotlib>=3.7.0',
        'seaborn>=0.12.0',
        'pyyaml>=6.0',
        'flask>=2.3.0',
        'flask-cors>=4.0.0',
        'python-dateutil>=2.8.0',
        'pytz>=2023.3',
        'colorlog>=6.7.0',
        'openpyxl>=3.1.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.3.0',
            'pytest-qt>=4.2.0',
            'black>=23.3.0',
            'pylint>=2.17.0',
            'mypy>=1.3.0',
        ],
        'performance': [
            'numba>=0.57.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'openbenchvue=openbenchvue.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Testing',
    ],
    keywords='test measurement instrument automation visa scpi oscilloscope dmm',
    include_package_data=True,
    zip_safe=False,
)
