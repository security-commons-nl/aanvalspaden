"""Het handelingsperspectief: waar staat de handleiding, en waar staat hij nog niet.

De normverankering zegt wat je aantoont, dit zegt hoe je het doet. Wat er niet staat is hier net zo
belangrijk als wat er wel staat: een barriere zonder handleiding is een openstaande schrijfopdracht,
en die lijst is de redactieagenda van de kennisbank. Deze tests bewaken vier dingen:

1. Elke barriere heeft een handleiding, staat als gevraagd, of is met reden vrijgesteld. Nooit niets.
2. Elke gevraagde barriere zegt wat het artikel zou moeten dekken. Zonder die zin is het geen
   uitnodiging maar een leeg vakje, en daar komt niemand op af.
3. handelingsperspectief.json is een kopie van de kennisbank en wordt hier niet met de hand gemaakt.
4. Een barriere mag meer dan een handleiding hebben, maar hoogstens een fundering: als er twee
   startpunten zijn, weet de lezer niet waar hij begint.

Faalt hier iets, repareer dan de kennisbank of gevraagd.json, niet de test.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import mappingen as helper  # noqa: E402

DATA = helper.handelingsperspectief()
AGENDA = helper.gevraagd()
EM_DASH = re.compile(r"[—–]")
KENNISBANK_EXPORT = ROOT.parent / "kennisbank" / "handelingsperspectief.json"


def test_elke_barriere_is_belegd():
    """Stilte mag geen vergissing kunnen zijn, net als bij de normverankering."""
    alle = set(helper.barrieres())
    met = {h["barriere"] for h in DATA["handleidingen"]}
    gevraagd = {g["barriere"] for g in AGENDA["gevraagd"]}
    vrijgesteld = {n["barriere"] for n in AGENDA["geen_handleiding_nodig"]}

    vergeten = sorted(alle - met - gevraagd - vrijgesteld)
    assert not vergeten, (
        f"deze barrieres staan nergens. Koppel er in de kennisbank een handleiding aan, zet ze in "
        f"gevraagd.json met wat het artikel zou moeten dekken, of bij geen_handleiding_nodig met een "
        f"reden: {vergeten}"
    )
    for naam, groep in (("handleiding en gevraagd", met & gevraagd),
                        ("handleiding en vrijgesteld", met & vrijgesteld),
                        ("gevraagd en vrijgesteld", gevraagd & vrijgesteld)):
        assert not groep, f"barriere staat in twee lijsten ({naam}): {sorted(groep)}"


def test_stille_barrieres_is_leeg():
    """Dezelfde eis als hierboven, maar via de helper die de bouw gebruikt om af te breken."""
    assert helper.stille_barrieres() == []


def test_alle_verwijzingen_gaan_over_bestaande_barrieres():
    bekend = set(helper.barrieres())
    alles = ([h["barriere"] for h in DATA["handleidingen"]]
             + [g["barriere"] for g in AGENDA["gevraagd"]]
             + [n["barriere"] for n in AGENDA["geen_handleiding_nodig"]])
    onbekend = sorted(set(alles) - bekend)
    assert not onbekend, f"verwijzingen naar barrieres die niet in paden.json staan: {onbekend}"


@pytest.mark.parametrize("hl", DATA["handleidingen"],
                         ids=[f"{h['barriere']}-{h['item'].split('/')[-1]}" for h in DATA["handleidingen"]])
def test_handleiding_heeft_de_verplichte_velden(hl):
    for veld in ("barriere", "item", "titel", "rol", "url"):
        assert hl.get(veld), f"{hl['barriere']}: veld {veld} ontbreekt"
    assert hl["rol"] in helper.ROLLEN, (
        f"{hl['barriere']}: rol '{hl['rol']}' moet een van {helper.ROLLEN} zijn"
    )
    assert hl["url"].startswith("https://security-commons-nl.github.io/kennisbank/"), (
        f"{hl['barriere']}: de url wijst niet naar de kennisbank"
    )
    assert hl["url"].endswith("/"), f"{hl['barriere']}: de url mist de afsluitende schuine streep"
    assert not EM_DASH.search(hl["titel"]), f"{hl['barriere']}: em-dash in de titel (redactiestatuut)"


@pytest.mark.parametrize("barriere", sorted({h["barriere"] for h in DATA["handleidingen"]}))
def test_hoogstens_een_fundering_per_barriere(barriere):
    """Meer routes mag, twee startpunten niet: dan weet de lezer niet waar hij begint."""
    hls = helper.handleidingen_van(barriere)
    fundering = [h for h in hls if h["rol"] == "fundering"]
    assert len(fundering) <= 1, (
        f"{barriere} heeft {len(fundering)} handleidingen met rol fundering: "
        f"{[h['item'] for h in fundering]}. Maak er een fundering van en zet de rest op alternatief "
        "of verdieping."
    )
    assert hls == sorted(hls, key=lambda h: (helper.ROLLEN.index(h["rol"]), h["titel"])), (
        f"{barriere}: handleidingen staan niet op rol gesorteerd"
    )


@pytest.mark.parametrize("gv", AGENDA["gevraagd"], ids=[g["barriere"] for g in AGENDA["gevraagd"]])
def test_elke_gevraagde_barriere_zegt_wat_er_zou_moeten_staan(gv):
    """Een leeg vakje nodigt niemand uit; een concrete vraag wel."""
    tekst = gv.get("zou_moeten_dekken", "")
    assert len(tekst) >= 60, (
        f"{gv['barriere']}: 'zou moeten dekken' is te kort om iemand op af te laten komen. Schrijf "
        f"wat het artikel moet behandelen: {tekst!r}"
    )
    assert gv.get("cluster"), f"{gv['barriere']}: geen cluster, dus geen schrijfopdracht om bij te horen"
    assert not EM_DASH.search(tekst), f"{gv['barriere']}: em-dash (redactiestatuut)"
    assert tekst.rstrip().endswith("."), f"{gv['barriere']}: eindigt niet op een punt"


def test_schrijfopdrachten_zijn_gesorteerd_op_gewicht():
    opdrachten = helper.schrijfopdrachten()
    assert opdrachten, "geen schrijfopdrachten, terwijl er gevraagde barrieres zijn"
    gewichten = [o["gewicht"] for o in opdrachten]
    assert gewichten == sorted(gewichten, reverse=True), (
        "de backlog hoort op gewicht te staan: wat bij de meeste aanvalspaden meetelt, schrijf je eerst"
    )
    assert sum(len(o["barrieres"]) for o in opdrachten) == len(AGENDA["gevraagd"])


def test_een_randvoorwaarde_weegt_over_alle_paden():
    """Een randvoorwaarde hangt aan geen enkel pad, maar geldt overal.

    Zou hij op bladeren geteld worden, dan kwam hij op nul en zakte hij naar de bodem van de backlog,
    terwijl hij juist het breedst geldt.
    """
    randvoorwaarden = [r["vraag_id"] for r in helper.paden_bron.laad().get("randvoorwaarden", [])]
    for vid in randvoorwaarden:
        assert helper.gewicht_van_barriere(vid) >= len(helper.paden_bron.paden()), (
            f"{vid} is een randvoorwaarde en hoort over alle paden te wegen"
        )


def test_dekking_telt_op():
    telling = helper.dekking_handelingsperspectief()
    assert telling["met_handleiding"] + telling["gevraagd"] + telling["geen_nodig"] == telling["barrieres"]
    assert telling["open"] == telling["gevraagd"] + telling["geen_nodig"]


def test_het_gat_is_zichtbaar_en_niet_weggepoetst():
    """De waarde van deze lijst zit in het gat. Verdwijnt dat, dan is er iets mis.

    Deze test is geen doel op zich: hij vangt af dat iemand ooit de gevraagde barrieres leeghaalt om
    de lijst er beter uit te laten zien, in plaats van artikelen te schrijven.
    """
    telling = helper.dekking_handelingsperspectief()
    assert telling["gevraagd"] > 0, (
        "geen enkele openstaande schrijfopdracht. Is alles echt geschreven, verwijder dan deze test "
        "bewust in plaats van hem te laten slagen door de lijst leeg te maken."
    )


@pytest.mark.skipif(not KENNISBANK_EXPORT.is_file(),
                    reason="kennisbank staat niet naast deze repo; in CI wordt hij uitgecheckt")
def test_de_kopie_is_gelijk_aan_de_kennisbank():
    """De kennisbank is de bron. Loopt de kopie achter, dan belooft de site iets wat er niet is."""
    import hashlib

    ruw = KENNISBANK_EXPORT.read_bytes()
    assert DATA["bron"]["sha256"] == hashlib.sha256(ruw).hexdigest(), (
        "handelingsperspectief.json loopt achter op de kennisbank. "
        "Draai: python tools/haal_handelingsperspectief.py"
    )
    export = json.loads(ruw.decode("utf-8"))
    assert DATA["handleidingen"] == export["handleidingen"]
    assert DATA["zonder_handleiding"] == export["zonder_handleiding"]


def test_de_kopie_wordt_niet_met_de_hand_onderhouden():
    """Wie hem toch bijwerkt, moet het script draaien; anders staat er een verkeerde sha256 onder."""
    assert "haal_handelingsperspectief.py" in DATA["versie"]
    assert set(DATA) == {"versie", "toelichting", "bron", "handleidingen", "zonder_handleiding"}, (
        "onbekend veld in de kopie; voeg het toe aan haal_handelingsperspectief.py, niet met de hand"
    )
