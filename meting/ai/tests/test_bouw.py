"""De gebouwde AI-pagina: een bestand, een sleutel die nergens landt, en niets meer dan nodig."""
from __future__ import annotations

import base64
import hashlib
import json
import re
from conftest import AI, METING


def hash_van(inhoud: str) -> str:
    return base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()


def gebouwd(ai_bouw, tmp_path) -> str:
    return ai_bouw.bouw(tmp_path).read_text(encoding="utf-8")


def test_een_script_en_een_stijl_met_hun_hash(ai_bouw, tmp_path):
    """De hele belofte hangt aan die twee hashes: alleen dit script en deze stijl mogen draaien."""
    html = gebouwd(ai_bouw, tmp_path)
    assert html.count("<script>") == 1 and html.count("<style>") == 1
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    stijl = html.split("<style>", 1)[1].split("</style>", 1)[0]
    assert f"sha256-{hash_van(script)}" in html
    assert f"sha256-{hash_van(stijl)}" in html
    for rest in ("__CSS__", "__SCRIPT__", "__SCRIPT_HASH__", "__STYLE_HASH__", "__CONNECT_SRC__"):
        assert rest not in html, rest


def test_csp_laat_alleen_praten_met_een_leverancier(ai_bouw, tmp_path):
    """default-src none, en connect-src precies zo ruim als nodig: https en een lokale Ollama."""
    html = gebouwd(ai_bouw, tmp_path)
    csp = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in csp
    assert "connect-src https: http://localhost:* http://127.0.0.1:*" in csp
    assert "form-action 'none'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp


def test_geen_sleutel_en_geen_leverancier_ingebakken(ai_bouw, tmp_path):
    """Een sleutel hoort van de gebruiker te komen; een ingebakken sleutel zou hier zichtbaar zijn.

    Twee lange reeksen horen er wel te staan: het favicon als data-URI en de sha256-hashes in het CSP.
    Die tellen niet mee. Wat daarna nog lang is en letters met cijfers mengt, is verdacht.
    """
    html = gebouwd(ai_bouw, tmp_path)
    schoon = re.sub(r"data:[^\"']+", "", html)
    schoon = re.sub(r"sha256-[A-Za-z0-9+/=]+", "", schoon)
    # De vingerafdruk van de meetregels is 64 tekens hex; die hoort er ook te staan.
    schoon = re.sub(r"\b[0-9a-f]{64}\b", "", schoon)
    for verdacht in re.findall(r"\b[A-Za-z0-9]{24,}\b", schoon):
        assert not (any(c.isdigit() for c in verdacht) and any(c.isalpha() for c in verdacht)), \
            f"lijkt op een sleutel: {verdacht}"
    assert "Bearer ' + stand.sleutel" in html, "de sleutel komt uit het invoerveld"
    assert "localStorage.setItem('meting-ai-sleutel" not in html


def test_de_contracten_gaan_mee_maar_de_meetregels_niet(ai_bouw, tmp_path):
    """De pagina kent de kolommen, niet de drempels: het model hoort de meetregels niet te kennen."""
    html = gebouwd(ai_bouw, tmp_path)
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    bronnen = json.loads(re.search(r"window\.__BRONNEN__ = (\[.*?\]);\n", script, re.S).group(1))
    assert len(bronnen) == 20
    assert {"id", "titel", "kolommen", "optioneel", "uitleg", "items"} == set(bronnen[0])
    regels = json.loads((METING / "regels.json").read_text(encoding="utf-8"))
    drempel = [i for i in regels["items"] if i["id"] == "1.3"][0]["regel"]["parameters"]
    assert str(drempel["minimaal_pct_multi"]) + '"' not in script
    assert "verdicts" not in script and "toets_" not in script


def test_de_tool_vingerafdruk_gaat_mee(ai_bouw, tmp_path):
    """Een voorstel weet bij welke versie van de meetregels het hoort; anders wordt het stil oud."""
    html = gebouwd(ai_bouw, tmp_path)
    assert ai_bouw.vingerafdruk_tool() in html


def test_geen_externe_verwijzingen(ai_bouw, tmp_path):
    """Alles in een bestand: geen font, geen script, geen afbeelding van buiten."""
    html = gebouwd(ai_bouw, tmp_path)
    for verwijzing in re.findall(r'(?:src|href)="(https?://[^"]+)"', html):
        assert verwijzing.startswith("https://security-commons-nl.github.io/") or \
            verwijzing.startswith("https://github.com/security-commons-nl/"), verwijzing


def test_alleen_ai_js_praat_naar_buiten(ai_bouw, tmp_path):
    """kern.js gaat ook mee in de tool zelf; daar mag geen netwerk in zitten."""
    kern = (AI / "bron" / "kern.js").read_text(encoding="utf-8")
    assert "fetch(" not in kern
    ai = (AI / "bron" / "ai.js").read_text(encoding="utf-8")
    assert ai.count("fetch(") >= 2, "de aanroepen horen juist hier te staan"


def test_de_pagina_wijst_naar_de_uitleg(ai_bouw, tmp_path):
    """Wat BYOK inhoudt staat een keer, op de site; elke AI-pagina verwijst daarheen."""
    html = gebouwd(ai_bouw, tmp_path)
    assert "https://security-commons-nl.github.io/ai-hulp/" in html
