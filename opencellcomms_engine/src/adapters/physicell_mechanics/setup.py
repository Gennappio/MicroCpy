"""
Build script for the _physicell_mechanics pybind11 extension.

Usage (from this directory):
    python setup.py build_ext --inplace

This produces _physicell_mechanics.cpython-*.so in the same directory,
which can then be imported as `from src.adapters.physicell_mechanics import _physicell_mechanics`.
"""

from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "_physicell_mechanics",
        ["mechanics.cpp"],
        cxx_std=17,
        extra_compile_args=["-O3", "-ffast-math"],
    ),
]

setup(
    name="_physicell_mechanics",
    version="0.1.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
