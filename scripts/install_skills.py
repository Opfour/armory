#!/usr/bin/env python3
"""Backward-compatible wrapper — use scripts/install.py instead."""
from __future__ import annotations

from scripts.install import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
