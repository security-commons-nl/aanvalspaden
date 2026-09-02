#!/usr/bin/env python3
"""Haalt de normbronnen op uit de repo `normen`.

`normen` is de bron van de kaders (BIO 2.0, NIST CSF 2.0, Wpg, AVG). Deze repo legt daar de mappingen op,
en die lezen een kopie in `mappingen/bronnen/`. Een kopie zonder bewaking wordt binnen een half jaar een
tweede waarheid; daarom staat in elke kopie de vingerafdruk van `normen` en meldt `--check` of hij nog
klopt.

Voor BIO 2.0 zijn er twee bestanden: `bio2-overheidsmaatregelen.json` is de kopie van `normen` (148
overheidsmaatregelen), en `bio2.json` is daaruit gegenereerd door `mappingen/bronnen/genereer_bio2.py`:
de 89 maatregelen op ISO-niveau waar de mapping op ligt. Dit script haalt de kopie; de generator draait
daarna.

Gebruik:
    python tools/haal_normen.py            (kopieren, daarna genereer_bio2.py)
    python tools/haal_normen.py --check    (alleen melden of de kopieen kloppen)

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOEL = ROOT / "mappingen" / "bronnen"
# Lokaal staat normen naast deze repo; in CI wordt hij binnen de workspace uitgecheckt als _normen.
KANDIDATEN = (ROOT.parent / "normen", ROOT / "_normen")

# kader in normen -> bestandsnaam hier
KADERS = {
    "bio2": "bio2-overheidsmaatregelen.json",
    "nist-csf": "nist-csf.json",
    "wpg": "wpg.json",
    "avg": "avg.json",
}


def normen_map() -> pathlib.Path:
    for pad in KANDIDATEN:
        if (pad / "bio2.json").is_file():
            return pad
    plekken = "\n".join(f"  {p}" for p in KANDIDATEN)
    sys.exit(f"repo normen niet gevonden. Gezocht op:\n{plekken}\n"
             "Zet normen naast deze repo, of check hem uit als _normen.")


def lees(pad: pathlib.Path) -> dict:
    return json.loads(pad.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    bron_map = normen_map()
    alleen_check = "--check" in argv
    achter: list[str] = []
    for kader, bestand in KADERS.items():
        bron = lees(bron_map / f"{kader}.json")
        doel = DOEL / bestand
        if alleen_check:
            if not doel.is_file():
                achter.append(f"{bestand} ontbreekt")
                continue
            kopie = lees(doel)
            if kopie.get("vingerafdruk") != bron["vingerafdruk"]:
                achter.append(f"{bestand}: kopie {str(kopie.get('vingerafdruk'))[:12]} != normen "
                              f"{bron['vingerafdruk'][:12]}")
        else:
            doel.write_bytes((json.dumps(bron, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
            print(f"  {bestand:34} {len(bron['maatregelen']):4} records  {bron['vingerafdruk'][:12]}")

    # bio2.json is afgeleid; hij draagt de vingerafdruk van de normen-kopie waaruit hij is gegenereerd.
    afgeleid = DOEL / "bio2.json"
    if alleen_check and afgeleid.is_file():
        verwacht = lees(bron_map / "bio2.json")["vingerafdruk"]
        gevonden = lees(afgeleid).get("bron", {}).get("vingerafdruk_normen")
        if gevonden != verwacht:
            achter.append("bio2.json is gegenereerd uit een oudere kopie; draai "
                          "python mappingen/bronnen/genereer_bio2.py")

    if alleen_check:
        if achter:
            print("de kopieen lopen achter op normen:\n  " + "\n  ".join(achter) +
                  "\nDraai 'python tools/haal_normen.py' en daarna 'python mappingen/bronnen/genereer_bio2.py'.")
            return 1
        print("mappingen/bronnen loopt gelijk met normen.")
        return 0
    print("klaar; draai nu python mappingen/bronnen/genereer_bio2.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
