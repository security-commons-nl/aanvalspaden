"""De repo heeft een vaste structuur; deze test beschermt die."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_vaste_bestanden_en_mappen_bestaan():
    for pad in (
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "BESLUITEN.md",
        ".gitignore",
        "paden.json",
        "check",
        "methode",
        "tools",
        ".github/workflows/ci.yml",
    ):
        assert (ROOT / pad).exists(), f"ontbreekt: {pad}"


def test_licentie_is_eupl():
    assert "EUROPEAN UNION PUBLIC LICENCE" in (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_geen_em_dash_in_de_documentatie():
    for pad in ("README.md", "CONTRIBUTING.md", "BESLUITEN.md", "methode/README.md"):
        tekst = (ROOT / pad).read_text(encoding="utf-8")
        assert "—" not in tekst, f"em-dash in {pad}"


def test_readme_noemt_de_twee_regels():
    tekst = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Bewijs is de scheidslijn" in tekst
    assert "knop, geen volgend scherm" in tekst
