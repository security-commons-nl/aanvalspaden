"""De gebouwde crosswalk: zelfstandig, offline en volledig uit de bron."""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import re
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
MAP = HIER.parent
REPO = MAP.parent
sys.path.insert(0, str(REPO))
# conftest.py laadt mappingen/bouw.py onder deze naam; check/ heeft ook een bouw.py.
import crosswalk_bouw as bouw  # noqa: E402

from tools import mappingen as helper  # noqa: E402


@pytest.fixture(scope="module")
def html(tmp_path_factory) -> str:
    return bouw.bouw(tmp_path_factory.mktemp("dist")).read_text(encoding="utf-8")


def test_geen_enkele_externe_verwijzing(html):
    """De belofte is dat de pagina niets van buiten haalt. Dat toetsen we, we beloven het niet."""
    verdacht = re.findall(r'(?:src|href)\s*=\s*"(?!data:|#)([^"]+)"', html)
    extern = [v for v in verdacht if v.startswith(("http://", "https://", "//"))]
    # Links in de tekst naar de eigen site en repo mogen; het gaat om laadbare bronnen.
    laadbaar = re.findall(r'<(?:script|link|img)[^>]*(?:src|href)\s*=\s*"(https?:)?//[^"]+"', html)
    assert not laadbaar, f"de pagina laadt iets van buiten: {laadbaar}"
    assert all("security-commons-nl" in v or v.startswith("data:") for v in extern), extern


def test_csp_hashes_kloppen(html):
    """Het Content-Security-Policy staat op de hash van het echte script en de echte stylesheet."""
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)

    def hash_van(inhoud: str) -> str:
        return base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()

    csp = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in csp
    assert f"'sha256-{hash_van(script)}'" in csp, "de script-hash in het CSP klopt niet"
    assert f"'sha256-{hash_van(style)}'" in csp, "de style-hash in het CSP klopt niet"


def test_alle_kaders_staan_in_de_pagina(html):
    data = json.loads(re.search(r"window\.__MAPPINGEN__ = (\{.*?\});\n", html, re.S).group(1))
    assert set(data) == set(helper.kaders())


def test_alle_maatregelen_en_barrieres_staan_erin(html):
    data = json.loads(re.search(r"window\.__MAPPINGEN__ = (\{.*?\});\n", html, re.S).group(1))
    for kader in helper.kaders():
        ids = {m["id"] for m in data[kader]["maatregelen"]}
        assert ids == {m["id"] for m in helper.maatregelen(kader)}, f"{kader}: maatregelen ontbreken"
        assert set(data[kader]["barrieres"]) == set(helper.barrieres()), f"{kader}: barrieres ontbreken"


def test_de_tellingen_in_de_pagina_komen_uit_de_bron(html):
    data = json.loads(re.search(r"window\.__MAPPINGEN__ = (\{.*?\});\n", html, re.S).group(1))
    for kader in helper.kaders():
        assert data[kader]["dekking"] == helper.dekking(kader)


def test_elk_chokepoint_draagt_de_regels_van_zijn_barriere(html):
    """De pagina rekent vooraf uit; die uitkomst moet gelijk zijn aan de bron."""
    data = json.loads(re.search(r"window\.__MAPPINGEN__ = (\{.*?\});\n", html, re.S).group(1))
    for kader in helper.kaders():
        for blad in data[kader]["bladeren"]:
            for cp in blad["chokepoints"]:
                verwacht = helper.regels_van_barriere(kader, cp["barriere"])
                assert len(cp["regels"]) == len(verwacht), f"{kader}/{cp['id']}: aantal regels wijkt af"
                assert {r["norm"] for r in cp["regels"]} == {r["norm"] for r in verwacht}


def test_witte_vlekken_zijn_compleet(html):
    data = json.loads(re.search(r"window\.__MAPPINGEN__ = (\{.*?\});\n", html, re.S).group(1))
    for kader in helper.kaders():
        ids = {m["id"] for m in data[kader]["witteVlekken"]}
        assert ids == {m["id"] for m in helper.witte_vlekken(kader)}


def test_de_pagina_belooft_geen_compliance(html):
    """Wat op het scherm staat mag nooit suggereren dat je ergens aan voldoet."""
    zichtbaar = re.sub(r"<[^>]+>", " ", html)
    for zin in ("voldoet aan de BIO", "compliant met", "aantoonbaar voldaan"):
        assert zin.lower() not in zichtbaar.lower(), f"de pagina belooft compliance: {zin}"
    assert "levert bewijs" in html, "de kern van de belofte hoort op de pagina te staan"


def test_pagina_is_niet_onredelijk_groot(html):
    kb = len(html.encode("utf-8")) / 1024
    assert kb < 600, f"de pagina is {kb:.0f} kB; dat is te zwaar voor een offline bestand"
