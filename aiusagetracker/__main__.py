"""Entry point: `python -m aiusagetracker` launches the GUI.

Use `python -m aiusagetracker.cli poll|monitor` for headless mode.
"""
from .gui.app import main

if __name__ == "__main__":
    main()
