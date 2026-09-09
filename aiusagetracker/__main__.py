"""Entry point: `python -m aiusagetracker` launches the GUI.

Use `python -m aiusagetracker.cli poll|monitor` for headless mode.
"""
import multiprocessing
multiprocessing.freeze_support()

from .gui.app import main

if __name__ == "__main__":
    main()
