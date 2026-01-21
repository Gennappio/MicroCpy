#!/usr/bin/env python3
"""
Setup script for OpenCellComms
"""

from setuptools import setup, find_packages

setup(
    name="opencellcomms",
    version="3.0.0",
    description="OpenCellComms - Biological Simulation Framework",
    author="OpenCellComms Team",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "numpy",
        "matplotlib",
        "fipy",
        "pyyaml",
        "scipy",
    ],
    extras_require={
        "dev": [
            "pytest",
            "flake8",
            "black",
        ]
    },
)
