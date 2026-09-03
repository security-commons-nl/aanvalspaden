#!/usr/bin/env python3
"""Bouwt de meting: één zelfstandig HTML-bestand uit regels.json, paden.json en de bestanden in bron/.

Zelfde afspraak als check/bouw.py en mappingen/bouw.py: geen bundler, geen dependencies, geen externe
verwijzingen. De data gaat als JSON in dezelfde scripttag als de app, zodat er precies één script en één
stylesheet is en het Content-Security-Policy hun sha256-hash kan vastleggen, met default-src 'none' voor
de rest. De offlinebelofte is daarmee controleerbaar in plaats van beloofd.

Uit paden.json gaan alleen de bladeren, de randvoorwaarden en de versie mee: meting toont bewijs per
chokepoint, niet de vragen van de zelfcheck.

Aanroep:
    python meting/bouw.py                 # schrijft meting/dist/index.html
    python meting/bouw.py <doelmap>

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent
BRON = HIER / "bron"


def sha256_csp(inhoud: str) -> str:
    """De hashvorm die het Content-Security-Policy verwacht."""
    return "sha256-" + base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()


def vingerafdruk(regels: dict) -> str:
    kern = {s: regels[s] for s in ("items", "bronnen", "tijd", "iamscan", "soorten")}
    ruw = json.dumps(kern, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(ruw.encode("utf-8")).hexdigest()


def bouw(doel: pathlib.Path) -> pathlib.Path:
    regels = json.loads((HIER / "regels.json").read_text(encoding="utf-8"))
    paden = json.loads((REPO / "paden.json").read_text(encoding="utf-8"))

    data = {
        "regels": regels,
        "paden": {sleutel: paden[sleutel] for sleutel in ("versie", "bladeren", "randvoorwaarden")},
        "vingerafdruk": vingerafdruk(regels),
    }

    css = (BRON / "app.css").read_text(encoding="utf-8").strip()
    js = (BRON / "app.js").read_text(encoding="utf-8").strip()
    sjabloon = (BRON / "index.html").read_text(encoding="utf-8")

    assert "fetch(" not in js, "meting praat met niemand; er hoort geen fetch in app.js te staan"
    # Een stuurteken in de bron wordt door de HTML-parser vervangen; de sha256 in het CSP klopt
    # dan niet meer met wat de browser ziet en de pagina wordt in zijn geheel geweigerd.
    for teken in (chr(0), chr(8), chr(27)):
        assert teken not in js and teken not in css and teken not in sjabloon, (
            f"stuurteken {ord(teken)} in de bron; de browser vervangt het en breekt het CSP")

    json_bron = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script = "window.__BRON__ = " + json_bron + ";\n" + js

    html = (sjabloon
            .replace("__CSS__", css)
            .replace("__SCRIPT__", script)
            .replace("__SCRIPT_HASH__", sha256_csp(script).removeprefix("sha256-"))
            .replace("__STYLE_HASH__", sha256_csp(css).removeprefix("sha256-")))
    for rest in ("__CSS__", "__SCRIPT__", "__SCRIPT_HASH__", "__STYLE_HASH__"):
        assert rest not in html, f"placeholder {rest} niet ingevuld"

    doel.mkdir(parents=True, exist_ok=True)
    uit = doel / "index.html"
    uit.write_bytes(html.encode("utf-8"))
    return uit


if __name__ == "__main__":
    doelmap = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HIER / "dist"
    bestand = bouw(doelmap)
    print(f"{bestand}: {bestand.stat().st_size / 1024:.0f} kB, zelfstandig en offline")
