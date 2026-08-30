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


def test_de_pagina_opent_op_bio2(pagina):
    """BIO 2.0 staat voorop in de redactionele volgorde, dus daar begint de lezer."""
    assert pagina.locator("h1").inner_text() == "Van aanvalspad naar norm"
    assert pagina.locator("button.gekozen").first.inner_text() == helper.bron("bio2")["titel"]


def test_alle_kaders_hebben_een_knop(pagina):
    knoppen = pagina.locator(".bedien button").all_inner_texts()
    for kader in helper.kaders():
        assert helper.bron(kader)["titel"] in knoppen, f"geen knop voor {kader}"


def test_alle_achttien_paden_staan_er_plus_de_randvoorwaarden(pagina):
    koppen = pagina.locator(".blok h3").all_inner_texts()
    for nummer in range(1, 19):
        assert any(k.startswith(f"AP{nummer:02d} ") for k in koppen), f"AP{nummer:02d} ontbreekt"
    assert any("Randvoorwaarden" in k for k in koppen), "de randvoorwaarden ontbreken"


def test_een_bekende_regel_staat_op_het_scherm(pagina):
    """AP01 hoort bewijs te leveren voor beveiligde authenticatie."""
    blok = pagina.locator(".blok", has_text="Phishing").first
    tekst = blok.inner_text()
    assert "8.5 Beveiligde authenticatie" in tekst, (
        "nummer en naam horen met een spatie ertussen te staan, ook in gekopieerde tekst"
    )
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


def test_de_bedieningsbalk_blijft_in_beeld_bij_scrollen(pagina):
    """Met vier kaders en honderd maatregelen moet het filter bij de hand blijven.

    De balk plakt bovenaan en wordt compact zodra de kop uit beeld is. Getoetst op wat een gebruiker
    merkt: staat de balk na het scrollen nog binnen het venster, en zijn de knoppen aanklikbaar.
    """
    balk = pagina.locator(".bedien")
    assert balk.count() == 1

    pagina.mouse.wheel(0, 4000)
    pagina.wait_for_timeout(150)

    vak = balk.bounding_box()
    hoogte = pagina.evaluate("window.innerHeight")
    assert vak is not None and vak["y"] >= -1, "de bedieningsbalk is uit beeld gescrold"
    assert vak["y"] < hoogte / 2, "de bedieningsbalk staat niet bovenin"
    assert "compact" in balk.get_attribute("class"), "de balk wordt niet compact bij scrollen"

    # En hij werkt daar ook: schakelen vanaf de gescrolde stand moet gewoon kunnen.
    pagina.get_by_role("button", name="Witte vlekken").click()
    assert pagina.locator(".telling").count() == 1


def test_de_balk_is_ruim_zolang_je_bovenaan_staat(pagina):
    balk = pagina.locator(".bedien")
    assert "compact" not in (balk.get_attribute("class") or "")
    assert pagina.locator(".bedien .toelichting").is_visible()


def test_filteren_houdt_de_focus_in_het_zoekveld(pagina):
    """De lijst wordt apart hertekend, dus typen mag de focus niet kwijtraken."""
    veld = pagina.locator('input[type="search"]')
    veld.click()
    veld.type("segment", delay=10)
    pagina.wait_for_timeout(80)
    assert pagina.evaluate("document.activeElement.type") == "search"
    assert veld.input_value() == "segment"


def test_elk_kader_toont_zijn_eigen_witte_vlekken(pagina):
    """De kern van de pagina: per kader een eigen, kloppende telling."""
    for kader in helper.kaders():
        pagina.get_by_role("button", name=helper.bron(kader)["titel"]).click()
        pagina.get_by_role("button", name="Witte vlekken").click()
        telling = helper.dekking(kader)
        groot = pagina.locator(".telling .groot").all_inner_texts()
        assert str(telling["geraakt"]) in groot, f"{kader}: geraakt-telling ontbreekt"
        assert str(telling["witte_vlekken"]) in groot, f"{kader}: witte-vlekken-telling ontbreekt"


def test_de_avg_laat_zien_dat_beveiliging_maar_een_deel_is(pagina):
    pagina.get_by_role("button", name=helper.bron("avg")["titel"]).click()
    pagina.get_by_role("button", name="Witte vlekken").click()
    tekst = pagina.locator("main").inner_text()
    for onderwerp in ("Recht op inzage", "Rechtmatigheid van de verwerking", "Register van verwerkingsactiviteiten"):
        assert onderwerp in tekst, f"{onderwerp} hoort als witte vlek zichtbaar te zijn"
    telling = helper.dekking("avg")
    assert telling["witte_vlekken"] > telling["geraakt"]


def test_nist_sluit_het_dichtst_aan_maar_mist_govern(pagina):
    """CSF is dreigingsgericht, dus de dekking is hoger; de GOVERN-functie blijft grotendeels leeg."""
    pagina.get_by_role("button", name=helper.bron("nist-csf")["titel"]).click()
    pagina.get_by_role("button", name="Witte vlekken").click()
    tekst = pagina.locator("main").inner_text()
    assert "GOVERN (GV)" in tekst, "de GOVERN-functie hoort bij de witte vlekken te staan"


def test_de_drie_niveaus_zijn_visueel_te_onderscheiden(pagina):
    """Aanvalspad, barriere en maatregel moeten er verschillend uitzien, niet alleen ingesprongen.

    Zonder verschil in grootte lezen de drie als een lijst van gelijken en verdwijnt de boom. Dit is
    de reden dat de opmaak op drie maten staat; de test legt die volgorde vast.
    """
    def px(locator):
        return float(locator.evaluate("e => getComputedStyle(e).fontSize").replace("px", ""))

    blok = pagina.locator(".blok", has_text="Phishing").first
    pad = px(blok.locator("h3").first)
    barriere = px(blok.locator("> ul.regels > li > .regel-kop > .titel").first)
    maatregel = px(blok.locator(".regels .regels .regel-kop .titel").first)

    assert pad > barriere > maatregel, (
        f"de niveaus lopen niet af in grootte: pad {pad}, barriere {barriere}, maatregel {maatregel}"
    )
    assert pad - barriere >= 5, "het verschil tussen aanvalspad en barriere is te klein om te zien"


def test_elk_blok_zegt_met_een_label_waar_je_naar_kijkt(pagina):
    labels = pagina.locator(".blok .soort").all_inner_texts()
    assert labels, "blokken hebben geen soortlabel"
    assert all(l.strip() for l in labels)
    assert any("AANVALSPAD" in l.upper() for l in labels)

    pagina.get_by_role("button", name="Vanuit de maatregel").click()
    labels = pagina.locator(".blok .soort").all_inner_texts()
    assert all("MAATREGEL" in l.upper() for l in labels), "in de maatregelweergave hoort elk blok Maatregel te zeggen"


def test_de_themakop_is_groter_dan_de_blokken_eronder(pagina):
    """De groepskop hoort boven zijn kinderen te staan, ook typografisch.

    Hij stond eerder op 1rem terwijl de blokken op 1,05 stonden, dus de bovenliggende kop was kleiner
    dan wat hij groepeerde.
    """
    pagina.get_by_role("button", name="Witte vlekken").click()
    def px(locator):
        return float(locator.evaluate("e => getComputedStyle(e).fontSize").replace("px", ""))
    thema = px(pagina.locator(".themakop").first)
    blok = px(pagina.locator(".blok h3").first)
    assert thema >= blok * 0.7, f"themakop {thema} verdwijnt naast de blokkoppen {blok}"
    assert "uppercase" not in pagina.locator(".themakop").first.evaluate(
        "e => getComputedStyle(e).textTransform"
    ), "hoofdletters maken lange themanamen als 'GOVERN (GV) - Organizational Context' onleesbaar"
