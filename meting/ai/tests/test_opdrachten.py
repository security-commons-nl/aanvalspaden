"""opdrachten.json en de contracten die eruit de pagina in gaan.

De prompts en het schema zijn data, geen code: wie een drempel of een kolom verandert, doet dat hier en
niet in JavaScript. Deze tests bewaken dat die data klopt met de meetregels waar ze over gaat.
"""
from __future__ import annotations

import json
import pytest

from conftest import AI, kern_bron


def test_kop(opdrachten):
    assert opdrachten["tool"] == "meting"
    assert opdrachten["voorstel_formaat"] == "meting-voorstel"
    assert opdrachten["versie"] == "2026-09"
    assert opdrachten["grenzen"]["max_tekens_per_aanroep"] == 24000


def test_leveranciers(opdrachten):
    """Mistral als advies, een lokaal model als het mag niets kosten, en een vrij veld."""
    ids = [lev["id"] for lev in opdrachten["leveranciers"]]
    assert ids == ["mistral", "ollama", "anders"]
    for lev in opdrachten["leveranciers"]:
        assert lev["uitleg"].strip(), lev["id"]
    lokaal = [lev for lev in opdrachten["leveranciers"] if lev["id"] == "ollama"][0]
    assert lokaal["basis"].startswith("http://localhost")


def test_de_opdracht(opdrachten):
    assert len(opdrachten["opdrachten"]) == 1, "een opdracht: een export omzetten naar een contract"
    opdracht = opdrachten["opdrachten"][0]
    assert opdracht["id"] == "contract"
    assert opdracht["doelkeuze"] == "bron", "zonder bronkeuze weet de pagina niet welke kolommen"
    assert "schema" not in opdracht, "het schema komt uit de gekozen bron, niet uit dit bestand"
    for veld in ("titel", "uitleg", "invoer", "systeemprompt", "voorbeeld"):
        assert opdracht[veld], veld


def test_de_vaste_regels_verbieden_oordelen(opdrachten):
    """Het model zet kolommen om. Beoordelen doet de meting, en dat moet in de prompt staan."""
    regels = opdrachten["vaste_regels"].lower()
    for eis in ("verzin niets", "woordelijk", "bronregel", "beoordeel niets", "onzeker"):
        assert eis in regels, eis


def test_alleen_tabelcontracten_gaan_mee(ai_bouw, regels):
    """Een XML-config of een geplakt rapport laat je niet door een model herschrijven.

    Dan toets je de tekst van het model in plaats van je eigen export. Alleen csv-contracten komen in
    de keuzelijst; de andere formaten kiest de gebruiker als bestand, zoals altijd.
    """
    bronnen = ai_bouw.bronnen_voor_de_pagina()
    csv_bronnen = {b["id"] for b in regels["bronnen"] if b["formaat"] == "csv"}
    assert {b["id"] for b in bronnen} == csv_bronnen
    assert len(bronnen) == 20
    for verboden in ("document", "iamscan_dump", "nmap_xml", "wdac_policy_xml", "siem_rules_json"):
        assert verboden not in {b["id"] for b in bronnen}, verboden


def test_elke_bron_draagt_zijn_contract(ai_bouw, regels):
    """De pagina bouwt schema en prompt uit deze velden; ontbreekt er een, dan verzint het model."""
    per_bron = {b["id"]: b for b in regels["bronnen"]}
    for bron in ai_bouw.bronnen_voor_de_pagina():
        origineel = per_bron[bron["id"]]
        assert bron["kolommen"] == origineel["kolommen"]
        assert bron["optioneel"] == origineel["optioneel"]
        assert bron["uitleg"] == origineel["uitleg"]
        assert bron["items"], f"{bron['id']} meet niets"
        for item_id in bron["items"]:
            item = [i for i in regels["items"] if i["id"] == item_id][0]
            assert bron["id"] in (item["bron"], item.get("bron_alternatief"))


def test_het_voorbeeld_klopt_met_de_fixtures(opdrachten, antwoord, invoer, regels):
    """Het voorbeeld in opdrachten.json wijst naar bestanden die er zijn en bij elkaar passen."""
    voorbeeld = opdrachten["opdrachten"][0]["voorbeeld"]
    bron = [b for b in regels["bronnen"] if b["id"] == voorbeeld["bron"]][0]
    velden = set(bron["kolommen"]) | set(bron["optioneel"]) | {"bronregel"}
    assert antwoord["items"], "het vastgelegde antwoord is leeg"
    for rij in antwoord["items"]:
        assert set(rij) == velden, rij
        assert rij["bronregel"] in invoer, "het citaat staat niet woordelijk in de voorbeeldinvoer"


def test_kern_is_gelijk_aan_procescheck():
    """De kern is een kopie: dezelfde citaatcontrole in elke tool, of geen van beide."""
    bron = kern_bron()
    if bron is None:
        pytest.skip("procescheck staat niet als buurmap; de vergelijking is overgeslagen")
    kopie = (AI / "bron" / "kern.js").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert kopie == bron.read_text(encoding="utf-8").replace("\r\n", "\n"), \
        "kern.js loopt uit de pas; draai python meting/ai/haal_kern.py"
