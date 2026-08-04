"""Forward legacy root-level setup invocations to the engine package."""

import os
import runpy
from pathlib import Path


ENGINE_DIR = Path(__file__).resolve().parent / "opencellcomms_engine"
os.chdir(ENGINE_DIR)
runpy.run_path(str(ENGINE_DIR / "setup.py"), run_name="__main__")
