"""Eenmalige omzetting: gecompileerde zelfcheck naar paden.json.

Zo is paden.json op 28-08-2026 de eerste keer gevuld, toen de broncode van de zelfcheck nog niet
beschikbaar was. Vanaf dat moment is paden.json zelf de bron; dit script staat er als documentatie van
de herkomst en om de omzetting te kunnen herhalen op een nieuwere bundel.

De bundel bevat twee structuren:
  Ba = [U(id, domein, claim, toelichting, hint, actie, letter?, opties?), ...]   44 vragen
  kk = [{id, domain, name, explain, required, response, limited, technical}, ...] 18 paden

Deze parser leest beide, koppelt de vragen aan de paden via required/response/limited,
en schrijft paden.json volgens tools/paden.schema.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

# Aanroep: python tools/uit_zelfcheck.py <zelfcheck.html> [doel.json]
BRON = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("zelfcheck.html")
DOEL = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(__file__).resolve().parent.parent / "paden.json"


def bundel() -> str:
    t = BRON.read_text(encoding="utf-8", errors="replace")
    return max(re.findall(r"<script[^>]*>(.*?)</script>", t, re.S), key=len)


def split_args(s: str, start: int) -> tuple[list[str], int]:
    """Split de argumenten van een aanroep die begint bij s[start] == '('."""
    assert s[start] == "("
    args, diepte, huidig, i = [], 0, [], start + 1
    in_str: str | None = None
    while i < len(s):
        c = s[i]
        if in_str:
            huidig.append(c)
            if c == "\\":
                huidig.append(s[i + 1])
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "\"'`":
            in_str = c
            huidig.append(c)
        elif c in "([{":
            diepte += 1
            huidig.append(c)
        elif c in ")]}":
            if c == ")" and diepte == 0:
                args.append("".join(huidig).strip())
                return args, i
            diepte -= 1
            huidig.append(c)
        elif c == "," and diepte == 0:
            args.append("".join(huidig).strip())
            huidig = []
        else:
            huidig.append(c)
        i += 1
    raise ValueError("niet gesloten aanroep")


def js_string(v: str) -> str:
    v = v.strip()
    if not v or v[0] not in "\"'`":
        return ""
    kern = v[1:-1]
    kern = kern.replace('\\"', '"').replace("\\'", "'").replace("\\`", "`")
    kern = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), kern)
    kern = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), kern)
    kern = kern.replace("\\n", " ").replace("\\/", "/")
    return kern.strip()


def lees_vragen(s: str) -> dict[str, dict]:
    """Alle U(...)-aanroepen als dict op vraag-id."""
    vragen: dict[str, dict] = {}
    for m in re.finditer(r"\bU\(", s):
        try:
            args, _ = split_args(s, m.end() - 1)
        except ValueError:
            continue
        if len(args) < 6:
            continue
        vid = js_string(args[0])
        if not vid or not re.fullmatch(r"[a-z0-9_]+", vid):
            continue
        claim = js_string(args[2])
        if not claim.endswith("?"):
            continue
        letter = js_string(args[6]) if len(args) > 6 else ""
        negatief = "negative" in (args[7] if len(args) > 7 else "")
        vragen[vid] = {
            "id": vid,
            "domein": int(args[1]) if args[1].strip().isdigit() else -1,
            "claim": claim,
            "toelichting": js_string(args[3]),
            "hint": js_string(args[4]),
            "actie": js_string(args[5]),
            "letter": letter if letter in ("D", "R", "P", "G") else "",
            "negatief": negatief,
        }
    return vragen


def lees_paden(s: str) -> list[dict]:
    """De kk-array met de achttien aanvalspaden."""
    paden = []
    for m in re.finditer(r'\{id:"(AP\d\d)"', s):
        start = m.start()
        diepte, i, in_str = 0, start, None
        while i < len(s):
            c = s[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == in_str:
                    in_str = None
            elif c in "\"'`":
                in_str = c
            elif c == "{":
                diepte += 1
            elif c == "}":
                diepte -= 1
                if diepte == 0:
                    break
            i += 1
        blok = s[start : i + 1]

        def lijst(veld: str) -> list[str]:
            mm = re.search(veld + r":\[(.*?)\]", blok, re.S)
            return [js_string(x) for x in mm.group(1).split(",") if x.strip()] if mm else []

        def tekst(veld: str) -> str:
            mm = re.search(veld + r':("(?:[^"\\]|\\.)*")', blok, re.S)
            return js_string(mm.group(1)) if mm else ""

        paden.append({
            "id": m.group(1),
            "name": tekst("name"),
            "explain": tekst("explain"),
            "technical": tekst("technical"),
            "required": lijst("required"),
            "response": lijst("response"),
            "limited": lijst("limited"),
        })
    return paden


# Clusters volgens het bouwplan (spec punt 2).
CLUSTERS = [
    ("C1", "Gecompromitteerd account",
     "Phishing, adversary-in-the-middle, gestolen inloggegevens, misbruikte toestemming: de aanvaller logt in als de gebruiker.",
     ["AP01", "AP02", "AP03", "AP04", "AP06", "AP07"]),
    ("C2", "Werkplek via de gebruiker",
     "De gebruiker voert zelf iets uit, of malware doet dat namens hem: van besmette werkplek naar verdere toegang.",
     ["AP08", "AP09", "AP10", "AP11"]),
    ("C3", "Kwetsbare internetgerichte dienst",
     "Een dienst die vanaf internet bereikbaar is, wordt misbruikt of platgelegd: kwetsbaarheid, onbekende exposure, applicatiefout of overbelasting.",
     ["AP12", "AP13", "AP14", "AP15", "AP16"]),
    ("C4", "Leverancier en keten",
     "Een incident bij een leverancier of ketenpartner raakt de eigen dienstverlening.",
     ["AP18"]),
    ("C5", "Misbruik van beheerrechten",
     "Eenmaal binnen: van een gewoon account naar verhoogde rechten en beheerdomeinen.",
     ["AP05"]),
]

# De bron is geschreven voor een gemeente; de commons publiceert voor publieke organisaties.
# Deze vervangingen gelden op elke tekst die uit de bundel komt (statuut A3).
GENERIEK = [
    ("gemeentelijke gegevens", "gegevens van de organisatie"),
    ("gemeentelijke informatie", "informatie van de organisatie"),
    ("kritieke gemeentelijke processen", "kritieke processen van de organisatie"),
    ("gemeentelijke", "organisatie-"),
    ("Gemeentelijke", "Organisatie-"),
]


def generiek(s: str) -> str:
    for a, b in GENERIEK:
        s = s.replace(a, b)
    return s


# Titels die generiek moeten zijn: de bron zei "gemeentelijke".
TITELS = {
    "AP17": "Ransomware → uitval van de dienstverlening",
    "AP18": "Leveranciersincident → impact op de dienstverlening",
}

# Welke letters horen bij welke rol van een vraag binnen een pad.
LETTER_VAN_ROL = {"required": "P", "response": "R", "limited": "P"}


# Een "niet telt"-zin herken je aan deze wendingen; de bron zet hem nu eens in het derde,
# dan weer in het vierde argument.
NIET_PATROON = re.compile(
    r"is niet genoeg|niet voldoende|telt niet|voorkomt niet|vervangt geen|zegt niets over|"
    r"is geen|alleen .{0,30}is onvoldoende|niet automatisch|sluit .{0,20}niet",
    re.I,
)

# Wat maakt een cel groen in diepte 1, per rol van het chokepoint.
BEWIJS_PER_LETTER = {
    "P": "Export of configuratie waaruit blijkt dat de maatregel technisch is afgedwongen, met de dekking en de uitzonderingen erbij.",
    "D": "De actieve detectieregel of het dashboard, plus een verslag van een test waaruit blijkt dat het signaal ook echt binnenkomt.",
    "R": "Het playbook plus een oefen- of incidentverslag waaruit blijkt dat er binnen de afgesproken tijd is gehandeld.",
}


def velden(v: dict) -> dict:
    """Verdeel de twee vrije toelichtingen van de bron over toelichting, telt_niet en verificatie."""
    a, b = generiek(v["toelichting"]), generiek(v["hint"])
    telt_niet, toelichting, verificatie = "", a, b
    if NIET_PATROON.search(a) and not NIET_PATROON.search(b):
        telt_niet, toelichting, verificatie = a, "", b
    elif NIET_PATROON.search(b):
        telt_niet, toelichting, verificatie = b, a, ""
    return {
        "claim": generiek(v["claim"]),
        "toelichting": toelichting or verificatie,
        "telt_niet": telt_niet,
        "verificatie": verificatie if toelichting else "",
        "actie": generiek(v["actie"]),
    }


def bouw() -> dict:
    s = bundel()
    vragen = lees_vragen(s)
    paden = lees_paden(s)
    per_id = {p["id"]: p for p in paden}
    in_cluster = {ap for _, _, _, aps in CLUSTERS for ap in aps}

    bladeren = []
    for pad in paden:
        is_impact = pad["id"] == "AP17"
        chokepoints = []
        gezien = set()
        volgnr = 0
        for rol in ("required", "limited", "response"):
            for vid in pad[rol]:
                if vid in gezien or vid not in vragen:
                    continue
                gezien.add(vid)
                v = vragen[vid]
                volgnr += 1
                letter = v["letter"] if v["letter"] in ("D", "R", "P") else LETTER_VAN_ROL[rol]
                vr = {k: w for k, w in velden(v).items() if w}
                chokepoints.append({
                    "id": f"{pad['id']}-{volgnr}",
                    "titel": generiek(v["actie"]).rstrip(".") or generiek(v["claim"]).rstrip("?"),
                    "vraag": vr,
                    "drp": [letter],
                    "bewijs": BEWIJS_PER_LETTER[letter],
                })
        titel = TITELS.get(pad["id"], pad["name"])
        blad = {
            "id": pad["id"],
            "titel": titel,
            "type": "impact" if is_impact else "pad",
            "scenario": generiek(pad["explain"]),
            "chokepoints": chokepoints,
            "bronnen": [],
        }
        if pad["technical"]:
            blad["nuance"] = generiek(pad["technical"])
        bladeren.append(blad)

    ontbreekt = [b["id"] for b in bladeren if b["type"] == "pad" and b["id"] not in in_cluster]
    if ontbreekt:
        raise SystemExit(f"paden zonder cluster: {ontbreekt}")

    # Vragen die in geen enkel pad staan maar wel meewegen in de beoordeling:
    # randvoorwaarden voor de hele check (zoals 24/7 opvolging van kritieke meldingen).
    gebruikt = {vid for p in paden for rol in ("required", "limited", "response") for vid in p[rol]}
    randvoorwaarden = []
    for vid, v in vragen.items():
        if vid in gebruikt:
            continue
        randvoorwaarden.append({
            "id": vid,
            "titel": generiek(v["actie"]).rstrip("."),
            "vraag": {k: w for k, w in velden(v).items() if w},
            "werking": (
                "Geldt voor de hele beoordeling, niet voor een enkel pad. Zonder deze voorwaarde blijft een "
                "pad met alleen reactieve maatregelen open in plaats van reactief beheerst."
            ),
        })

    return {
        "versie": "2026-08",
        "toelichting": (
            "Eén bron voor de aanvalspaden van de publieke sector. Vijf clusters voor het overzicht, "
            "achttien bladeren voor het detail. Zelfcheck, risicoanalyse en meting lezen dit bestand; "
            "wijzig hier, niet in de code."
        ),
        "clusters": [
            {"id": cid, "titel": titel, "kern": kern, "bladeren": aps}
            for cid, titel, kern, aps in CLUSTERS
        ],
        "bladeren": bladeren,
        "randvoorwaarden": randvoorwaarden,
    }


if __name__ == "__main__":
    data = bouw()
    DOEL.parent.mkdir(parents=True, exist_ok=True)
    DOEL.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{DOEL}: {len(data['clusters'])} clusters, {len(data['bladeren'])} bladeren, "
          f"{len(data['randvoorwaarden'])} randvoorwaarde(n)")
    for b in data["bladeren"]:
        print(f"  {b['id']} {b['type']:7s} {len(b['chokepoints'])} chokepoints  {b['titel'][:52]}")
