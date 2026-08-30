#!/usr/bin/env python3
"""Haalt de koppeling barriere -> handleiding op uit de kennisbank.

De kennisbank is de bron: daar staat in de frontmatter van elk item bij welke barrieres het hoort en
met welke rol. `kennisbank/tools/build.py` exporteert dat naar `handelingsperspectief.json`. Dit script
kopieert die export hierheen, met een sha256 erbij zodat een verlopen kopie opvalt.

Waarom kopieren en niet lezen? De site van aanvalspaden wordt gebouwd zonder de kennisbank ernaast, en
een pagina die stilletjes zonder handelingsperspectief bouwt is erger dan een build die stukloopt. De
kopie staat in git, dus een verschil is zichtbaar in de review in plaats van pas op de site.

Gebruik:
    python tools/haal_handelingsperspectief.py            (kopieren)
    python tools/haal_handelingsperspectief.py --check    (alleen melden of de kopie klopt)

Alleen standaardbibliotheek; geen pip nodig.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOEL = ROOT / "mappingen" / "handelingsperspectief.json"
# Lokaal staat de kennisbank ernaast; in CI wordt hij naar _kennisbank uitgecheckt.
KANDIDATEN = (
    ROOT.parent / "kennisbank" / "handelingsperspectief.json",
    ROOT / "_kennisbank" / "handelingsperspectief.json",
)

TOELICHTING = (
    "Waar staat de handleiding bij een barriere? De zelfcheck zegt wat je moet doen, dit zegt hoe. "
    "Wat hier niet staat is geen omissie maar een openstaande schrijfopdracht: de barrieres in "
    "gevraagd.json hebben nog geen handleiding, met erbij wat die zou moeten dekken. Dat is de "
    "redactieagenda van de kennisbank, en tegelijk de uitnodiging aan wie het wel weet."
)


def bronbestand() -> pathlib.Path:
    for pad in KANDIDATEN:
        if pad.is_file():
            return pad
    plekken = "\n".join(f"  {p}" for p in KANDIDATEN)
    sys.exit(f"kennisbank-export niet gevonden. Gezocht op:\n{plekken}\n"
             "Zet de kennisbank-repo ernaast, of check hem uit als _kennisbank.")


def kopie(bron: pathlib.Path) -> dict:
    ruw = bron.read_bytes()
    export = json.loads(ruw.decode("utf-8"))
    return {
        "versie": "gegenereerd door tools/haal_handelingsperspectief.py; wijzig de kennisbank, niet dit bestand",
        "toelichting": TOELICHTING,
        "bron": {
            "kennisbank": "https://security-commons-nl.github.io/kennisbank/",
            "repo": "security-commons-nl/kennisbank",
            "bestand": "handelingsperspectief.json",
            "sha256": hashlib.sha256(ruw).hexdigest(),
            "let_op": ("De kennisbank is de bron. Klopt deze kopie niet meer, dan draai je dit script "
                       "opnieuw; hem met de hand bijwerken laat de sha256 achter en verbergt het verschil."),
        },
        "handleidingen": export["handleidingen"],
        "zonder_handleiding": export["zonder_handleiding"],
    }


def main() -> int:
    bron = bronbestand()
    nieuw = json.dumps(kopie(bron), ensure_ascii=False, indent=2) + chr(10)
    oud = DOEL.read_text(encoding="utf-8") if DOEL.is_file() else ""
    if "--check" in sys.argv:
        if oud == nieuw:
            print("handelingsperspectief.json is gelijk aan de kennisbank-export.")
            return 0
        print("handelingsperspectief.json loopt achter op de kennisbank.\n"
              "Draai: python tools/haal_handelingsperspectief.py", file=sys.stderr)
        return 1
    if oud == nieuw:
        print("handelingsperspectief.json: niets gewijzigd")
        return 0
    DOEL.write_text(nieuw, encoding="utf-8")
    aantal = len(json.loads(nieuw)["handleidingen"])
    print(f"handelingsperspectief.json bijgewerkt uit {bron}: {aantal} koppelingen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
