#!/usr/bin/env python3
"""Convenience launcher for the AIUsageTracker GUI (also the PyInstaller target)."""
import multiprocessing
multiprocessing.freeze_support()

from aiusagetracker.gui.app import main

if __name__ == "__main__":
    main()
