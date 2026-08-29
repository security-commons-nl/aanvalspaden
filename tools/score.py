"""Referentie-implementatie van de scoreregels uit paden.json.

Dit is geen tweede waarheid: elke regel komt uit het blok `regels` en uit `regels` per blad in
paden.json. Wie een app bouwt, kan hiermee toetsen of zijn uitslag klopt.

Gebruik:
    from tools import paden, score
    uitslag = score.beoordeel(paden.laad(), {"pr": "yes", "fallback": "no", ...})
    uitslag["AP01"]["status"]      -> "strong" | "limited" | "reactive" | "open" | "unknown"
    score.acties(paden.laad(), antwoorden, uitslag)  -> de drie zwaarste acties
"""
from __future__ import annotations

ONBEKEND = "unknown"


def _vragen(data: dict) -> dict[str, dict]:
    """Per vraag_id: negatief, alleen_als, letter (drp) en actie, uit de eerste plek waar hij voorkomt."""
    uit: dict[str, dict] = {}
    for blad in data["bladeren"]:
        for cp in blad["chokepoints"]:
            uit.setdefault(cp["vraag_id"], {
                "negatief": cp.get("negatief", False),
                "alleen_als": cp.get("alleen_als"),
                "letter": cp["drp"][0],
                "actie": cp["vraag"]["actie"],
                "model": "opties" in cp,
            })
    for rv in data["randvoorwaarden"]:
        uit.setdefault(rv["vraag_id"], {
            "negatief": False, "alleen_als": None, "letter": "R", "actie": rv["vraag"]["actie"], "model": False,
        })
    return uit


def _antwoord(vragen: dict, antwoorden: dict, vid: str) -> str:
    """Het antwoord na omkering bij een negatieve vraag; leeg telt als onbekend."""
    a = antwoorden.get(vid) or ONBEKEND
    if vragen.get(vid, {}).get("negatief"):
        return {"yes": "no", "no": "yes"}.get(a, a)
    return a


def beoordeel(data: dict, antwoorden: dict[str, str]) -> dict[str, dict]:
    regels = data["regels"]
    vragen = _vragen(data)
    telt_als_ja = set(regels["telt_als_ja"])
    model_ja = set(regels["uitzonderingen"]["AP05"]["model_telt_als_ja"])
    volgorde = [s["id"] for s in regels["statussen"]]

    def ja(vid: str) -> bool:
        if vragen.get(vid, {}).get("model"):
            return antwoorden.get(vid) in model_ja
        return _antwoord(vragen, antwoorden, vid) in telt_als_ja

    def onbekend(vid: str) -> bool:
        return _antwoord(vragen, antwoorden, vid) == ONBEKEND

    uit: dict[str, dict] = {}
    for blad in data["bladeren"]:
        r = blad["regels"]
        ontbrekend = [v for v in r["vereist"] if not ja(v)]
        concreet = any(not onbekend(v) for v in ontbrekend)
        reactief_aanwezig = [v for v in r["reactief"] if ja(v)]

        if not ontbrekend:
            status = r.get("plafond", "strong")
        elif not concreet:
            status = "unknown"
        elif r["beperkt"] and all(ja(v) for v in r["beperkt"]):
            status = "limited"
        elif reactief_aanwezig and ja(regels["randvoorwaarde"]):
            status = "reactive"
        else:
            status = "open"

        if blad["id"] == "AP05":
            status = _ap05(antwoorden, ontbrekend, concreet, ja, onbekend)

        uit[blad["id"]] = {"status": status, "ontbrekend": ontbrekend, "reactief_aanwezig": reactief_aanwezig}

    # AP17: samenstelling van de toegangspaden en de herstelbaarheid.
    ap17 = regels["uitzonderingen"]["AP17"]
    toegang = [uit[p]["status"] for p in ap17["toegangspaden"]]
    slechtste_toegang = next(s for s in volgorde if s in toegang)
    herstel = _herstel(antwoorden)
    samengesteld = volgorde[min(volgorde.index(slechtste_toegang), volgorde.index(herstel))]
    gezien: list[str] = []
    for v in uit["AP17"]["ontbrekend"] + [v for p in ap17["toegangspaden"] for v in uit[p]["ontbrekend"]]:
        if v not in gezien:
            gezien.append(v)
    uit["AP17"].update({"status": samengesteld, "ontbrekend": gezien,
                        "toegang": slechtste_toegang, "herstel": herstel})
    return uit


def _ap05(antwoorden, ontbrekend, concreet, ja, onbekend) -> str:
    model = antwoorden.get("model")
    if not model or model == ONBEKEND:
        return "unknown"
    if model in ("permanent", "separate") or antwoorden.get("jit") == "no":
        return "open"
    sterk_model = model in ("dedicated", "hardened")
    if sterk_model and not ontbrekend:
        return "strong"
    if not concreet:
        return "unknown"
    if sterk_model and all(ja(v) for v in ("adminhard", "jit", "elevation")):
        return "limited"
    if ja("jit") and any(not ja(v) and not onbekend(v) for v in ("elevation", "adminhard")):
        return "reactive"
    return "open"


def _herstel(antwoorden: dict) -> str:
    a = antwoorden
    if a.get("backup") == "no":
        return "open"
    if all(a.get(v) == "yes" for v in ("backup", "restore", "crisis")):
        return "strong"
    if a.get("backup") == "yes" and a.get("restore") == "yes":
        return "limited"
    if any(not a.get(v) or a.get(v) == ONBEKEND for v in ("backup", "restore")):
        return "unknown"
    return "open"


def acties(data: dict, antwoorden: dict[str, str], uitslag: dict[str, dict]) -> list[dict]:
    """De zwaarste acties: vragen die niet ja zijn, gewogen naar de paden waar ze ontbreken."""
    regels = data["regels"]["acties"]
    vragen = _vragen(data)
    model_ja = set(data["regels"]["uitzonderingen"]["AP05"]["model_telt_als_ja"])
    kandidaten = []
    for vid, v in vragen.items():
        niet_ja = antwoorden.get(vid) not in model_ja if v["model"] else _antwoord(vragen, antwoorden, vid) != "yes"
        if not niet_ja:
            continue
        if v["alleen_als"] and antwoorden.get(v["alleen_als"]) == "no":
            continue
        helpt = [p for p, u in uitslag.items() if vid in u["ontbrekend"] and u["status"] != "strong"]
        gewicht = sum(regels["gewicht"][uitslag[p]["status"]] for p in helpt)
        if v["letter"] == "P":
            gewicht *= regels["factor_preventief"]
        if gewicht > 0:
            kandidaten.append({"vraag_id": vid, "actie": v["actie"], "gewicht": gewicht, "helpt": helpt,
                               "verifieer": _antwoord(vragen, antwoorden, vid) == ONBEKEND})
    kandidaten.sort(key=lambda k: -k["gewicht"])
    return kandidaten[: regels["aantal"]]
