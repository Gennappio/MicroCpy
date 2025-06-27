#!/usr/bin/env python3
"""
MicroC Setup Script
Multi-scale cellular simulation platform
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "MicroC: Multi-scale cellular simulation platform"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    if os.path.exists(req_path):
        with open(req_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
    return requirements

setup(
    name="microc",
    version="2.0.0",
    description="Multi-scale cellular simulation platform with gene networks and spatial dynamics",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="MicroC Development Team",
    author_email="microc@example.com",
    url="https://github.com/microc/microc",
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Include data files
    package_data={
        "": ["*.yaml", "*.yml", "*.bnd", "*.txt", "*.md"],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=read_requirements(),
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.17.0",
        ],
        "jupyter": [
            "jupyter>=1.0.0",
            "ipykernel>=6.0.0",
            "notebook>=6.4.0",
        ],
        "performance": [
            "numba>=0.56.0",
            "cython>=0.29.0",
            "joblib>=1.1.0",
        ],
        "visualization": [
            "mayavi>=4.7.0",
            "vtk>=9.0.0",
        ],
    },
    
    # Entry points
    entry_points={
        "console_scripts": [
            "microc-run=microc.cli:main",
            "microc-analyze=microc.analysis:main",
            "microc-plot=microc.visualization:main",
        ],
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Keywords
    keywords="cellular simulation, gene networks, systems biology, spatial modeling",
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/microc/microc/issues",
        "Source": "https://github.com/microc/microc",
        "Documentation": "https://microc.readthedocs.io/",
    },
)
