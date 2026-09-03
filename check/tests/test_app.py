"""De zelfcheck in een echte browser: klikken, opslaan, terugladen, en de uitslag.

Deze tests draaien de gebouwde HTML in Chromium. Ze bewijzen twee dingen die je met een unit-test
niet kunt bewijzen: dat de app werkt zoals een gebruiker hem gebruikt, en dat zijn beoordeling exact
gelijk is aan tools/score.py en aan de zelfcheck waar de bron uit komt.

Overslaan als Playwright of de browser ontbreekt; CI installeert beide.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
CHECK = HIER.parent
REPO = CHECK.parent
sys.path.insert(0, str(CHECK))
sys.path.insert(0, str(REPO))
import bouw  # noqa: E402
from tools import score  # noqa: E402

sync_api = pytest.importorskip("playwright.sync_api", reason="playwright niet beschikbaar")


@pytest.fixture(scope="module")
def bestand(tmp_path_factory) -> str:
    return bouw.bouw(tmp_path_factory.mktemp("dist")).as_uri()


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads((REPO / "paden.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:  # geen browser geinstalleerd
            pytest.skip(f"chromium niet beschikbaar: {e}")
        yield b
        b.close()


@pytest.fixture
def pagina(browser, bestand):
    context = browser.new_context()
    p = context.new_page()
    fouten = []
    p.on("pageerror", lambda e: fouten.append(str(e)))
    p.on("console", lambda m: fouten.append(m.text) if m.type == "error" else None)
    p.goto(bestand)
    yield p
    assert not fouten, f"fouten in de browser: {fouten}"
    context.close()


def alle_antwoorden(data: dict, antwoord: str, model: str) -> dict[str, str]:
    neg = {cp["vraag_id"] for b in data["bladeren"] for cp in b["chokepoints"] if cp.get("negatief")}
    ids = {cp["vraag_id"] for b in data["bladeren"] for cp in b["chokepoints"]}
    ids |= {rv["vraag_id"] for rv in data["randvoorwaarden"]}
    om = {"yes": "no", "no": "yes"}.get(antwoord, antwoord)
    a = {v: (om if v in neg else antwoord) for v in ids}
    a["model"] = model
    return a


def uitslag_in_browser(pagina, antwoorden: dict) -> dict:
    return pagina.evaluate(
        "a => { window.zelfcheck.zet(a); const u = window.zelfcheck.beoordeel();"
        " return {status: Object.fromEntries(Object.entries(u).map(([k, v]) => [k, v.status])),"
        " acties: window.zelfcheck.acties().map(x => x.vraag_id)}; }",
        antwoorden,
    )


# ---------- de app zoals een gebruiker hem gebruikt ----------

@pytest.fixture(scope="module")
def meting_export(data) -> dict:
    """Het echte exportbestand uit meting; zo bewijst deze test dat beide kanten op elkaar passen."""
    conftest_pad = REPO / "meting" / "tests" / "conftest.py"
    if not conftest_pad.exists():
        pytest.skip("meting staat niet in deze repo")
    import importlib.util
    spec = importlib.util.spec_from_file_location("meting_conftest", conftest_pad)
    mconf = importlib.util.module_from_spec(spec)
    sys.modules["meting_conftest"] = mconf
    spec.loader.exec_module(mconf)
    regels = json.loads((REPO / "meting" / "regels.json").read_text(encoding="utf-8"))
    dossier = mconf.doorloop_dossier(regels, data)
    return mconf.reken_module.zelfcheck_export(regels, data, dossier, mconf.PEILDATUM)


def laad_meting(pagina, tmp_path, inhoud: dict, naam: str = "uit-meting.json") -> None:
    doel = tmp_path / naam
    doel.write_text(json.dumps(inhoud, ensure_ascii=False), encoding="utf-8")
    pagina.set_input_files("#bestand-meting", str(doel))
    pagina.wait_for_selector("#meting-status")


def test_antwoorden_uit_meting_laden(pagina, data, meting_export, tmp_path):
    gemeten = {v: a for v, a in meting_export["antwoorden"].items() if a != "unknown"}
    assert gemeten, "de doorloop hoort ten minste een vraag te beantwoorden"
    eerste = sorted(gemeten)[0]

    # Een eigen antwoord op de eerste vraag blijft staan; de rest wordt gevuld.
    eigen = "no" if gemeten[eerste] == "yes" else "yes"
    pagina.evaluate("a => window.zelfcheck.zet(a)", {eerste: eigen})
    laad_meting(pagina, tmp_path, meting_export)

    melding = pagina.text_content("#meting-status")
    assert f"{len(gemeten) - 1} antwoorden overgenomen" in melding
    assert "1 overgeslagen (al ingevuld)" in melding
    bewaard = json.loads(pagina.evaluate("() => localStorage.getItem('aanvalspaden-zelfcheck-v1')"))
    assert bewaard["antwoorden"][eerste] == eigen, "een eigen antwoord mag niet overschreven worden"
    for vraag, antwoord in gemeten.items():
        if vraag != eerste:
            assert bewaard["antwoorden"][vraag] == antwoord, vraag
    for vraag, antwoord in meting_export["antwoorden"].items():
        if antwoord == "unknown":
            assert vraag not in bewaard["antwoorden"], f"{vraag}: onbekend hoort niets te vullen"

    # De herkomst staat als notitie bij de vraag, zodat zichtbaar is waar het antwoord vandaan komt.
    tweede = sorted(v for v in gemeten if v != eerste)[0]
    notitie = bewaard["notities"][tweede]
    assert notitie.startswith("uit meting 2026-09-03")
    for item in meting_export["herkomst"].get(tweede, {}).get("items", []):
        assert item in notitie
    pagina.evaluate("() => window.zelfcheck.ga('vragen', 0)")
    zichtbaar = pagina.locator(".notitie").all_inner_texts()
    assert any(t.startswith("uit meting") for t in zichtbaar)


def test_laden_weigert_een_ander_bestand(pagina, tmp_path, meting_export):
    laad_meting(pagina, tmp_path, {"formaat": "meting-dossier", "metingen": {}})
    assert "geen exportbestand van de meting" in pagina.text_content("#meting-status")
    assert pagina.evaluate("() => localStorage.getItem('aanvalspaden-zelfcheck-v1')") is None


def test_startscherm_toont_de_check(pagina, data):
    assert "aanvalspaden" in pagina.title().lower()
    assert pagina.get_by_role("heading", name="Welke aanvalspaden staan bij jullie open?").is_visible()
    assert str(len(data["bladeren"])) in pagina.locator("main").inner_text()


def test_doorklikken_langs_alle_onderdelen_en_terug(pagina, data):
    pagina.get_by_role("button", name="Start de check").click()
    for n, onderdeel in enumerate(data["onderdelen"]):
        assert pagina.get_by_role("heading", name=onderdeel["titel"]).is_visible()
        naam = "Naar het resultaat" if n == len(data["onderdelen"]) - 1 else "Volgende onderdeel"
        pagina.get_by_role("button", name=naam).click()
    assert pagina.locator("#open-paden").is_visible()
    pagina.get_by_role("button", name="Terug naar de vragen").click()
    assert pagina.get_by_role("heading", name=data["onderdelen"][0]["titel"]).is_visible()


def test_antwoord_klikken_bewaart_en_overleeft_herladen(pagina, data):
    pagina.get_by_role("button", name="Start de check").click()
    eerste = data["onderdelen"][0]["vragen"][0]
    knop = pagina.locator(f'#vraag-{eerste} button[data-antwoord="yes"]')
    knop.click()
    assert knop.get_attribute("aria-checked") == "true"
    pagina.reload()
    pagina.get_by_role("button", name="Verder met je check").click()
    assert pagina.locator(f'#vraag-{eerste} button[data-antwoord="yes"]').get_attribute("aria-checked") == "true"
    assert "1 van de" in pagina.locator("main").inner_text()


def test_wissen_leegt_de_opslag(pagina, data):
    pagina.evaluate("a => window.zelfcheck.zet(a)", alle_antwoorden(data, "yes", "dedicated"))
    pagina.evaluate("() => window.zelfcheck.ga('resultaat')")
    pagina.once("dialog", lambda d: d.accept())
    pagina.get_by_role("button", name="Wis alle antwoorden").click()
    assert pagina.evaluate("() => localStorage.getItem('aanvalspaden-zelfcheck-v1')") is None
    assert pagina.get_by_role("button", name="Start de check").is_visible()


def test_vervolgvraag_verdwijnt_als_de_voorwaarde_nee_is(pagina, data):
    # restore hoort alleen gesteld te worden als backup niet nee is
    pagina.evaluate("() => window.zelfcheck.zet({backup: 'no'})")
    pagina.evaluate("() => window.zelfcheck.ga('vragen', 5)")
    assert pagina.locator("#vraag-backup").count() == 1
    assert pagina.locator("#vraag-restore").count() == 0
    pagina.evaluate("() => window.zelfcheck.zet({backup: 'yes'})")
    pagina.evaluate("() => window.zelfcheck.ga('vragen', 5)")
    assert pagina.locator("#vraag-restore").count() == 1


# ---------- de drie doorlopen ----------

def test_alles_ja_geeft_geen_open_paden(pagina, data):
    uit = uitslag_in_browser(pagina, alle_antwoorden(data, "yes", "dedicated"))
    assert "open" not in uit["status"].values()
    assert uit["acties"] == []
    pagina.evaluate("() => window.zelfcheck.ga('resultaat')")
    assert pagina.locator('[data-status="open"]').count() == 0


def test_alles_nee_geeft_alleen_open_paden(pagina, data):
    uit = uitslag_in_browser(pagina, alle_antwoorden(data, "no", "permanent"))
    assert set(uit["status"].values()) == {"open"}
    assert len(uit["acties"]) == data["regels"]["acties"]["aantal"]
    pagina.evaluate("() => window.zelfcheck.ga('resultaat')")
    assert pagina.locator('.pad[data-status="open"]').count() >= len(data["bladeren"])


def test_alles_onbekend_geeft_overal_onbekend(pagina, data):
    uit = uitslag_in_browser(pagina, alle_antwoorden(data, "unknown", "unknown"))
    assert set(uit["status"].values()) == {"unknown"}


# ---------- gelijk aan de referentie en aan de zelfcheck ----------

@pytest.mark.parametrize("antwoord,model", [("yes", "dedicated"), ("no", "permanent"),
                                            ("unknown", "unknown"), ("partial", "separate")])
def test_browser_en_referentie_geven_hetzelfde(pagina, data, antwoord, model):
    antwoorden = alle_antwoorden(data, antwoord, model)
    in_browser = uitslag_in_browser(pagina, antwoorden)
    in_python = score.beoordeel(data, antwoorden)
    verschil = {p: (in_browser["status"][p], in_python[p]["status"])
                for p in in_python if in_browser["status"][p] != in_python[p]["status"]}
    assert not verschil, f"(browser, referentie): {verschil}"
    assert in_browser["acties"] == [a["vraag_id"] for a in score.acties(data, antwoorden, in_python)]


def test_browser_geeft_dezelfde_uitslag_als_de_oorspronkelijke_zelfcheck(pagina, data):
    fx = json.loads((REPO / "tests" / "fixtures" / "doorloop-2026-08-28.json").read_text(encoding="utf-8"))
    in_browser = uitslag_in_browser(pagina, fx["antwoorden"])
    verschil = {p: (in_browser["status"][p], s) for p, s in fx["status_volgens_app"].items()
                if in_browser["status"][p] != s}
    assert not verschil, f"(nieuwe app, oorspronkelijke zelfcheck): {verschil}"
    assert in_browser["acties"] == fx["acties_volgens_app"]


def test_resultaatscherm_toont_paden_acties_en_statussen(pagina, data):
    fx = json.loads((REPO / "tests" / "fixtures" / "doorloop-2026-08-28.json").read_text(encoding="utf-8"))
    pagina.evaluate("a => window.zelfcheck.zet(a)", fx["antwoorden"])
    pagina.evaluate("() => window.zelfcheck.ga('resultaat')")
    tekst = pagina.locator("main").inner_text()
    assert "Als je morgen maar drie dingen kunt doen" in tekst
    assert pagina.locator(".actie").count() == 3
    for pad, status in fx["status_volgens_app"].items():
        kaart = pagina.locator(f'.pad[data-pad="{pad}"]').first
        assert kaart.get_attribute("data-status") == status, pad
    assert "Verder met de risicoanalyse" in tekst
