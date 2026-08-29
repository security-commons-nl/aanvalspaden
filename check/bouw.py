"""Bouwt de zelfcheck: één zelfstandig HTML-bestand uit paden.json en de bestanden in bron/.

Geen bundler, geen dependencies, geen externe verwijzingen. De bron wordt als JSON in dezelfde
scripttag gezet als de app, zodat er precies één script en één stylesheet is en het
Content-Security-Policy hun sha256-hash kan vastleggen: default-src 'none' voor de rest. Zo is de
offlinebelofte controleerbaar in plaats van beloofd.

Aanroep:
    python check/bouw.py                 # schrijft check/dist/index.html
    python check/bouw.py <doelmap>
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


def bouw(doel: pathlib.Path) -> pathlib.Path:
    data = json.loads((REPO / "paden.json").read_text(encoding="utf-8"))
    css = (BRON / "app.css").read_text(encoding="utf-8").strip()
    js = (BRON / "app.js").read_text(encoding="utf-8").strip()
    sjabloon = (BRON / "index.html").read_text(encoding="utf-8")

    # </script> in de data zou de scripttag vroegtijdig sluiten; JSON mag die slash escapen.
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
    doel = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HIER / "dist"
    uit = bouw(doel)
    kb = uit.stat().st_size / 1024
    print(f"{uit}: {kb:.0f} kB, zelfstandig en offline")
