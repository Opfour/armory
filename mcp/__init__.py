# Extend __path__ so that submodule imports (mcp.server, etc.) resolve to
# the installed mcp SDK package rather than only this local directory.
from __future__ import annotations

import sys
from pathlib import Path

_this_dir = str(Path(__file__).resolve().parent)

for _entry in sys.path:
    _candidate = Path(_entry).resolve() / "mcp"
    # Skip ourselves.
    if str(_candidate) == _this_dir:
        continue
    if _candidate.is_dir() and (_candidate / "server").is_dir():
        _installed_path = str(_candidate)
        if _installed_path not in __path__:
            __path__.append(_installed_path)
        break
