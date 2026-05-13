#!/bin/sh
cd /Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/OpenCellComms/opencellcomms_engine/src/adapters/physicell_mechanics
rm -rf build _physicell_mechanics*.so
/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/OpenCellComms/.venv/bin/python setup.py build_ext --inplace
ls -la _physicell_mechanics*.so
echo REBUILD_OK
