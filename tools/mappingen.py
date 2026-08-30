"""Toegang tot de mappingen: welke barriere levert bewijs voor welke maatregel.

De mapping hangt aan de barriere (het `vraag_id` uit paden.json), niet aan het chokepoint. Dezelfde
barriere staat bij meer paden: phishingbestendige authenticatie telt bij vier. Zou je per chokepoint
mappen, dan kun je die vier uit elkaar laten lopen zonder dat iemand het merkt. Een chokepoint erft
dus de mapping van zijn barriere.

Wie een norm of een pad wil opzoeken, haalt het hier op. Nooit een kopie in code.
"""
from __future__ import annotations

import json
import pathlib

from . import paden as paden_bron

MAP = pathlib.Path(__file__).resolve().parent.parent / "mappingen"
BRONNEN = MAP / "bronnen"

STERKTES = ("volledig", "gedeeltelijk", "raakvlak")

# De volgorde is redactioneel, niet alfabetisch (zelfde principe als statuut B4 voor indexpagina's).
# Het eerste kader is wat de pagina opent. BIO 2.0 staat voorop omdat dat het kader is waar de
# doelgroep op wordt bevraagd; daarna NIST CSF, dat het dichtst bij de aanvalspaden staat; dan de
# twee kaders die maar deels over beveiliging gaan en juist de grens laten zien.
VOLGORDE = ("bio2", "nist-csf", "wpg", "avg")


def kaders() -> list[str]:
    """De kaders waarvoor een mapping bestaat, in redactionele volgorde."""
    gevonden = {p.stem for p in MAP.glob("*.json") if p.name != "mapping.schema.json"}
    ongeplaatst = sorted(gevonden - set(VOLGORDE))
    return [k for k in VOLGORDE if k in gevonden] + ongeplaatst


def mapping(kader: str) -> dict:
    """De mapping van een kader: regels en de barrieres die met opzet geen regel hebben."""
    return json.loads((MAP / f"{kader}.json").read_text(encoding="utf-8"))


def bron(kader: str) -> dict:
    """Het normenkader zelf: de maatregelen met hun titel en thema."""
    return json.loads((BRONNEN / f"{kader}.json").read_text(encoding="utf-8"))


def maatregelen(kader: str) -> list[dict]:
    return bron(kader)["maatregelen"]


def maatregel(kader: str, norm_id: str) -> dict | None:
    return next((m for m in maatregelen(kader) if m["id"] == norm_id), None)


def barrieres() -> dict[str, dict]:
    """Elke unieke barriere uit paden.json, met de chokepoints die erop staan.

    Sleutel is het vraag_id. Titel, claim en bewijs zijn per definitie gelijk voor alle chokepoints
    van dezelfde barriere; een test in tests/test_mappingen.py bewaakt dat.
    """
    uit: dict[str, dict] = {}
    bron_data = paden_bron.laad()
    losse = [dict(cp, blad=b["id"]) for b in bron_data["bladeren"] for cp in b["chokepoints"]]
    losse += [dict(r, blad=None) for r in bron_data.get("randvoorwaarden", [])]

    for cp in losse:
        item = uit.setdefault(cp["vraag_id"], {
            "id": cp["vraag_id"],
            "titel": cp["titel"],
            "claim": cp["vraag"]["claim"],
            "bewijs": cp.get("bewijs", ""),
            "drp": cp.get("drp", []),
            "chokepoints": [],
            "bladeren": [],
        })
        item["chokepoints"].append(cp["id"])
        if cp["blad"] and cp["blad"] not in item["bladeren"]:
            item["bladeren"].append(cp["blad"])
    return uit


def regels_van_barriere(kader: str, barriere: str) -> list[dict]:
    """Wat deze barriere aantoont in dit kader, zwaarste eerst."""
    regels = [r for r in mapping(kader)["regels"] if r["barriere"] == barriere]
    return sorted(regels, key=lambda r: STERKTES.index(r["sterkte"]))


def regels_van_norm(kader: str, norm_id: str) -> list[dict]:
    """Welke barrieres bewijs leveren voor deze maatregel, zwaarste eerst."""
    regels = [r for r in mapping(kader)["regels"] if r["norm"] == norm_id]
    return sorted(regels, key=lambda r: STERKTES.index(r["sterkte"]))


def aangetoond(kader: str) -> set[str]:
    """De maatregelen waar echt bewijs voor is: volledig of gedeeltelijk.

    Een raakvlak telt hier met opzet niet mee. De definitie van raakvlak is dat het bewijs de
    maatregel niet aantoont; zou een raakvlak toch als dekking tellen, dan zou de pagina precies de
    valse zekerheid geven die dit hele instrument probeert te vermijden.
    """
    return {r["norm"] for r in mapping(kader)["regels"] if r["sterkte"] != "raakvlak"}


def witte_vlekken(kader: str) -> list[dict]:
    """De maatregelen waar geen enkele barriere bewijs voor levert.

    Dit is het antwoord op de vraag waar de zelfcheck ophoudt. Het is geen tekort van de zelfcheck:
    een dreigingsgerichte vragenlijst hoort niet over bewaartermijnen of screening te gaan.

    Een maatregel met alleen raakvlakken staat hier ook, maar draagt die raakvlakken mee onder
    `raakvlakken`. Dat is vaak het interessantste geval: de zelfcheck komt in de buurt en de lezer
    moet weten waarom het toch niet telt.
    """
    hard = aangetoond(kader)
    uit = []
    for m in maatregelen(kader):
        if m["id"] in hard:
            continue
        raakvlakken = [r for r in mapping(kader)["regels"] if r["norm"] == m["id"]]
        uit.append(dict(m, raakvlakken=raakvlakken))
    return uit


def dekking(kader: str) -> dict:
    """De telling die op de pagina staat en die een test bewaakt."""
    data = mapping(kader)
    alle = maatregelen(kader)
    hard = aangetoond(kader)
    aangeraakt = {r["norm"] for r in data["regels"]}
    return {
        "kader": kader,
        "regels": len(data["regels"]),
        "maatregelen": len(alle),
        "geraakt": len(hard),
        "witte_vlekken": len(alle) - len(hard),
        "alleen_raakvlak": len(aangeraakt - hard),
        "barrieres_gemapt": len({r["barriere"] for r in data["regels"]}),
        "barrieres_ongekoppeld": len(data["ongekoppeld"]),
    }
