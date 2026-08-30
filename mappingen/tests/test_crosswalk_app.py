"""De crosswalk in een echte browser: schakelen tussen kaders, weergaven en zoeken.

Deze tests bewijzen wat een unit-test niet kan: dat de pagina doet wat een lezer verwacht, en dat
wat er op het scherm staat gelijk is aan de mapping in de repo. Vooral de witte vlekken tellen: dat
getal is het inhoudelijke punt van deze pagina, dus het mag niet uit de lucht komen.

Overslaan als Playwright of de browser ontbreekt; CI installeert beide.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
MAP = HIER.parent
REPO = MAP.parent
sys.path.insert(0, str(REPO))
# conftest.py laadt mappingen/bouw.py onder deze naam; check/ heeft ook een bouw.py.
import crosswalk_bouw as bouw  # noqa: E402

from tools import mappingen as helper  # noqa: E402

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright niet beschikbaar")


@pytest.fixture(scope="module")
def bestand(tmp_path_factory) -> str:
    return bouw.bouw(tmp_path_factory.mktemp("dist")).as_uri()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as fout:  # pragma: no cover
            pytest.skip(f"chromium niet beschikbaar: {fout}")
        yield b
        b.close()


@pytest.fixture()
def pagina(browser, bestand):
    p = browser.new_page()
    fouten: list[str] = []
    p.on("pageerror", lambda e: fouten.append(str(e)))
    p.goto(bestand)
    p.wait_for_selector("h1")
    yield p
    assert not fouten, f"javascriptfouten op de pagina: {fouten}"
    p.close()


def test_de_pagina_opent_op_het_eerste_kader(pagina):
    assert pagina.locator("h1").inner_text() == "Van aanvalspad naar norm"
    assert pagina.locator("button.gekozen").first.inner_text() == helper.bron("bio2")["titel"]


def test_alle_achttien_paden_staan_er_plus_de_randvoorwaarden(pagina):
    koppen = pagina.locator(".blok h3").all_inner_texts()
    for nummer in range(1, 19):
        assert any(k.startswith(f"AP{nummer:02d}.") for k in koppen), f"AP{nummer:02d} ontbreekt"
    assert any("Randvoorwaarden" in k for k in koppen), "de randvoorwaarden ontbreken"


def test_een_bekende_regel_staat_op_het_scherm(pagina):
    """AP01 hoort bewijs te leveren voor beveiligde authenticatie."""
    blok = pagina.locator(".blok", has_text="AP01.").first
    tekst = blok.inner_text()
    assert "8.5 Beveiligde authenticatie" in tekst
    assert "volledig" in tekst
    assert "Bewijs:" in tekst


def test_schakelen_naar_de_maatregelweergave(pagina):
    pagina.get_by_role("button", name="Vanuit de maatregel").click()
    koppen = pagina.locator(".blok h3").all_inner_texts()
    assert len(koppen) == len(helper.maatregelen("bio2"))
    assert any(k.startswith("8.5 ") for k in koppen)
    # Een maatregel zonder regels hoort als witte vlek herkenbaar te zijn.
    assert pagina.locator(".sterkte.geen", has_text="witte vlek").count() > 0


def test_witte_vlekken_tonen_hetzelfde_getal_als_de_bron(pagina):
    pagina.get_by_role("button", name="Witte vlekken").click()
    telling = helper.dekking("bio2")
    groot = pagina.locator(".telling .groot").all_inner_texts()
    assert str(telling["geraakt"]) in groot
    assert str(telling["witte_vlekken"]) in groot
    assert str(telling["maatregelen"]) in groot


def test_wpg_laat_zien_dat_het_kader_breder_is_dan_security(pagina):
    pagina.get_by_role("button", name=helper.bron("wpg")["titel"]).click()
    pagina.get_by_role("button", name="Witte vlekken").click()
    tekst = pagina.locator("main").inner_text()
    for onderwerp in ("Bewaartermijnen", "Rechten van de betrokkene", "Register van verwerkingen"):
        assert onderwerp in tekst, f"{onderwerp} hoort als witte vlek zichtbaar te zijn"
    telling = helper.dekking("wpg")
    assert telling["witte_vlekken"] > telling["geraakt"]


def test_de_ongekoppelde_barrieres_staan_met_hun_reden_op_de_witte_vlekken(pagina):
    pagina.get_by_role("button", name=helper.bron("wpg")["titel"]).click()
    pagina.get_by_role("button", name="Witte vlekken").click()
    tekst = pagina.locator("main").inner_text()
    assert "Barrieres die dit kader niet raakt" in tekst
    for paar in helper.mapping("wpg")["ongekoppeld"]:
        barriere = helper.barrieres()[paar["barriere"]]
        assert barriere["titel"] in tekst, f"{paar['barriere']} ontbreekt bij de ongekoppelde"


def test_zoeken_filtert_en_houdt_de_focus(pagina):
    veld = pagina.locator('input[type="search"]')
    veld.fill("segmentatie")
    pagina.wait_for_timeout(50)
    koppen = pagina.locator(".blok h3").all_inner_texts()
    assert koppen, "zoeken op een bestaand woord levert niets op"
    assert len(koppen) < 18, "zoeken filtert niet"
    assert pagina.evaluate("document.activeElement.type") == "search", "de focus springt weg tijdens typen"


def test_zoeken_zonder_resultaat_zegt_dat_netjes(pagina):
    pagina.locator('input[type="search"]').fill("ditwoordbestaatniet")
    pagina.wait_for_timeout(50)
    assert pagina.locator(".geenresultaat").count() == 1


def test_de_pagina_slaat_niets_op(pagina):
    """Deze pagina leest alleen. Geen opslag betekent ook geen cookiegesprek."""
    assert pagina.evaluate("Object.keys(localStorage).length") == 0
    assert pagina.evaluate("Object.keys(sessionStorage).length") == 0
    assert pagina.evaluate("document.cookie") == ""
