"""De pagina in een echte browser: bestanden kiezen, toetsen, exporteren, afdrukken.

Deze tests bewijzen wat een unit-test niet kan: dat wat op het scherm staat gelijk is aan wat
meting/reken.py uitrekent, en dat de pagina met niemand praat.
"""
from __future__ import annotations

import gzip
import json
import pathlib

import pytest

from conftest import FIXTURES, PEILDATUM, doorloop_dossier

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright niet beschikbaar")


@pytest.fixture(scope="module")
def bestand(tmp_path_factory) -> str:
    import bouw as bouwer
    return bouwer.bouw(tmp_path_factory.mktemp("meting-dist")).as_uri()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as pw:
        try:
            gestart = pw.chromium.launch()
        except Exception as fout:
            pytest.skip(f"chromium niet beschikbaar: {fout}")
        yield gestart
        gestart.close()


@pytest.fixture
def pagina(browser, bestand):
    context = browser.new_context()
    blad = context.new_page()
    fouten: list[str] = []
    blad.on("pageerror", lambda e: fouten.append(str(e)))
    blad.on("console", lambda m: fouten.append(m.text) if m.type == "error" else None)
    blad.goto(bestand)
    blad.evaluate("() => window.localStorage.clear()")
    blad.reload()
    zet_peildatum(blad, PEILDATUM)
    yield blad
    assert not fouten, f"fouten in de browser: {fouten}"
    context.close()


def zet_peildatum(blad, datum: str) -> None:
    blad.fill("#org-peildatum", datum)
    blad.dispatch_event("#org-peildatum", "change")


def wacht_op(blad, item: str, kiezer: str, tekst: str | None = None) -> None:
    """Wacht op een element binnen een item; het kan tussendoor opnieuw getekend zijn, dus nooit
    blind dereferencen. Zonder tekst: wacht tot er iets staat. Met tekst: tot het dat precies is."""
    blad.wait_for_function(
        "([id, kiezer, tekst]) => {"
        " var e = document.querySelector('[data-item=\"' + id + '\"] ' + kiezer);"
        " if (!e) return false;"
        " var t = e.textContent.trim();"
        " return tekst === null ? t.length > 0 : t === tekst; }",
        arg=[item, kiezer, tekst])


def kies(blad, item: str, naam: str, wordt: str | None = None) -> None:
    blad.set_input_files(f'[data-item="{item}"] input[type=file]', str(FIXTURES / naam))
    wacht_op(blad, item, ".bestand")
    if wordt is not None:
        wacht_op(blad, item, ".verdict", wordt)


def verdict(blad, item: str) -> str:
    return blad.text_content(f'[data-item="{item}"] .verdict').strip()


def dossier_uit(blad) -> dict:
    return json.loads(blad.evaluate("() => window.localStorage.getItem('aanvalspaden-meting-v1')"))


def laad_dossier(blad, dossier: dict) -> None:
    blad.evaluate("(tekst) => window.localStorage.setItem('aanvalspaden-meting-v1', tekst)",
                  json.dumps(dossier))
    blad.reload()


# ---------------------------------------------------------------- de schermen

def test_startscherm(pagina, regels):
    assert pagina.locator('[role="tab"]').count() == 5
    assert pagina.locator("[data-item]").count() == len(regels["items"])
    assert "nog geen bewijs" in pagina.text_content('[data-item="1.1"] .verdict')
    assert "0 van 41 gemeten" in pagina.text_content("#dossier-status")


def test_een_bestand_dekt_twee_items(pagina, reken, regels):
    kies(pagina, "1.1", "crown-jewels.csv")
    assert verdict(pagina, "1.1") == "voldoet"
    assert verdict(pagina, "1.2") == "voldoet"
    dossier = dossier_uit(pagina)
    assert dossier["metingen"]["1.1"]["sha256"] == dossier["metingen"]["1.2"]["sha256"]
    assert "3 van 3 (100%)" in pagina.text_content('[data-item="1.2"] .samenvatting')


def test_fail_en_unparsed_op_het_scherm(pagina, tmp_path):
    kies(pagina, "3.4", "laps.csv")
    assert verdict(pagina, "3.4") == "voldoet niet"
    assert "2 van 3 (67%)" in pagina.text_content('[data-item="3.4"] .samenvatting')
    kapot = tmp_path / "zonder-kolom.csv"
    kapot.write_text("device_name,iets_anders\nA,true\n", encoding="utf-8")
    pagina.set_input_files('[data-item="3.4"] input[type=file]', str(kapot))
    wacht_op(pagina, "3.4", ".verdict", "niet te lezen")
    assert "laps_configured" in pagina.text_content('[data-item="3.4"]')


def test_firewallconfig_dekt_vier_items(pagina, reken, regels):
    kies(pagina, "2.1", "fortigate-config.txt")
    for item in ("2.1", "2.2", "2.3", "2.4"):
        assert verdict(pagina, item) == "voldoet", item
    verwacht = reken.toets("fw_config", (FIXTURES / "fortigate-config.txt").read_text(encoding="utf-8"),
                           PEILDATUM, regels)
    dossier = dossier_uit(pagina)
    for item, waarde in verwacht["verdicts"].items():
        assert dossier["metingen"][item]["verdict"] == waarde


def test_termijn_kantelt_met_de_peildatum(pagina):
    kies(pagina, "5.4", "nmap-extern.xml")
    assert verdict(pagina, "5.4") == "voldoet"
    zet_peildatum(pagina, "2026-09-25")
    assert "peildatum is gewijzigd" in pagina.text_content("#dossier-status")
    kies(pagina, "5.4", "nmap-extern.xml", "te oud")
    assert verdict(pagina, "5.4") == "te oud"


DATUMS = ["2026-08-30", "2026-08-30T10:00", "2026-08-30T10:00:00", "2026-08-30T10:00:00Z",
          "2026-08-30T00:00:00.000Z", "2026-08-30T10:00:00.123456+02:00", "2026-08-30 10:00:00",
          "30-08-2026", "gescand op 2026/8/30 door de scanner", "", "geen datum", "2026-13-40"]


def test_datumlezer_spiegelt_python(pagina, reken):
    """De browser moet elke datumvorm net zo lezen als reken.py; een gemiste vorm wist stil elke termijn."""
    uit = pagina.evaluate(
        "(waarden) => waarden.map(w => [window.reken.dagen_tussen(w, '2026-09-03'),"
        " window.reken.uren_tussen(w, '2026-09-03')])", DATUMS)
    for waarde, (dagen, uren) in zip(DATUMS, uit):
        assert dagen == reken.dagen_tussen(waarde, PEILDATUM), waarde
        verwacht_uren = reken.uren_tussen(waarde, PEILDATUM)
        if verwacht_uren is None:
            assert uren is None, waarde
        else:
            assert abs(uren - verwacht_uren) < 0.001, waarde
    assert uit[4][0] == 4, "een ISO-tijd met milliseconden hoort gewoon gelezen te worden"


def test_document_plakken(pagina):
    tekst = (FIXTURES / "pentest.txt").read_text(encoding="utf-8")
    pagina.fill('[data-document="9.3"]', tekst)
    pagina.click('[data-item="9.3"] .toets')
    wacht_op(pagina, "9.3", ".verdict", "voldoet")
    pagina.fill('[data-document="9.3"]', "Een tekst zonder de gevraagde woorden.")
    pagina.click('[data-item="9.3"] .toets')
    wacht_op(pagina, "9.3", ".verdict", "niet te lezen")
    assert "trefwoord niet gevonden" in pagina.text_content('[data-item="9.3"]')


def test_iamscan_tar_gz(pagina, reken, regels, tmp_path):
    gz = tmp_path / "web01-iamscan.tar.gz"
    gz.write_bytes(gzip.compress((FIXTURES / "web01-iamscan.tar").read_bytes()))
    pagina.set_input_files('[data-item="10.1"] input[type=file]', str(gz))
    wacht_op(pagina, "10.1", ".samenvatting")
    verwacht = reken.toets("iamscan_dump",
                           reken.dump_uit_tar((FIXTURES / "web01-iamscan.tar").read_bytes()),
                           PEILDATUM, regels)
    dossier = dossier_uit(pagina)
    for item, waarde in verwacht["verdicts"].items():
        assert dossier["metingen"][item]["verdict"] == waarde, item
    pagina.click("#tab-hosts")
    assert pagina.locator("[data-route]").count() == len(verwacht["analyse"]["routes"])
    assert pagina.locator("[data-bevinding]").count() == len(verwacht["analyse"]["bevindingen"])


def test_iamscan_map(pagina, reken, regels):
    """De tweede file-invoer bij 10.1 heeft webkitdirectory: een uitgepakte dump als map."""
    wortel = FIXTURES / "iamscan-dump" / "hosts"
    pagina.locator('[data-item="10.1"] input[type=file]').nth(1).set_input_files(str(wortel))
    wacht_op(pagina, "10.4", ".bestand")
    bestanden = {}
    for pad in sorted(wortel.rglob("*")):
        if pad.is_file():
            bestanden[str(pad.relative_to(wortel)).replace("\\", "/")] = pad.read_text(
                encoding="utf-8", errors="replace")
    verwacht = reken.toets("iamscan_dump", bestanden, PEILDATUM, regels)
    dossier = dossier_uit(pagina)
    assert verwacht["samenvatting"]["hosts"] == 3
    for item, waarde in verwacht["verdicts"].items():
        assert dossier["metingen"][item]["verdict"] == waarde, item


def test_paden_tonen_bewijs_en_witte_vlekken(pagina, reken, regels, paden, doorloop):
    laad_dossier(pagina, doorloop)
    pagina.click("#tab-paden")
    assert pagina.locator("[data-chokepoint]").count() == 76
    assert pagina.locator("tr.witte-vlek").count() == 54
    assert "22 van de 76" in pagina.text_content("#paden-samenvatting")
    cps = reken.per_chokepoint(regels, paden, doorloop)
    for cp_id in ("AP18-1", "AP11-3", "AP05-1"):
        rij = pagina.text_content(f'tr[data-chokepoint="{cp_id}"]')
        for meting in cps[cp_id]["items"]:
            assert meting["id"] in rij
        assert {"yes": "ja", "no": "nee", "unknown": "onbekend"}[cps[cp_id]["afgeleid"]] in \
            pagina.text_content(f'tr[data-chokepoint="{cp_id}"] .afgeleid')


def test_dashboard_gelijk_aan_de_referentie(pagina, reken, regels, paden, doorloop):
    laad_dossier(pagina, doorloop)
    pagina.click("#tab-dashboard")
    stand = reken.dashboard(regels, paden, doorloop)
    tellers = pagina.evaluate(
        "() => Object.fromEntries(Array.from(document.querySelectorAll('[data-teller]'))"
        ".map(e => [e.getAttribute('data-teller'), e.textContent]))")
    assert tellers["items.totaal"] == str(stand["items"]["totaal"])
    assert tellers["items.gemeten"] == str(stand["items"]["gemeten"])
    for verdict_naam, aantal in stand["verdict"].items():
        assert tellers["verdict." + verdict_naam] == str(aantal)
    for sleutel in ("totaal", "gemeten", "witte_vlekken"):
        assert tellers["chokepoints." + sleutel] == str(stand["chokepoints"][sleutel])
    for categorie in regels["categorieen"]:
        for verdict_naam, aantal in stand["categorie"][str(categorie["nummer"])].items():
            assert tellers[f"categorie.{categorie['nummer']}.{verdict_naam}"] == str(aantal)


def test_export_naar_de_zelfcheck(pagina, reken, regels, paden, doorloop, tmp_path):
    laad_dossier(pagina, doorloop)
    with pagina.expect_download() as download:
        pagina.click("#knop-zelfcheck-export")
    naam = download.value.suggested_filename
    assert naam.startswith("zelfcheck-antwoorden-uit-meting-") and naam.endswith(".json")
    doel = tmp_path / naam
    download.value.save_as(str(doel))
    inhoud = json.loads(doel.read_text(encoding="utf-8"))
    assert inhoud["formaat"] == "zelfcheck-antwoorden" and inhoud["bron"] == "meting"
    assert inhoud["antwoorden"] == reken.afgeleide_antwoorden(regels, paden, doorloop)
    assert "model" not in inhoud["antwoorden"]
    for vraag, herkomst in inhoud["herkomst"].items():
        assert herkomst["items"]


def test_export_zonder_metingen_weigert(pagina):
    pagina.click("#knop-zelfcheck-export")
    assert "meet eerst iets" in pagina.text_content("#dossier-status")


def test_opslaan_laden_wissen_herladen(pagina, tmp_path):
    pagina.fill("#org-naam", "Gemeente Voorbeeld")
    pagina.dispatch_event("#org-naam", "change")
    kies(pagina, "1.1", "crown-jewels.csv")
    with pagina.expect_download() as download:
        pagina.click("#knop-opslaan")
    assert download.value.suggested_filename.startswith("meting-dossier-gemeente-voorbeeld-")
    doel = tmp_path / "dossier.json"
    download.value.save_as(str(doel))
    opgeslagen = json.loads(doel.read_text(encoding="utf-8"))
    assert opgeslagen["formaat"] == "meting-dossier"
    assert opgeslagen["metingen"]["1.1"]["verdict"] == "pass"
    # Het dossier draagt geen ruwe export.
    assert "Paspoortuitgifte,Teamleider Burgerzaken" not in doel.read_text(encoding="utf-8")

    pagina.on("dialog", lambda d: d.accept())
    pagina.click("#knop-wissen")
    assert "0 van 41 gemeten" in pagina.text_content("#dossier-status")

    pagina.set_input_files("#bestand-laden", str(doel))
    pagina.wait_for_function(
        "() => document.getElementById('dossier-status').textContent.indexOf('1 van 41') >= 0"
        " || document.getElementById('dossier-status').textContent.indexOf('2 van 41') >= 0")
    assert pagina.input_value("#org-naam") == "Gemeente Voorbeeld"
    pagina.reload()
    assert pagina.input_value("#org-naam") == "Gemeente Voorbeeld"


def test_laden_weigert_verkeerd_bestand(pagina, tmp_path):
    verkeerd = tmp_path / "verkeerd.json"
    verkeerd.write_text('{"formaat": "iets anders"}', encoding="utf-8")
    pagina.set_input_files("#bestand-laden", str(verkeerd))
    pagina.wait_for_selector("#dossier-status.let-op")
    assert "geen meting-dossier" in pagina.text_content("#dossier-status")


def test_laden_meldt_andere_regelsversie(pagina, tmp_path, doorloop):
    ander = json.loads(json.dumps(doorloop))
    ander["regels_sha256"] = "a" * 64
    bestand = tmp_path / "ander.json"
    bestand.write_text(json.dumps(ander), encoding="utf-8")
    pagina.set_input_files("#bestand-laden", str(bestand))
    pagina.wait_for_selector("#dossier-status.let-op")
    assert "andere versie van de meetregels" in pagina.text_content("#dossier-status")


def test_filter_op_uitkomst(pagina, doorloop):
    laad_dossier(pagina, doorloop)
    pagina.select_option("#filter-verdict", "fail")
    pagina.wait_for_function("() => document.querySelectorAll('[data-item]').length === 3")
    getoond = pagina.eval_on_selector_all("[data-item]",
                                          "n => n.map(e => e.getAttribute('data-item'))")
    assert sorted(getoond) == ["10.1", "10.2", "3.4"]
    pagina.select_option("#filter-verdict", "")
    pagina.select_option("#filter-soort", "C")
    pagina.wait_for_function("() => document.querySelectorAll('[data-item]').length === 5")


def test_uitdraai_bevat_alles(pagina, regels, doorloop):
    laad_dossier(pagina, doorloop)
    pagina.click("#tab-uitdraai")
    tekst = pagina.text_content("#uitdraai-inhoud")
    assert "Gemeente Voorbeeld" in tekst
    for kop in ("1 Organisatie en peildatum", "2 Dashboard", "3 Bewijs per aanvalspad",
                "4 Per meetregel", "5 Linux-hosts", "6 Niet uit data te halen", "7 Verantwoording"):
        assert kop in tekst
    for item in regels["items"]:
        assert item["id"] in tekst
    vinger = pagina.evaluate("() => window.__BRON__.vingerafdruk")
    assert vinger in tekst


def test_afdrukken_toont_uitdraai(pagina):
    pagina.emulate_media(media="print")
    assert pagina.is_visible("#scherm-uitdraai")
    assert not pagina.is_visible("#scherm-items")
    pagina.emulate_media(media="screen")


def test_geen_netwerk(pagina, doorloop):
    verzoeken: list[str] = []
    pagina.on("request", lambda r: verzoeken.append(r.url)
              if not r.url.startswith(("file:", "data:", "blob:")) else None)
    laad_dossier(pagina, doorloop)
    for tab in ("items", "paden", "hosts", "dashboard", "uitdraai"):
        pagina.click(f"#tab-{tab}")
    kies(pagina, "1.1", "crown-jewels.csv")
    assert verzoeken == [], verzoeken

def test_filter_op_wie_levert_het(pagina, regels):
    """Filteren op wie de export levert: eerst wat je zelf kunt trekken.

    De telling is dezelfde als in test_regels.py, maar dan zoals hij op het scherm uitpakt; loopt de
    pagina uit de pas met de regels, dan valt een van beide om.
    """
    per_bron = {b["id"]: b["wie"] for b in regels["bronnen"]}
    for waarde, verwacht in (("zelf", 14), ("beheer", 23), ("afspraak", 4)):
        pagina.select_option("#filter-wie", waarde)
        pagina.wait_for_function(
            "(n) => document.querySelectorAll('[data-item]').length === n", arg=verwacht)
        getoond = pagina.eval_on_selector_all(
            "[data-item]", "n => n.map(e => e.getAttribute('data-item'))")
        for item_id in getoond:
            item = [i for i in regels["items"] if i["id"] == item_id][0]
            assert per_bron[item["bron"]] == waarde, item_id
    pagina.select_option("#filter-wie", "")
    pagina.wait_for_function("() => document.querySelectorAll('[data-item]').length === 41")
