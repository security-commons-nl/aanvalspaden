"""Gedeelde fixtures van de AI-hulp van de meting.

Deze map heeft geen eigen kern.py. `bron/kern.js` is een byte-identieke kopie van die in procescheck,
en daar staat de Python-referentie met zijn eigen tests; een tweede kopie hier zou een tweede waarheid
worden. Wat hier getoetst wordt, is wat aan de meting eigen is: de opdrachten, de contracten die uit
regels.json in de pagina komen, de bouw, en de weg van voorstel naar meting.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
AI = HIER.parent
METING = AI.parent
REPO = METING.parent
FIXTURES = HIER / "fixtures"

# meting/bouw.py en meting/ai/bouw.py heten allebei bouw. Wie ze via sys.path importeert, krijgt de
# eerste die python vindt, en dan toetst een test stil de verkeerde pagina. Daarom allebei op pad
# laden, onder een eigen naam.
import importlib.util  # noqa: E402


def _laad(naam: str, pad: pathlib.Path):
    spec = importlib.util.spec_from_file_location(naam, pad)
    module = importlib.util.module_from_spec(spec)
    sys.modules[naam] = module
    spec.loader.exec_module(module)
    return module

PROCESCHECK = REPO.parent / "procescheck"


@pytest.fixture(scope="session")
def ai_bouw():
    """De build van de AI-pagina (meting/ai/bouw.py)."""
    return _laad("ai_bouw", AI / "bouw.py")


@pytest.fixture(scope="session")
def tool_bouw():
    """De build van de meting zelf (meting/bouw.py), voor de tests die de tool erbij nodig hebben."""
    return _laad("meting_bouw_tests", METING / "bouw.py")


@pytest.fixture(scope="session")
def opdrachten() -> dict:
    return json.loads((AI / "opdrachten.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def regels() -> dict:
    return json.loads((METING / "regels.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def invoer() -> str:
    """De voorbeeldinvoer zoals het model hem kreeg: een geplakte uitdraai, geen csv."""
    return (FIXTURES / "voorbeeld-cmdb.md").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def antwoord() -> dict:
    """Het vastgelegde modelantwoord, zonder de herkomstregel die er voor de lezer in staat."""
    data = json.loads((FIXTURES / "antwoorden" / "contract-crown-jewels.json").read_text(encoding="utf-8"))
    return {sleutel: waarde for sleutel, waarde in data.items() if not sleutel.startswith("_")}


def kern_bron() -> pathlib.Path | None:
    """procescheck als buurmap, of None; de vergelijking met de bron slaat zichzelf dan over."""
    pad = PROCESCHECK / "ai" / "bron" / "kern.js"
    return pad if pad.is_file() else None


def draai(*argumenten: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *argumenten], capture_output=True, cwd=str(REPO))
