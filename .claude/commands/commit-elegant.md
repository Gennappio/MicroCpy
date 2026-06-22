# /commit-elegamt — commit last changes

give a look at the last changes that are not committed. then evaluate 
gorup them by task accomplished / bug solved / new feature implemented in a reasonable way. Give the commits a brief but comprehensive descrtption. No mention to AI or to the author

Note: a pre-commit hook (`.pre-commit-config.yaml`, activated with `pre-commit install`) runs the fast engine test suite (`pytest -m "not slow"`, ~2s) on any commit that touches `opencellcomms_engine/` or `opencellcomms_adapters/` Python. Such commits will run those tests and are blocked if they fail — make sure they pass before committing, and only bypass with `git commit --no-verify` when deliberate.