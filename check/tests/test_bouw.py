"""De gebouwde zelfcheck: zelfstandig, offline en volledig uit de bron."""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import re
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
CHECK = HIER.parent
REPO = CHECK.parent
sys.path.insert(0, str(CHECK))
import bouw  # noqa: E402


@pytest.fixture(scope="module")
def html(tmp_path_factory) -> str:
    return bouw.bouw(tmp_path_factory.mktemp("dist")).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads((REPO / "paden.json").read_text(encoding="utf-8"))


def ingebakken(html: str) -> dict:
    return json.loads(re.search(r"window\.__BRON__ = (\{.*?\});\n", html, re.S).group(1).replace("<\\/", "</"))


def test_alle_vragen_staan_in_de_pagina(html, data):
    claims = {cp["vraag"]["claim"] for b in data["bladeren"] for cp in b["chokepoints"]}
    claims |= {rv["vraag"]["claim"] for rv in data["randvoorwaarden"]}
    assert len(claims) == 44
    embedded = ingebakken(html)
    # Het handelingsperspectief komt uit de kennisbank en staat naast paden.json in de bron; de rest
    # moet er ongewijzigd in zitten, want paden.json is de enige bron voor de paden zelf.
    handelingsperspectief = embedded.pop("handelingsperspectief", None)
    assert embedded == data, "de meegebakken bron wijkt af van paden.json"
    assert handelingsperspectief is not None, "het handelingsperspectief hoort mee te gaan"


def test_de_uitslag_kan_naar_de_handleiding_wijzen(html, data):
    """Zonder deze koppeling zegt de uitslag wat je moet doen, maar niet hoe.

    De handleidingen staan in de kennisbank en hangen aan dezelfde vraag_id. Ze hier inbakken is de
    enige manier om ze te tonen zonder de offlinebelofte te breken.
    """
    hp = ingebakken(html)["handelingsperspectief"]
    barrieres = {cp["vraag_id"] for b in data["bladeren"] for cp in b["chokepoints"]}
    barrieres |= {rv["vraag_id"] for rv in data["randvoorwaarden"]}

    onbekend = sorted(set(hp) - barrieres)
    assert not onbekend, f"handleidingen bij barrieres die niet in paden.json staan: {onbekend}"
    assert len(hp) >= 30, f"maar {len(hp)} barrieres met een handleiding; loopt de kopie achter?"

    for barriere, lijst in hp.items():
        assert lijst, f"{barriere}: lege lijst hoort er niet in te staan"
        for h in lijst:
            assert set(h) == {"titel", "rol", "url"}, f"{barriere}: onverwacht veld in {h}"
            assert h["rol"] in ("fundering", "alternatief", "verdieping"), f"{barriere}: rol {h['rol']}"
            assert h["url"].startswith("https://security-commons-nl.github.io/kennisbank/")
        funderingen = [h for h in lijst if h["rol"] == "fundering"]
        assert len(funderingen) <= 1, f"{barriere}: twee startpunten, dan weet de lezer niet waar te beginnen"


def test_geen_enkele_externe_verwijzing(html):
    """Offline betekent: niets dat de pagina zelf van buiten haalt."""
    for tag in re.findall(r"<(?:script|link|img|iframe|source|video|audio|object|embed)\b[^>]*>", html, re.I):
        assert not re.search(r'\b(?:src|href)\s*=\s*["\']https?:', tag, re.I), tag
    assert "@import" not in html
    assert not re.search(r"url\(\s*['\"]?https?:", html, re.I)
    # Gewone tekstlinks naar de repo en de kennisbank mogen wel; die laadt de pagina niet zelf.


def test_csp_sluit_alles_af_en_klopt_met_de_inhoud(html):
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in csp
    assert "form-action 'none'" in csp and "base-uri 'none'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp

    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    for inhoud, soort in ((script, "script-src"), (style, "style-src")):
        h = base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()
        assert f"{soort} 'sha256-{h}'" in csp, f"{soort} hash klopt niet met de inhoud"


def test_precies_een_script_en_een_stylesheet(html):
    assert len(re.findall(r"<script\b", html)) == 1
    assert len(re.findall(r"<style\b", html)) == 1


def test_de_app_bevat_geen_eigen_kopie_van_de_vragen(data):
    """De regels en vragen horen uit de bron te komen, niet in de code te staan."""
    js = (CHECK / "bron" / "app.js").read_text(encoding="utf-8")
    for blad in data["bladeren"]:
        if blad["id"] not in ("AP05", "AP17"):  # die twee hebben een uitzondering in de regels
            assert blad["id"] not in js, f"{blad['id']} staat hardgecodeerd in app.js"
    for cp in (cp for b in data["bladeren"] for cp in b["chokepoints"]):
        assert cp["vraag"]["claim"] not in js


def test_pagina_werkt_zonder_javascript_uitleg(html):
    assert "<noscript>" in html
    assert "paden.json" in html


def test_bouw_is_herhaalbaar(tmp_path):
    een = bouw.bouw(tmp_path / "a").read_bytes()
    twee = bouw.bouw(tmp_path / "b").read_bytes()
    assert een == twee


def test_kruimelpad_wijst_terug_naar_de_hoofdpagina(html):
    """Statuut B10: elke pagina op Pages begint met een weg terug."""
    assert 'class="kruimel"' in html
    assert 'href="https://security-commons-nl.github.io/"' in html
    assert "Security Commons NL" in html
