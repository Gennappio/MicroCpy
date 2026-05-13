#!/bin/sh
# Force rebuild of the _physicell_mechanics extension.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
rm -rf build _physicell_mechanics*.so
"${PY:-python3}" setup.py build_ext --inplace
ls -la _physicell_mechanics*.so
echo REBUILD_OK
