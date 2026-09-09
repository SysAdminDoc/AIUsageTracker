#!/usr/bin/env python3
"""Protect frozen Windows workers before application imports."""
import multiprocessing
multiprocessing.freeze_support()
