"""Backward-compatible launcher for HARDINFO.

The monolithic implementation has been moved to the :mod:`hardinfo` package.
Running ``python HardInfo.py`` keeps the original behaviour.
"""

from hardinfo.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
