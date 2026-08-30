"""Maakt bronnen/nist-csf.json uit de officiele CSF 2.0 Reference Tool-export.

NIST publiceert het framework in het publieke domein, dus de uitkomstformuleringen mogen hier
letterlijk staan. Ze blijven Engels: dat is hoe het kader heet en hoe iedereen ernaar verwijst
(redactiestatuut A10, Engelse vaktermen blijven Engels).

De export bevat naast de 106 geldende subcategorieen ook de ingetrokken subcategorieen uit CSF 1.1,
herkenbaar aan "[Withdrawn". Die horen niet in een mapping thuis en worden overgeslagen.

Downloaden en draaien:
    curl -o nist-csf.xlsx "https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=all"
    python mappingen/bronnen/genereer_nist.py nist-csf.xlsx
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent
UIT = HIER / "nist-csf.json"

FUNCTIE = re.compile(r"^(.*?)\s*\(([A-Z]{2})\):")
CATEGORIE = re.compile(r"^(.*?)\s*\(([A-Z]{2}\.[A-Z]{2})\):")
SUBCATEGORIE = re.compile(r"^([A-Z]{2}\.[A-Z]{2}-\d{2}):\s*(.*)$", re.S)


def lees(xlsx: pathlib.Path) -> list[dict]:
    import openpyxl  # alleen nodig bij het genereren, niet bij het bouwen of testen

    werkblad = openpyxl.load_workbook(xlsx, read_only=True)["CSF 2.0"]
    functie = categorie = None
    uit: dict[str, dict] = {}

    for rij in list(werkblad.iter_rows(values_only=True))[2:]:
        f, c, s = (rij[0] or ""), (rij[1] or ""), (rij[2] or "")
        if f.strip() and (m := FUNCTIE.match(f.strip())):
            functie = (m.group(2), m.group(1))
        if c.strip() and (m := CATEGORIE.match(c.strip())):
            categorie = (m.group(2), m.group(1))
        if not (s.strip() and (m := SUBCATEGORIE.match(s.strip()))):
            continue
        sub_id, titel = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if titel.startswith("[Withdrawn") or sub_id in uit:
            continue
        uit[sub_id] = {
            "id": sub_id,
            "titel": titel,
            "thema": f"{functie[1]} ({functie[0]}) · {categorie[1]}",
        }
    return list(uit.values())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    bron = pathlib.Path(sys.argv[1])
    if not bron.exists():
        sys.exit(f"bron niet gevonden: {bron}")

    maatregelen = lees(bron)
    if len(maatregelen) != 106:
        sys.exit(f"verwacht 106 geldende subcategorieen, gevonden: {len(maatregelen)}")

    data = {
        "kader": "nist-csf",
        "titel": "NIST CSF 2.0",
        "toelichting": (
            "De 106 subcategorieen van het NIST Cybersecurity Framework 2.0, gegroepeerd per functie "
            "en categorie. De uitkomstformuleringen zijn die van NIST zelf en blijven Engels; het "
            "framework staat in het publieke domein."
        ),
        "bron": {
            "naam": "National Institute of Standards and Technology (NIST)",
            "versie": "Cybersecurity Framework 2.0",
            "peildatum": "2026-08-30",
            "url": "https://www.nist.gov/cyberframework",
            "herkomst": "CSF 2.0 Reference Tool, volledige export inclusief informative references",
            "let_op": (
                "Publiek domein. Ingetrokken subcategorieen uit CSF 1.1 staan wel in de export en "
                "zijn hier overgeslagen. Gegenereerd met mappingen/bronnen/genereer_nist.py."
            ),
        },
        "maatregelen": maatregelen,
    }
    UIT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{UIT}: {len(maatregelen)} subcategorieen")
