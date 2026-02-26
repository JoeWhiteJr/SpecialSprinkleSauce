"""Shared pytest configuration — adds project root to sys.path for src imports."""

import sys
from pathlib import Path

# Add project root (parent of backend/) to sys.path so src.* imports resolve
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
