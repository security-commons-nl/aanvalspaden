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

# Bestanden in mappingen/ die geen normenkader zijn. Zonder deze lijst wordt elk nieuw JSON-bestand
# in die map stilletjes als kader opgepakt, en valt de bouw pas om op een ontbrekend bronbestand.
GEEN_KADER = {"mapping.schema.json", "handelingsperspectief.json", "gevraagd.json"}


def kaders() -> list[str]:
    """De kaders waarvoor een mapping bestaat, in redactionele volgorde."""
    gevonden = {p.stem for p in MAP.glob("*.json") if p.name not in GEEN_KADER}
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


# ---------------------------------------------------------------------------
# Handelingsperspectief: waar staat de handleiding bij een barriere?
#
# De normverankering zegt wat je aantoont, dit zegt hoe je het doet. Wat er niet
# staat is net zo belangrijk: een barriere zonder handleiding is een openstaande
# schrijfopdracht, en die lijst is de redactieagenda van de kennisbank.
#
# Twee bestanden, met opzet uit elkaar gehouden. handelingsperspectief.json is een
# kopie van de kennisbank-export (tools/haal_handelingsperspectief.py) en wordt hier
# nooit met de hand aangeraakt. gevraagd.json is wel handwerk: wat een nog niet
# geschreven handleiding zou moeten dekken, weet de kennisbank niet.
# ---------------------------------------------------------------------------

HP = MAP / "handelingsperspectief.json"
GEVRAAGD = MAP / "gevraagd.json"
# De volgorde waarin meer dan een handleiding bij dezelfde barriere wordt getoond: eerst waar je
# begint, dan wat ernaast kan, dan wat erbovenop gaat.
ROLLEN = ("fundering", "alternatief", "verdieping")


def handelingsperspectief() -> dict:
    return json.loads(HP.read_text(encoding="utf-8"))


def gevraagd() -> dict:
    return json.loads(GEVRAAGD.read_text(encoding="utf-8"))


def handleidingen_van(barriere: str) -> list[dict]:
    """Alle handleidingen bij deze barriere, op rol gesorteerd; leeg als er nog geen is.

    Meer dan een mag: bij monitoring kun je kiezen tussen zelf doen, co-managed of uitbesteden. Die
    keuze is de kern van het advies, dus de lijst afkappen op de eerste zou het weggooien.
    """
    hl = [h for h in handelingsperspectief()["handleidingen"] if h["barriere"] == barriere]
    return sorted(hl, key=lambda h: (ROLLEN.index(h["rol"]) if h["rol"] in ROLLEN else 9, h["titel"]))


def gevraagd_van(barriere: str) -> dict | None:
    """De openstaande schrijfopdracht bij deze barriere, of None."""
    return next((g for g in gevraagd()["gevraagd"] if g["barriere"] == barriere), None)


def gewicht_van_barriere(barriere: str) -> int:
    """Hoe zwaar weegt deze barriere? Proxy zolang er geen echte zelfcheck-data is.

    Het aantal aanvalspaden waarop de barriere staat. Een barriere die bij vier paden meetelt, sluit
    bij een verbetering vier routes tegelijk; die hoort eerder geschreven te worden dan een die maar
    op een pad staat. Zodra er uitslagen zijn, is het betere signaal hoe vaak de barriere als actie
    uit `score.acties()` komt.

    Een randvoorwaarde hangt aan geen enkel pad maar weegt in de beoordeling over alle paden heen
    mee. Tellen op bladeren zou hem op nul zetten, terwijl hij juist het breedst geldt; hij krijgt
    daarom het aantal paden als gewicht.
    """
    item = barrieres().get(barriere)
    if not item:
        return 0
    if not item["bladeren"] and item["chokepoints"]:
        return len(paden_bron.paden())
    return len(item["bladeren"])


def schrijfopdrachten() -> list[dict]:
    """De openstaande schrijfopdrachten, gegroepeerd tot artikelen en gesorteerd op gewicht.

    Een artikel bedient vaak meer dan een barriere: een stuk over werkplekhardening dekt er drie. De
    mapping loopt per barriere omdat dat precies en toetsbaar is; de backlog groepeert ze, omdat dat
    is hoe je gaat schrijven.
    """
    data = gevraagd()
    alle = barrieres()
    per_cluster: dict[str, list[dict]] = {}
    for item in data["gevraagd"]:
        per_cluster.setdefault(item["cluster"], []).append(item)

    uit = []
    for cluster, items in per_cluster.items():
        gewicht = sum(gewicht_van_barriere(i["barriere"]) for i in items)
        uit.append({
            "cluster": cluster,
            "barrieres": [
                {
                    "id": i["barriere"],
                    "titel": alle[i["barriere"]]["titel"] if i["barriere"] in alle else i["barriere"],
                    "zou_moeten_dekken": i["zou_moeten_dekken"],
                    "gewicht": gewicht_van_barriere(i["barriere"]),
                }
                for i in sorted(items, key=lambda x: -gewicht_van_barriere(x["barriere"]))
            ],
            "gewicht": gewicht,
        })
    return sorted(uit, key=lambda c: (-c["gewicht"], c["cluster"]))


def dekking_handelingsperspectief() -> dict:
    data = handelingsperspectief()
    agenda = gevraagd()
    alle = barrieres()
    met = {h["barriere"] for h in data["handleidingen"]}
    return {
        "barrieres": len(alle),
        "met_handleiding": len(met),
        "keuze": len({h["barriere"] for h in data["handleidingen"] if h["rol"] == "alternatief"}),
        "open": len(data["zonder_handleiding"]),
        "gevraagd": len(agenda["gevraagd"]),
        "geen_nodig": len(agenda["geen_handleiding_nodig"]),
        "schrijfopdrachten": len(schrijfopdrachten()),
    }


def stille_barrieres() -> list[str]:
    """Barrieres die geen handleiding hebben en ook niet in de agenda staan.

    Stilte is nooit een vergissing: staat een barriere nergens in, dan weet de lezer niet of er niets
    over te schrijven valt of dat het gewoon is blijven liggen. Deze lijst hoort leeg te zijn.
    """
    agenda = gevraagd()
    genoemd = ({g["barriere"] for g in agenda["gevraagd"]}
               | {g["barriere"] for g in agenda["geen_handleiding_nodig"]})
    return sorted(b for b in handelingsperspectief()["zonder_handleiding"] if b not in genoemd)
