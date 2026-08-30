"""Bouwt de crosswalk: één zelfstandig HTML-bestand uit paden.json en de mappingen.

Zelfde afspraak als check/bouw.py: geen bundler, geen dependencies, geen externe verwijzingen. De
data gaat als JSON in dezelfde scripttag als de app, zodat er precies één script en één stylesheet
is en het Content-Security-Policy hun sha256-hash kan vastleggen, met default-src 'none' voor de
rest. De offlinebelofte is daarmee controleerbaar in plaats van beloofd.

Wat de pagina toont is vooraf uitgerekend, niet in de browser: per aanvalspad de regels, per
maatregel de barrieres, en de witte vlekken. De browser tekent alleen.

Aanroep:
    python mappingen/bouw.py                 # schrijft mappingen/dist/index.html
    python mappingen/bouw.py <doelmap>
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent
BRON = HIER / "bron"

sys.path.insert(0, str(REPO))

from tools import mappingen as helper  # noqa: E402
from tools import paden as paden_bron  # noqa: E402

INLEIDING = (
    "De zelfcheck vraagt naar barrieres tegen aanvalspaden, niet naar normen. Deze pagina legt het "
    "verband: welk bewijs uit een barriere zegt iets over welke maatregel, en net zo belangrijk, "
    "over welke maatregelen het niets zegt."
)

BELOFTE = (
    "Er is een relatie en die heeft een richting: een barriere levert bewijs voor een maatregel. "
    "Nooit dat je eraan voldoet. Wie de zelfcheck heeft gedaan, heeft antwoorden; wie het bewijs "
    "erbij legt, heeft materiaal voor een gesprek met de auditor. Het oordeel blijft van de auditor."
)

WITTE_VLEKKEN_TEKST = {
    "bio2": (
        "Deze maatregelen van BIO 2.0 worden door geen enkele barriere uit de zelfcheck geraakt. "
        "Dat is geen tekort van de zelfcheck. Een dreigingsgerichte vragenlijst gaat over de "
        "technische aanvalsoppervlakte; BIO 2.0 gaat daarnaast over beleid, screening, fysieke "
        "toegang, classificatie en leveranciersmanagement. Dit is precies de grens tussen wat een "
        "zelfcheck aantoont en wat een normenkader verder van je vraagt."
    ),
    "wpg": (
        "Van de 36 maatregelen in dit kader raakt de zelfcheck er een minderheid, en dat hoort zo. "
        "Het Wpg-toetsingskader gaat over rechtmatige verwerking van politiegegevens: doelbinding, "
        "bewaartermijnen, verstrekking, de rechten van betrokkenen en het toezicht daarop. Geen "
        "aanvalspad zegt daar iets over. Wat de zelfcheck wel raakt is beveiliging: maatregel 6 en "
        "de technische maatregelen uit bijlage 4, die volgens de handreiking naast de BIO gelden."
    ),
}


def sha256_csp(inhoud: str) -> str:
    """De hashvorm die het Content-Security-Policy verwacht."""
    return "sha256-" + base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()


def bouw_kader(kader: str, barrieres: dict) -> dict:
    """Alles wat de pagina van een kader nodig heeft, vooraf uitgerekend."""
    data = helper.mapping(kader)
    bron_data = helper.bron(kader)
    paden = paden_bron.laad()

    per_barriere: dict[str, list[dict]] = {}
    per_norm: dict[str, list[dict]] = {}
    for regel in data["regels"]:
        kort = {k: regel[k] for k in ("barriere", "norm", "sterkte", "reden")}
        per_barriere.setdefault(regel["barriere"], []).append(kort)
        per_norm.setdefault(regel["norm"], []).append(kort)

    ongekoppeld = {x["barriere"]: x["reden"] for x in data["ongekoppeld"]}

    bladeren = []
    for blad in paden["bladeren"]:
        chokepoints = []
        for cp in blad["chokepoints"]:
            chokepoints.append({
                "id": cp["id"],
                "titel": cp["titel"],
                "barriere": cp["vraag_id"],
                "bewijs": cp.get("bewijs", ""),
                "regels": per_barriere.get(cp["vraag_id"], []),
            })
        bladeren.append({
            "id": blad["id"],
            "titel": blad["titel"],
            "type": blad["type"],
            "scenario": blad.get("scenario", ""),
            "chokepoints": chokepoints,
        })

    # De randvoorwaarden horen bij geen enkel pad, maar hun bewijs telt wel mee. Ze krijgen een eigen
    # blok onderaan, zodat een lezer ze niet mist.
    randvoorwaarden = []
    for rand in paden.get("randvoorwaarden", []):
        randvoorwaarden.append({
            "id": rand["id"],
            "titel": rand["titel"],
            "barriere": rand["vraag_id"],
            "bewijs": rand.get("bewijs", ""),
            "regels": per_barriere.get(rand["vraag_id"], []),
        })
    if randvoorwaarden:
        bladeren.append({
            "id": "RV",
            "titel": "Randvoorwaarden, over alle paden heen",
            "type": "randvoorwaarde",
            "scenario": "Deze vragen wegen mee bij elk pad in plaats van bij een enkel pad.",
            "chokepoints": randvoorwaarden,
        })

    return {
        "titel": bron_data["titel"],
        "herkomst": f"{bron_data['bron'].get('versie', '')}, {bron_data['bron'].get('naam', '')}".strip(", "),
        "toelichting": data["toelichting"],
        "maatregelen": bron_data["maatregelen"],
        "barrieres": barrieres,
        "bladeren": bladeren,
        "perNorm": per_norm,
        "ongekoppeld": ongekoppeld,
        "ongekoppeldeLijst": data["ongekoppeld"],
        "witteVlekken": helper.witte_vlekken(kader),
        "witteVlekkenTekst": WITTE_VLEKKEN_TEKST.get(kader, ""),
        "dekking": helper.dekking(kader),
    }


def verzamel() -> tuple[dict, dict]:
    barrieres = helper.barrieres()
    kaders = {kader: bouw_kader(kader, barrieres) for kader in helper.kaders()}
    bron = {
        "versie": max(helper.mapping(k)["versie"] for k in helper.kaders()),
        "inleiding": INLEIDING,
        "belofte": BELOFTE,
    }
    return bron, kaders


def bouw(doel: pathlib.Path) -> pathlib.Path:
    bron, kaders = verzamel()

    css = (BRON / "app.css").read_text(encoding="utf-8").strip()
    js = (BRON / "app.js").read_text(encoding="utf-8").strip()
    sjabloon = (BRON / "index.html").read_text(encoding="utf-8")

    def als_json(waarde: object) -> str:
        # </script> in de data zou de scripttag vroegtijdig sluiten; JSON mag die slash escapen.
        return json.dumps(waarde, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    script = (
        "window.__BRON__ = " + als_json(bron) + ";\n"
        "window.__MAPPINGEN__ = " + als_json(kaders) + ";\n" + js
    )

    html = (sjabloon
            .replace("__CSS__", css)
            .replace("__SCRIPT__", script)
            .replace("__SCRIPT_HASH__", sha256_csp(script).removeprefix("sha256-"))
            .replace("__STYLE_HASH__", sha256_csp(css).removeprefix("sha256-")))

    for rest in ("__CSS__", "__SCRIPT__", "__SCRIPT_HASH__", "__STYLE_HASH__"):
        assert rest not in html, f"placeholder {rest} niet ingevuld"

    doel.mkdir(parents=True, exist_ok=True)
    uit = doel / "index.html"
    uit.write_bytes(html.encode("utf-8"))
    return uit


if __name__ == "__main__":
    doel = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HIER / "dist"
    uit = bouw(doel)
    kb = uit.stat().st_size / 1024
    tellingen = ", ".join(
        f"{k}: {helper.dekking(k)['geraakt']}/{helper.dekking(k)['maatregelen']}" for k in helper.kaders()
    )
    print(f"{uit}: {kb:.0f} kB, zelfstandig en offline ({tellingen})")
