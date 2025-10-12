#!/usr/bin/env python3
"""
Setup script for MicroC 2.0
"""

from setuptools import setup, find_packages

setup(
    name="microc-2.0",
    version="2.0.0",
    description="MicroC 2.0 - Biological Simulation Framework",
    author="MicroC Team",
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
