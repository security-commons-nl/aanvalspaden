"""Laadt mappingen/bouw.py onder een eigen naam.

Zowel check/ als mappingen/ heeft een bouw.py. Draai je de hele testmap in een keer, dan zou
`import bouw` de eerste van de twee pakken en zouden de tests van het andere script stil de
verkeerde module toetsen. Daarom laden we hem hier expliciet op pad, als `crosswalk_bouw`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

MAP = pathlib.Path(__file__).resolve().parent.parent
REPO = MAP.parent

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location("crosswalk_bouw", MAP / "bouw.py")
_module = importlib.util.module_from_spec(_spec)
sys.modules["crosswalk_bouw"] = _module
_spec.loader.exec_module(_module)
