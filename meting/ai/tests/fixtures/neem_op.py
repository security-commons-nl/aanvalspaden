#!/usr/bin/env python3
"""Neemt het voorbeeldantwoord een keer echt op bij een leverancier.

De tests draaien zonder sleutel en zonder netwerk: ze spelen de leverancier na met het antwoord dat
hier is vastgelegd. Dat antwoord is met de hand geschreven zolang niemand het heeft opgenomen; wie het
echt wil vastleggen, draait dit script een keer met zijn eigen sleutel.

    set MISTRAL_API_KEY=...            (of export, op Linux en macOS)
    python meting/ai/tests/fixtures/neem_op.py

Optioneel: MISTRAL_MODEL (standaard mistral-medium-latest) en MISTRAL_BASIS.

De sleutel komt uit de omgeving en wordt nergens weggeschreven: niet in het antwoord, niet in de
uitvoer, niet in de repo. Wat er wel in het bestand komt, is het antwoord van het model, precies zoals
het binnenkwam.

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

HIER = pathlib.Path(__file__).resolve().parent
AI = HIER.parent.parent
METING = AI.parent

BRON = "crown_jewels_csv"
INVOER = HIER / "voorbeeld-cmdb.md"
DOEL = HIER / "antwoorden" / "contract-crown-jewels.json"


def systeemprompt(opdrachten: dict, bron: dict) -> str:
    """Dezelfde prompt als de pagina bouwt: de opdracht, het contract en de vaste regels."""
    regels = ["", f"Het contract heet {bron['id']} ({bron['titel']}).",
              "Verplichte kolommen: " + ", ".join(bron["kolommen"]) + "."]
    if bron["optioneel"]:
        regels.append("Kolommen die meetellen als je ze kunt vullen: " + ", ".join(bron["optioneel"]) + ".")
    if bron.get("uitleg"):
        regels.append("Wat het contract betekent: " + bron["uitleg"])
    regels.append("Gebruik precies deze kolomnamen, ook als de invoer ze anders noemt.")
    opdracht = opdrachten["opdrachten"][0]
    return opdracht["systeemprompt"] + "\n".join(regels) + "\n\n" + opdrachten["vaste_regels"]


def main() -> int:
    sleutel = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not sleutel:
        print("Zet MISTRAL_API_KEY in de omgeving; hij komt niet in de repo.", file=sys.stderr)
        return 1
    basis = os.environ.get("MISTRAL_BASIS", "https://api.mistral.ai").rstrip("/")
    model = os.environ.get("MISTRAL_MODEL", "mistral-medium-latest")

    opdrachten = json.loads((AI / "opdrachten.json").read_text(encoding="utf-8"))
    regels = json.loads((METING / "regels.json").read_text(encoding="utf-8"))
    bron = [b for b in regels["bronnen"] if b["id"] == BRON][0]

    verzoek = urllib.request.Request(
        f"{basis}/v1/chat/completions",
        data=json.dumps({
            "model": model, "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": systeemprompt(opdrachten, bron)},
                         {"role": "user", "content": INVOER.read_text(encoding="utf-8")}],
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {sleutel}"},
    )
    try:
        with urllib.request.urlopen(verzoek, timeout=120) as antwoord:
            data = json.loads(antwoord.read().decode("utf-8"))
    except urllib.error.HTTPError as fout:
        print(f"HTTP {fout.code}: {fout.read().decode('utf-8', 'replace')[:400]}", file=sys.stderr)
        return 1

    inhoud = json.loads(data["choices"][0]["message"]["content"])
    DOEL.parent.mkdir(parents=True, exist_ok=True)
    DOEL.write_bytes((json.dumps(inhoud, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"{DOEL}: opgenomen bij {model}, {len(inhoud.get('items', []))} rijen")
    print("Controleer of elk citaat woordelijk in voorbeeld-cmdb.md staat; de tests eisen dat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
