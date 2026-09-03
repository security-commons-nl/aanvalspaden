"""De gebouwde pagina: zelfstandig, offline, en zonder tweede kopie van de meetregels."""
from __future__ import annotations

import base64
import hashlib
import json
import re

from conftest import METING, REPO


def hash_van(inhoud: str) -> str:
    return base64.b64encode(hashlib.sha256(inhoud.encode("utf-8")).digest()).decode()


def test_meetregels_staan_in_de_pagina(html, regels):
    assert "window.__BRON__ = " in html
    for item in regels["items"]:
        assert item["label"] in html, f"{item['id']} staat niet in de pagina"
    for bron in regels["bronnen"]:
        assert bron["titel"] in html
        for kolom in bron["kolommen"]:
            assert kolom in html


def test_paden_gaan_mee_zonder_de_vragen(html, paden):
    for blad in paden["bladeren"]:
        assert blad["titel"] in html
        for cp in blad["chokepoints"]:
            assert cp["id"] in html
    # De vragen van de zelfcheck horen hier niet; die wonen in check/.
    assert '"onderdelen"' not in html
    eerste_vraag = paden["onderdelen"][0]["vragen"][0]
    if isinstance(eerste_vraag, dict) and eerste_vraag.get("claim"):
        assert eerste_vraag["claim"] not in html


def test_geen_externe_verwijzingen(html):
    verwijzingen = re.findall(r'(?:src|href)="([^"]+)"', html)
    extern = [v for v in verwijzingen
              if v.startswith("http") and "security-commons-nl" not in v]
    assert extern == [], extern
    assert "fonts.googleapis" not in html


def test_csp_en_een_script(html):
    csp = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in csp
    assert "connect-src" not in csp, "meting praat met niemand"
    assert "form-action 'none'" in csp and "base-uri 'none'" in csp
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    assert f"sha256-{hash_van(script)}" in csp
    assert f"sha256-{hash_van(css)}" in csp
    assert html.count("<script>") == 1 and html.count("<style>") == 1
    assert "<script src" not in html and ' style="' not in html


def test_de_pagina_kent_geen_netwerk(html, app_js):
    """Geen enkele netwerkaanroep in de tool, ook niet via de kern die uit de AI-hulp meekomt.

    Op de aanroepvorm toetsen en niet op het losse woord: kern.js legt in zijn eigen commentaar uit
    dat hij geen fetch en geen XMLHttpRequest kent, en dat is precies de zin die een tekstvergelijking
    ten onrechte rood maakt.
    """
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    for verboden in ("fetch(", "new XMLHttpRequest", "new WebSocket", "new EventSource",
                     "navigator.sendBeacon", "import("):
        assert verboden not in script, f"{verboden} hoort niet in meting te staan"
    assert "fetch(" not in app_js
    # De kern gaat wel mee: zonder hem kan de tool het citaat bij een AI-voorstel niet controleren.
    assert "kern.bronregel_klopt" in script


def test_de_klok_zit_alleen_in_vandaag(app_js):
    """Elke termijn rekent vanaf de peildatum; new Date() mag alleen de standaarddatum voeden."""
    regels_met_datum = [r.strip() for r in app_js.splitlines() if "new Date()" in r]
    assert len(regels_met_datum) == 1, regels_met_datum
    assert "var nu = new Date();" in app_js
    assert "Date.now(" not in app_js


def test_app_js_bevat_geen_kopie_van_de_regels(app_js, regels):
    for item in regels["items"]:
        assert item["label"] not in app_js, f"label van {item['id']} staat in app.js"
        assert item["regel"]["uitleg"][:40] not in app_js
    for bron in regels["bronnen"]:
        assert bron["uitleg"][:40] not in app_js
        assert bron["hoe"][:40] not in app_js
    # Drempels horen uit regels.json te komen, niet uit code.
    for getal in ("minimaal_pct: 95", "minimaal: 10", "dagen: 90"):
        assert getal not in app_js


def test_drempels_komen_uit_de_regels(app_js):
    for parameter in ("param(regels, '4.4').minimaal_pct", "param(regels, '3.5').dagen",
                      "param(regels, '5.2').maximale_uren", "param(regels, '6.1').maximale_uren"):
        assert parameter in app_js, f"{parameter} wordt niet uit de regels gelezen"


def test_schermen_en_ids(html):
    for scherm in ("items", "paden", "hosts", "dashboard", "uitdraai"):
        assert f'id="scherm-{scherm}"' in html
        assert f'id="tab-{scherm}"' in html
    for id_ in ("org-naam", "org-peildatum", "filter-verdict", "filter-soort", "knop-opslaan",
                "knop-laden", "knop-zelfcheck-export", "knop-wissen", "dossier-status",
                "paden-samenvatting", "tabel-routes", "tabel-bevindingen"):
        assert f'id="{id_}"' in html, id_


def test_noscript_en_kruimelpad(html):
    assert "<noscript>" in html
    assert "regels.json" in html
    assert 'aria-label="Kruimelpad"' in html
    assert "EUPL-1.2" in html


def test_vingerafdruk_klopt(html, reken, regels):
    vinger = re.search(r'"vingerafdruk":"([0-9a-f]{64})"', html)
    assert vinger and vinger.group(1) == reken.vingerafdruk(regels)


def test_herhaalbaar(tmp_path):
    import bouw as bouwer
    assert bouwer.bouw(tmp_path / "a").read_bytes() == bouwer.bouw(tmp_path / "b").read_bytes()


def test_grootte(gebouwd):
    kb = gebouwd.stat().st_size / 1024
    assert 100 < kb < 400, kb


def test_app_js_spiegelt_reken_py(app_js):
    """Elke publieke functie uit reken.py staat ook in app.js.

    Dat is de kern van de opzet: de referentie in Python en de pagina in de browser horen dezelfde
    namen en dezelfde uitkomsten te hebben. Verdwijnt hier een naam, dan rekent de pagina stil iets
    anders dan de referentie, en dan is de uitkomst niet meer na te rekenen.
    """
    referentie = (METING / "reken.py").read_text(encoding="utf-8")
    namen = re.findall(r"^def ([a-z][a-z0-9_]*)\(", referentie, re.M)
    assert len(namen) >= 60, "de referentie is onverwacht klein geworden"
    ontbreekt = [naam for naam in namen if "reken." + naam + " = " not in app_js]
    assert not ontbreekt, f"niet gespiegeld in app.js: {ontbreekt}"

def test_wie_staat_op_de_pagina(html):
    """Het label en de uitleg gaan mee, zodat de pagina zelf zegt wie de export kan leveren."""
    for waarde in ("zelf te trekken", "vraag aan beheer", "aparte afspraak"):
        assert waarde in html, waarde
    assert 'id="filter-wie"' in html
    assert "Zelf te trekken: een portaalexport" in html, "de uitleg uit regels.json ontbreekt"

def test_ai_knop_is_een_knop_en_staat_rechts(html):
    """De AI-hulp is een knop met accentrand, als laatste in de balk (keuze Bas 03-09-2026).

    Hij was een kaal linkje tussen echte knoppen. Nu heeft elk linkje in de balk de vorm van een knop,
    staat de AI-hulp rechts los van de dossieracties, en draagt hij de oranje rand die in deze
    huisstijl een bewuste keuze markeert. Niet gevuld: opt-in hoort niet de primaire actie te lijken.
    """
    balk = html.split('<div class="knoppen">', 1)[1].split("</div>", 1)[0]
    assert 'id="knop-ai"' in balk
    assert balk.rindex('id="knop-ai"') > balk.rindex('href="../normen/"'), "AI-hulp hoort achteraan"
    assert ".knoppen a#knop-ai" in html and "margin-left: auto" in html
    assert "#e1a54a" in html, "de accentrand ontbreekt"

def test_recepten_staan_in_de_pagina(html):
    """De werkwijze gaat mee in het bestand: ook offline moet je weten waar je moet zijn."""
    for proef in ("Microsoft Entra admin center", "Waar vind ik dit, en hoe trek ik het?",
                  "GET /v1.0/users?", "ms-LAPS-PasswordExpirationTime", "Hernoem naar"):
        assert proef in html, proef
    assert "details" in html and "recept" in html
