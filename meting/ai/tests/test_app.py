"""De AI-pagina in een echte browser, met de leverancier nagespeeld: geen sleutel, geen netwerk.

Elke test onderschept /v1/models en /v1/chat/completions met page.route en geeft het vastgelegde
antwoord terug. Een aanroep die niet onderschept wordt, loopt tegen het CSP aan en geeft een
consolefout; daar valt de test op om.

De laatste test is de belangrijkste: hij loopt de hele weg af, van export naar voorstel naar meting.
Dat is de enige plek waar bewezen wordt dat de omzetting van de AI-pagina daadwerkelijk door dezelfde
toets gaat als een gewoon bestand, en dat de meting daarna zichtbaar draagt dat de invoer met AI is
omgezet.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from conftest import FIXTURES, METING

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright niet beschikbaar")

BASIS = "https://api.mistral.ai"
PEILDATUM = "2026-09-03"


@pytest.fixture(scope="module")
def bestand(ai_bouw, tmp_path_factory) -> str:
    return ai_bouw.bouw(tmp_path_factory.mktemp("ai-dist")).as_uri()


@pytest.fixture(scope="module")
def tool_bestand(tool_bouw, tmp_path_factory) -> str:
    return tool_bouw.bouw(tmp_path_factory.mktemp("meting-dist")).as_uri()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as pw:
        try:
            gestart = pw.chromium.launch()
        except Exception as fout:
            pytest.skip(f"chromium niet beschikbaar: {fout}")
        yield gestart
        gestart.close()


def nieuw_blad(browser, adres):
    context = browser.new_context()
    blad = context.new_page()
    fouten: list[str] = []
    blad.on("pageerror", lambda e: fouten.append(str(e)))
    blad.on("console", lambda m: fouten.append(m.text)
            if m.type == "error" and not m.text.startswith("Failed to load resource: the server responded")
            else None)
    blad.goto(adres)
    blad.evaluate("() => { window.localStorage.clear(); window.sessionStorage.clear(); }")
    blad.reload()
    return blad, fouten, context


@pytest.fixture
def pagina(browser, bestand):
    blad, fouten, context = nieuw_blad(browser, bestand)
    yield blad
    assert not fouten, f"fouten in de browser: {fouten}"
    context.close()


class Leverancier:
    """Speelt de endpoint na en telt de aanroepen."""

    def __init__(self, blad, antwoorden):
        self.aanroepen: list[dict] = []
        self.antwoorden = list(antwoorden)
        blad.route(f"{BASIS}/v1/models", lambda route: route.fulfill(
            status=200, content_type="application/json", body='{"data": []}'))
        blad.route(f"{BASIS}/v1/chat/completions", self._chat)

    def _chat(self, route):
        verzoek = route.request
        self.aanroepen.append({"headers": verzoek.headers, "body": json.loads(verzoek.post_data)})
        volgende = self.antwoorden.pop(0) if self.antwoorden else {"items": [], "onzeker": []}
        if isinstance(volgende, int):
            route.fulfill(status=volgende, content_type="application/json", body='{"message": "nee"}')
            return
        inhoud = volgende if isinstance(volgende, str) else json.dumps(volgende, ensure_ascii=False)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"choices": [{"message": {"role": "assistant", "content": inhoud}}]}))


def verbind(blad, sleutel="test-sleutel"):
    blad.fill("#lev-sleutel", sleutel)
    blad.click("#knop-verbinding")
    blad.wait_for_selector("#lev-status.status-ok")


def kies(blad, bron="crown_jewels_csv", tekst=None):
    blad.select_option("#opdracht-keuze", "contract")
    blad.select_option("#bron-keuze", bron)
    blad.fill("#invoer-tekst", tekst if tekst is not None else "")
    blad.check("#toestemming")


def actief(blad, stap: str) -> bool:
    return blad.get_attribute(f"#stap-{stap}", "data-actief") == "ja"


# ---------------------------------------------------------------- de stappen

def test_start_zonder_sleutel(pagina):
    assert actief(pagina, "leverancier")
    for stap in ("opdracht", "invoer", "toestemming", "uitvoeren", "voorstel", "verder"):
        assert not actief(pagina, stap), stap
    assert pagina.is_disabled("#knop-verbinding")


def test_de_contracten_staan_in_de_lijst(pagina, regels):
    """De keuzelijst komt uit regels.json: alleen tabelcontracten, met hun meetregels erbij."""
    opties = pagina.eval_on_selector_all(
        "#bron-keuze option", "n => n.map(o => o.value).filter(v => v)")
    csv_bronnen = {b["id"] for b in regels["bronnen"] if b["formaat"] == "csv"}
    assert set(opties) == csv_bronnen
    tekst = pagina.text_content("#bron-keuze")
    assert "1.1" in tekst and "Kroonjuwelenlijst" in tekst


def test_zonder_bron_geen_invoer(pagina):
    """Zonder contract weet de pagina de kolommen niet; dan valt er niets om te zetten."""
    Leverancier(pagina, [])          # zonder deze stub loopt de verbindingstest tegen het CSP aan
    verbind(pagina)
    pagina.select_option("#opdracht-keuze", "contract")
    assert not actief(pagina, "invoer"), "de invoerstap hoort dicht te blijven"
    pagina.select_option("#bron-keuze", "crown_jewels_csv")
    assert actief(pagina, "invoer")
    assert "name" in pagina.text_content("#bron-uitleg")


def test_de_prompt_draagt_de_kolommen_en_niet_de_meetregels(pagina, invoer, antwoord, regels):
    """Het model krijgt het contract, niet de drempels: beoordelen doet de tool."""
    leverancier = Leverancier(pagina, [antwoord])
    verbind(pagina)
    kies(pagina, tekst=invoer)
    pagina.click("#knop-uitvoeren")
    pagina.wait_for_selector("#stap-voorstel[data-actief='ja']")

    systeem = leverancier.aanroepen[0]["body"]["messages"][0]["content"]
    for kolom in ("name", "owner", "vlan_or_subnet", "backup_type", "rto", "rpo"):
        assert kolom in systeem, kolom
    assert "crown_jewels_csv" in systeem
    assert "beoordeel niets" in systeem.lower()
    assert "minimaal_pct_multi" not in systeem and "verdict" not in systeem.lower()
    schema = leverancier.aanroepen[0]["body"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["items"]["items"]["additionalProperties"] is False
    assert set(schema["properties"]["items"]["items"]["properties"]) == {
        "name", "owner", "vlan_or_subnet", "backup_type", "rto", "rpo", "bronregel"}


def test_voorstel_en_citaatcontrole(pagina, invoer, antwoord):
    """Elke rij draagt een citaat; wat niet woordelijk in de invoer staat, wordt gemarkeerd."""
    verzonnen = json.loads(json.dumps(antwoord))
    verzonnen["items"][2]["bronregel"] = "| Verzonnen systeem | Niemand | VLAN 99 | geen | 1 uur | 1 uur |"
    Leverancier(pagina, [verzonnen])
    verbind(pagina)
    kies(pagina, tekst=invoer)
    pagina.click("#knop-uitvoeren")
    pagina.wait_for_selector("#stap-voorstel[data-actief='ja']")

    assert pagina.locator("#tabel-voorstel tbody tr").count() == 3
    assert pagina.locator("#tabel-voorstel tr.niet-in-bron").count() == 1
    assert "niet in de bron" in pagina.text_content("#voorstel-samenvatting")
    onzeker = pagina.text_content("#onzeker")
    assert "Office 365" in onzeker, "wat het model oversloeg, hoort zichtbaar te zijn"


def test_de_sleutel_gaat_mee_maar_landt_nergens(pagina, invoer, antwoord):
    leverancier = Leverancier(pagina, [antwoord])
    verbind(pagina, "geheime-sleutel")
    kies(pagina, tekst=invoer)
    pagina.click("#knop-uitvoeren")
    pagina.wait_for_selector("#stap-voorstel[data-actief='ja']")

    assert leverancier.aanroepen[0]["headers"]["authorization"] == "Bearer geheime-sleutel"
    opslag = pagina.evaluate("() => JSON.stringify(window.localStorage)")
    assert "geheime-sleutel" not in opslag
    voorstel = pagina.evaluate("() => JSON.stringify(window.__laatsteVoorstel__ || '')")
    assert "geheime-sleutel" not in voorstel


def test_van_export_naar_meting(browser, bestand, tool_bestand, invoer, antwoord, tmp_path):
    """De hele weg: omzetten op de AI-pagina, laden in de meting, en daar pas toetsen.

    Dit is de kern van het ontwerp. De AI schrijft niet in het dossier; de tool toetst de omgezette
    tabel met dezelfde regels als een gekozen bestand, en noteert dat de invoer met AI is omgezet.
    """
    blad, fouten, context = nieuw_blad(browser, bestand)
    Leverancier(blad, [antwoord])
    verbind(blad)
    kies(blad, tekst=invoer)
    blad.click("#knop-uitvoeren")
    blad.wait_for_selector("#stap-voorstel[data-actief='ja']")
    with blad.expect_download() as download:
        blad.click("#knop-voorstel-opslaan")
    doel = tmp_path / download.value.suggested_filename
    download.value.save_as(str(doel))
    assert not fouten, f"fouten op de AI-pagina: {fouten}"
    context.close()

    voorstel = json.loads(doel.read_text(encoding="utf-8"))
    assert voorstel["formaat"] == "meting-voorstel" and voorstel["tool"] == "meting"
    assert voorstel["bron"] == "crown_jewels_csv"
    assert len(voorstel["items"]) == 3
    assert all(rij["bronregel_klopt"] for rij in voorstel["items"])
    assert "invoer" in voorstel and "sha256" in voorstel["invoer"]
    assert invoer[:40] not in doel.read_text(encoding="utf-8"), "de invoer zelf hoort er niet in"

    tool, toolfouten, toolcontext = nieuw_blad(browser, tool_bestand)
    tool.fill("#org-peildatum", PEILDATUM)
    tool.dispatch_event("#org-peildatum", "change")
    tool.set_input_files("#bestand-voorstel", str(doel))
    tool.wait_for_selector("#voorstel-blok:not([hidden])")
    assert "Kroonjuwelenlijst" in tool.text_content("#voorstel-kop")
    assert tool.locator("#tabel-voorstel tbody tr").count() == 3

    tool.click("#knop-voorstel-overnemen")
    tool.wait_for_selector('[data-item="1.1"] .verdict.v-pass')
    dossier = json.loads(tool.evaluate("() => window.localStorage.getItem('aanvalspaden-meting-v1')"))
    for item_id in ("1.1", "1.2"):
        meting = dossier["metingen"][item_id]
        assert meting["verdict"] == "pass", item_id
        assert meting["bestand"].startswith("AI-voorstel"), item_id
        assert meting["herkomst_ai"]["leverancier"] == "mistral"
        assert meting["herkomst_ai"]["rijen"] == 3
        assert meting["herkomst_ai"]["invoer_sha256"] == voorstel["invoer"]["sha256"]

    tool.click("#tab-uitdraai")
    assert "omgezet met AI" in tool.text_content("#uitdraai-inhoud")
    assert not toolfouten, f"fouten in de meting: {toolfouten}"
    toolcontext.close()


def test_een_rij_zonder_citaat_wordt_niet_gemeten(browser, bestand, tool_bestand, invoer, antwoord,
                                                  tmp_path):
    """Een verzonnen rij haalt de citaatcontrole niet en gaat niet mee in de toets."""
    verzonnen = json.loads(json.dumps(antwoord))
    verzonnen["items"][2]["name"] = "Verzonnen systeem"
    verzonnen["items"][2]["bronregel"] = "| Verzonnen systeem | Niemand | VLAN 99 | geen | 1 uur | 1 uur |"
    blad, fouten, context = nieuw_blad(browser, bestand)
    Leverancier(blad, [verzonnen])
    verbind(blad)
    kies(blad, tekst=invoer)
    blad.click("#knop-uitvoeren")
    blad.wait_for_selector("#stap-voorstel[data-actief='ja']")
    with blad.expect_download() as download:
        blad.click("#knop-voorstel-opslaan")
    doel = tmp_path / "voorstel-met-verzinsel.json"
    download.value.save_as(str(doel))
    context.close()

    tool, toolfouten, toolcontext = nieuw_blad(browser, tool_bestand)
    tool.fill("#org-peildatum", PEILDATUM)
    tool.dispatch_event("#org-peildatum", "change")
    tool.set_input_files("#bestand-voorstel", str(doel))
    tool.wait_for_selector("#voorstel-blok:not([hidden])")
    assert "niet woordelijk in je invoer" in tool.text_content("#voorstel-afgekeurd")
    tool.click("#knop-voorstel-overnemen")
    tool.wait_for_selector('[data-item="1.1"] .bestand:not(:empty)')
    assert "AI-voorstel" in tool.text_content('[data-item="1.1"] .bestand')


def test_voorstel_van_een_andere_tool_wordt_geweigerd(browser, tool_bestand, tmp_path):
    verkeerd = tmp_path / "ander.json"
    verkeerd.write_text(json.dumps({"formaat": "procescheck-voorstel", "tool": "procescheck"}),
                        encoding="utf-8")
    tool, fouten, context = nieuw_blad(browser, tool_bestand)
    tool.set_input_files("#bestand-voorstel", str(verkeerd))
    tool.wait_for_selector("#dossier-status.let-op")
    assert "geen voorstel van de AI-hulp van de meting" in tool.text_content("#dossier-status")
    assert tool.is_hidden("#voorstel-blok")
    assert not fouten
    context.close()
