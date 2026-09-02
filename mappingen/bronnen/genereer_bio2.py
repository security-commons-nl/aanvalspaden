"""Maakt bronnen/bio2.json uit de BIO2-kopie van normen (bronnen/bio2-overheidsmaatregelen.json).

De repo normen is de bron: 148 overheidsmaatregelen, genummerd volgens de structuur van
ISO 27002:2022 (5.01.01 hoort bij ISO-maatregel 5.1). Hier groeperen we ze per ISO-maatregel, want dat
is het niveau waarop de mapping wordt gelegd: een barriere levert bewijs voor een maatregel, niet voor
een enkele overheidsmaatregel daarbinnen.

Wat wel wordt overgenomen: het nummer, de Nederlandse titel uit BIO2, de sub-ids en het thema. Wat
niet: de tekst van de ISO-maatregel. Die is auteursrechtelijk beschermd en we hebben hem niet nodig;
wie de tekst wil, gaat naar de bron.

Aanroep (na python tools/haal_normen.py):
    python mappingen/bronnen/genereer_bio2.py [pad naar de kopie]
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

HIER = pathlib.Path(__file__).resolve().parent
UIT = HIER / "bio2.json"
# mappingen/bronnen -> mappingen -> aanvalspaden -> de werkmap met alle repo's ernaast.
STANDAARD_BRON = HIER / "bio2-overheidsmaatregelen.json"


def iso_nummer(sub_id: str) -> str:
    """5.01.01 hoort bij ISO-maatregel 5.1; 8.13.04 bij 8.13."""
    hoofdstuk, maatregel, _ = sub_id.split(".")
    return f"{int(hoofdstuk)}.{int(maatregel)}"


def schoon(tekst: str) -> str:
    """Titels in de bron bevatten afbreekregels uit de oorspronkelijke tabel."""
    return re.sub(r"\s+", " ", tekst).strip().rstrip("'")


def commit_van(pad: pathlib.Path) -> str:
    """De commit waar de bron uit komt, zodat een kopie te herleiden is."""
    try:
        uit = subprocess.run(
            ["git", "-C", str(pad.parent), "log", "-1", "--format=%H"],
            capture_output=True, text=True, timeout=10,
        )
        return uit.stdout.strip() or "onbekend"
    except (OSError, subprocess.SubprocessError):
        return "onbekend"


def bouw(bron_pad: pathlib.Path) -> dict:
    bron = json.loads(bron_pad.read_text(encoding="utf-8"))

    maatregelen: dict[str, dict] = {}
    for control in bron["maatregelen"]:
        nummer = iso_nummer(control["id"])
        maatregel = maatregelen.setdefault(nummer, {
            "id": nummer,
            "titel": schoon(control["titel"]),
            "thema": schoon(control.get("thema") or "Overig"),
            "overheidsmaatregelen": [],
        })
        maatregel["overheidsmaatregelen"].append(control["id"])

    def sorteer(nummer: str) -> tuple[int, int]:
        hoofdstuk, rest = nummer.split(".")
        return int(hoofdstuk), int(rest)

    return {
        "kader": "bio2",
        "titel": "BIO 2.0",
        "toelichting": (
            "De maatregelen van BIO 2.0, gegroepeerd op de ISO 27002-structuur die BIO 2.0 volgt. "
            "Elke maatregel noemt de overheidsmaatregelen die eronder vallen. De teksten zelf staan "
            "in de bron; hier staan alleen nummer, titel en thema."
        ),
        "bron": {
            "naam": bron["bron"]["naam"],
            "versie": bron.get("versie", "BIO2 v1.3"),
            "herkomst": "security-commons-nl/normen, bio2.json (kopie in bronnen/bio2-overheidsmaatregelen.json)",
            "vingerafdruk_normen": bron["vingerafdruk"],
            "commit": bron["bron"].get("commit", "onbekend"),
            "let_op": (
                "Gegenereerd met mappingen/bronnen/genereer_bio2.py uit de kopie van normen. Wijzig de dataset "
                "in normen, niet dit bestand."
            ),
        },
        "tweede_etiket": {
            "kader": "ISO 27001:2022",
            "toelichting": (
                "BIO 2.0 volgt de nummering van ISO 27002:2022, bijlage A van ISO 27001:2022. Het "
                "nummer van een maatregel hier is dus ook het ISO-nummer. De ISO-tekst staat er niet "
                "bij; die is auteursrechtelijk beschermd."
            ),
        },
        "maatregelen": [maatregelen[n] for n in sorted(maatregelen, key=sorteer)],
    }


if __name__ == "__main__":
    bron_pad = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STANDAARD_BRON
    if not bron_pad.exists():
        sys.exit(f"bron niet gevonden: {bron_pad}")
    data = bouw(bron_pad)
    UIT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{UIT}: {len(data['maatregelen'])} maatregelen uit {bron_pad}")
