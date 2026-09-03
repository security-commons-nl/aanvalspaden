#!/usr/bin/env python3
"""Bouwt de AI-hulp van de meting: een zelfstandig HTML-bestand uit ai/opdrachten.json en ai/bron/.

Zelfde recept als meting/bouw.py: de data als JSON in dezelfde scripttag als kern.js en ai.js, een
stylesheet, en een Content-Security-Policy op de sha256 van beide. Het verschil met de tool zit in
connect-src: deze pagina bestaat om naar buiten te praten, naar de leverancier die de gebruiker kiest.
Alleen https, plus localhost voor een lokale Ollama.

Wat hier extra meegaat ten opzichte van procescheck: de bronnen uit meting/regels.json. De pagina laat
je kiezen naar welk kolomcontract je omzet, en bouwt daar de prompt en het schema uit op. Alleen de
velden die daarvoor nodig zijn gaan mee, niet de hele regelset: het model hoort de meetregels niet te
kennen.

Aanroep:
    python meting/ai/bouw.py                 schrijft meting/ai/dist/index.html
    python meting/ai/bouw.py <doelmap>

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import pathlib
import sys

HIER = pathlib.Path(__file__).resolve().parent
METING = HIER.parent
BRON = HIER / "bron"

CONNECT_SRC = "https: http://localhost:* http://127.0.0.1:*"

# Alleen tabelcontracten kunnen omgezet worden. Een XML-config, een JSON-regelset, een geplakt rapport
# of een Linux-dump laat je niet door een taalmodel herschrijven: dan toets je de tekst van het model
# in plaats van je eigen export.
FORMAAT = "csv"


def sha256_csp(inhoud: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()


def vingerafdruk_tool() -> str:
    """De vingerafdruk van de meetregels, zodat een voorstel weet bij welke versie het hoort."""
    # Niet 'import bouw': dat is de naam van dit bestand zelf. Laden op pad, onder een eigen naam.
    spec = importlib.util.spec_from_file_location("meting_bouw", METING / "bouw.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool.vingerafdruk(json.loads((METING / "regels.json").read_text(encoding="utf-8")))


def bronnen_voor_de_pagina() -> list[dict]:
    """Per tabelcontract wat de pagina nodig heeft: de kolommen, de uitleg en wat het meet."""
    regels = json.loads((METING / "regels.json").read_text(encoding="utf-8"))
    per_bron: dict[str, list[str]] = {}
    for item in regels["items"]:
        per_bron.setdefault(item["bron"], []).append(item["id"])
        if item.get("bron_alternatief"):
            per_bron.setdefault(item["bron_alternatief"], []).append(item["id"])
    uit = []
    for bron in regels["bronnen"]:
        if bron["formaat"] != FORMAAT:
            continue
        uit.append({
            "id": bron["id"], "titel": bron["titel"], "kolommen": bron["kolommen"],
            "optioneel": bron["optioneel"], "uitleg": bron["uitleg"],
            "items": sorted(per_bron.get(bron["id"], [])),
        })
    return uit


def bouw(doel: pathlib.Path) -> pathlib.Path:
    data = json.loads((HIER / "opdrachten.json").read_text(encoding="utf-8"))
    data["tool_vingerafdruk"] = vingerafdruk_tool()
    bronnen = bronnen_voor_de_pagina()
    assert bronnen, "geen tabelcontracten gevonden in regels.json"

    css = (BRON / "ai.css").read_text(encoding="utf-8").strip()
    kern = (BRON / "kern.js").read_text(encoding="utf-8").strip()
    ai = (BRON / "ai.js").read_text(encoding="utf-8").strip()
    sjabloon = (BRON / "index.html").read_text(encoding="utf-8")

    assert "fetch(" not in kern, "kern.js is de gedeelde kern en mag geen netwerk kennen"
    for teken in (chr(0), chr(8), chr(27)):
        assert teken not in css and teken not in kern and teken not in ai, (
            f"stuurteken {ord(teken)} in de bron; de browser vervangt het en breekt het CSP")

    def json_regel(naam: str, waarde) -> str:
        ruw = json.dumps(waarde, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return f"window.{naam} = {ruw};"

    script = (json_regel("__OPDRACHTEN__", data) + "\n"
              + json_regel("__BRONNEN__", bronnen) + "\n"
              + kern + "\n" + ai)

    html = (sjabloon
            .replace("__CSS__", css)
            .replace("__SCRIPT__", script)
            .replace("__SCRIPT_HASH__", sha256_csp(script).removeprefix("sha256-"))
            .replace("__STYLE_HASH__", sha256_csp(css).removeprefix("sha256-"))
            .replace("__CONNECT_SRC__", CONNECT_SRC))
    for rest in ("__CSS__", "__SCRIPT__", "__SCRIPT_HASH__", "__STYLE_HASH__", "__CONNECT_SRC__"):
        assert rest not in html, f"placeholder {rest} niet ingevuld"

    doel.mkdir(parents=True, exist_ok=True)
    uit = doel / "index.html"
    uit.write_bytes(html.encode("utf-8"))
    return uit


if __name__ == "__main__":
    doelmap = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HIER / "dist"
    bestand = bouw(doelmap)
    print(f"{bestand}: {bestand.stat().st_size / 1024:.0f} kB")
