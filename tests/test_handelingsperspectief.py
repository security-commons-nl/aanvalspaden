"""Het handelingsperspectief: waar staat de handleiding, en waar staat hij nog niet.

De normverankering zegt wat je aantoont, dit zegt hoe je het doet. Wat er niet staat is hier net zo
belangrijk als wat er wel staat: een barriere zonder handleiding is een openstaande schrijfopdracht,
en die lijst is de redactieagenda van de kennisbank. Deze tests bewaken drie dingen:

1. Elke barriere heeft een handleiding, staat als gevraagd, of is met reden vrijgesteld. Nooit niets.
2. Elke gevraagde barriere zegt wat het artikel zou moeten dekken. Zonder die zin is het geen
   uitnodiging maar een leeg vakje, en daar komt niemand op af.

Faalt hier iets, repareer dan de mapping of het kennisbank-item, niet de test.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import mappingen as helper  # noqa: E402

DATA = helper.handelingsperspectief()
EM_DASH = re.compile(r"[—–]")


def test_elke_barriere_is_belegd():
    """Stilte mag geen vergissing kunnen zijn, net als bij de normverankering."""
    alle = set(helper.barrieres())
    met = {h["barriere"] for h in DATA["handleidingen"]}
    gevraagd = {g["barriere"] for g in DATA["gevraagd"]}
    vrijgesteld = {n["barriere"] for n in DATA["geen_handleiding_nodig"]}

    vergeten = sorted(alle - met - gevraagd - vrijgesteld)
    assert not vergeten, (
        f"deze barrieres staan nergens. Zet ze bij handleidingen, bij gevraagd met wat het artikel "
        f"zou moeten dekken, of bij geen_handleiding_nodig met een reden: {vergeten}"
    )
    for naam, groep in (("handleiding en gevraagd", met & gevraagd),
                        ("handleiding en vrijgesteld", met & vrijgesteld),
                        ("gevraagd en vrijgesteld", gevraagd & vrijgesteld)):
        assert not groep, f"barriere staat in twee lijsten ({naam}): {sorted(groep)}"


def test_alle_verwijzingen_gaan_over_bestaande_barrieres():
    bekend = set(helper.barrieres())
    alles = ([h["barriere"] for h in DATA["handleidingen"]]
             + [g["barriere"] for g in DATA["gevraagd"]]
             + [n["barriere"] for n in DATA["geen_handleiding_nodig"]])
    onbekend = sorted(set(alles) - bekend)
    assert not onbekend, f"verwijzingen naar barrieres die niet in paden.json staan: {onbekend}"


@pytest.mark.parametrize("hl", DATA["handleidingen"], ids=[h["barriere"] for h in DATA["handleidingen"]])
def test_handleiding_heeft_de_verplichte_velden(hl):
    for veld in ("barriere", "item", "titel", "paragraaf", "dekking", "reden"):
        assert hl.get(veld), f"{hl['barriere']}: veld {veld} ontbreekt"
    assert hl["dekking"] in ("volledig", "gedeeltelijk"), (
        f"{hl['barriere']}: dekking is volledig of gedeeltelijk. Dekt het item de barriere niet echt, "
        "zet hem dan bij gevraagd; half verwijzen helpt niemand."
    )
    assert not EM_DASH.search(hl["reden"]), f"{hl['barriere']}: em-dash in de reden (redactiestatuut)"
    assert hl["reden"].rstrip().endswith("."), f"{hl['barriere']}: reden eindigt niet op een punt"


@pytest.mark.parametrize("gv", DATA["gevraagd"], ids=[g["barriere"] for g in DATA["gevraagd"]])
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
    assert sum(len(o["barrieres"]) for o in opdrachten) == len(DATA["gevraagd"])


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
    assert telling["volledig"] + telling["gedeeltelijk"] == telling["met_handleiding"]


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
