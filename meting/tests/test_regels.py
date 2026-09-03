"""regels.json: klopt de tabel met zichzelf, met paden.json en met de applicatie op de tag?

Deze tests bewaken de overname. Wie een item, een bron of een drempel wijzigt, moet dat hier ook
verantwoorden; wie de koppeling aan een chokepoint verzint, valt om op paden.json.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

from conftest import METING, POSTURE, TAG, bronrepo

VERWACHTE_ITEMS = 41
VERWACHTE_CHOKEPOINTS = 22
VERWACHTE_SOORTEN = {"A": 32, "B": 4, "C": 5, "D": 0}
REGELTYPES = {"dekking", "drempel", "drempel_pct", "aanwezig", "datum", "firewall", "document",
              "geen_bevinding", "geen_rij", "iamscan", "spreiding"}


def test_versie_en_herkomst(regels):
    """De herkomst staat per onderdeel in de bron, met de tag erbij; anders is niets na te lopen."""
    assert regels["versie"] == "2026-09"
    herkomst = regels["bron"]
    assert set(herkomst) == {"items", "toetsregels", "iamscan", "paden", "gegenereerd_door"}
    assert "security-posture-tool" in herkomst["items"]
    assert "iamscan" in herkomst["iamscan"]
    for sleutel in ("items", "toetsregels", "iamscan"):
        assert "v0-applicatie" in herkomst[sleutel], sleutel


def test_aantallen(regels):
    assert len(regels["items"]) == VERWACHTE_ITEMS
    assert len({i["id"] for i in regels["items"]}) == VERWACHTE_ITEMS
    assert len(regels["bronnen"]) == len({b["id"] for b in regels["bronnen"]})
    telling = {s: sum(1 for i in regels["items"] if i["soort"] == s) for s in "ABCD"}
    assert telling == VERWACHTE_SOORTEN


def test_elk_item_heeft_een_bron_en_regel(regels):
    bronnen = {b["id"] for b in regels["bronnen"]}
    categorieen = {c["nummer"] for c in regels["categorieen"]}
    for item in regels["items"]:
        assert item["bron"] in bronnen, item["id"]
        if item.get("bron_alternatief"):
            assert item["bron_alternatief"] in bronnen, item["id"]
        assert item["soort"] in regels["soorten"], item["id"]
        assert item["categorie"] in categorieen, item["id"]
        assert item["regel"]["type"] in REGELTYPES, item["id"]
        assert item["regel"]["uitleg"].strip(), item["id"]
        assert isinstance(item["regel"]["parameters"], dict), item["id"]


def test_elke_bron_wordt_gebruikt(regels):
    gebruikt = {i["bron"] for i in regels["items"]}
    gebruikt |= {i["bron_alternatief"] for i in regels["items"] if i.get("bron_alternatief")}
    ongebruikt = {b["id"] for b in regels["bronnen"]} - gebruikt
    assert not ongebruikt, f"bron zonder item: {sorted(ongebruikt)}"


def test_chokepoints_bestaan_in_paden(regels, paden):
    bekend = {cp["id"] for blad in paden["bladeren"] for cp in blad.get("chokepoints", [])}
    gekoppeld = [i for i in regels["items"] if i.get("chokepoint")]
    for item in gekoppeld:
        assert item["chokepoint"] in bekend, item["id"]
        blad = next(b for b in paden["bladeren"] for cp in b.get("chokepoints", [])
                    if cp["id"] == item["chokepoint"])
        assert blad["id"] == item["pad"], f'{item["id"]}: {item["pad"]} tegen {blad["id"]}'
    assert len({i["chokepoint"] for i in gekoppeld}) == VERWACHTE_CHOKEPOINTS


def test_ongekoppelde_items_staan_apart(regels):
    zonder = sorted(i["id"] for i in regels["items"] if not i.get("chokepoint"))
    assert zonder == sorted(regels["ongekoppeld"].keys())
    for item_id, reden in regels["ongekoppeld"].items():
        assert reden.strip(), item_id


def test_tijdparameters_staan_in_de_items(regels):
    """Elke drempel in `tijd` komt terug in een item; document_dagen_per_maand is de uitzondering.

    Die laatste is geen drempel van een item maar de omrekening van maanden naar dagen, en staat
    daarom alleen in `tijd`. `reken.toets_document` haalt hem daar op.
    """
    gebruikt = json.dumps(regels["items"], ensure_ascii=False)
    for sleutel, waarde in regels["tijd"].items():
        if sleutel == "document_dagen_per_maand":
            continue
        assert str(waarde) in gebruikt, f"{sleutel} ({waarde}) komt in geen enkel item terug"
    assert regels["tijd"]["document_dagen_per_maand"] == 31


def test_iamscan_items(regels):
    iamscan = [i for i in regels["items"] if i["regel"]["type"] == "iamscan"]
    assert [i["id"] for i in iamscan] == ["10.1", "10.2", "10.3", "10.4"]
    assert [i["chokepoint"] for i in iamscan] == ["AP05-1", "AP05-1", "AP11-3", "AP11-3"]
    checks = [c for i in iamscan for c in i["regel"]["parameters"]["checks"]]
    assert len(checks) == len(set(checks)), "een controle telt maar bij een item mee"
    assert regels["iamscan"]["uid_grens_systeem"] == 1000
    assert "vim" in regels["iamscan"]["shell_escape"]


def test_elke_bron_zegt_wie_hem_levert(regels):
    """`wie` bepaalt de volgorde van een eerste ronde: eerst wat je zelf kunt, dan de vragen.

    De verdeling is geen willekeur en hoort vast te liggen: veertien meetregels komen uit exports die
    een CISO zelf trekt (Entra-portaal, eigen lijsten, eigen rapporten), drieentwintig vragen om
    beheer, en de vier iamscan-regels vragen een aparte afspraak omdat er iets op productiehosts
    draait.
    """
    assert set(regels["wie"]) == {"zelf", "beheer", "afspraak"}
    for waarde, uitleg in regels["wie"].items():
        assert uitleg.strip(), waarde
    per_bron = {b["id"]: b["wie"] for b in regels["bronnen"]}
    for bron in regels["bronnen"]:
        assert bron["wie"] in regels["wie"], bron["id"]
    telling = {"zelf": 0, "beheer": 0, "afspraak": 0}
    for item in regels["items"]:
        telling[per_bron[item["bron"]]] += 1
    assert telling == {"zelf": 14, "beheer": 23, "afspraak": 4}, telling
    assert per_bron["iamscan_dump"] == "afspraak"
    assert per_bron["document"] == "zelf", "de vijf documenten heeft de CISO zelf"


def test_vingerafdruk_is_stabiel(reken, regels):
    """Dezelfde inhoud geeft dezelfde vingerafdruk; een gewijzigde drempel niet."""
    eerste = reken.vingerafdruk(regels)
    assert eerste == reken.vingerafdruk(json.loads(json.dumps(regels)))
    anders = json.loads(json.dumps(regels))
    anders["tijd"]["nmap_max_dagen"] = 8
    assert reken.vingerafdruk(anders) != eerste


def test_overname_is_reproduceerbaar():
    """overname.py --check: regels.json past nog bij de applicatie op de tag."""
    bronrepo(POSTURE, "security-posture-tool")
    uit = subprocess.run([sys.executable, str(METING / "overname.py"), "--check"],
                         capture_output=True, cwd=str(METING.parent))
    melding = uit.stdout.decode("utf-8", "replace") + uit.stderr.decode("utf-8", "replace")
    assert uit.returncode == 0, melding


def test_posture_items_woordelijk(regels):
    """Label en doel van de 37 posture-items komen woordelijk uit checklist.py op de tag."""
    bronrepo(POSTURE, "security-posture-tool")
    import overname

    items, _, _ = overname.posture_items()
    origineel = {i["id"]: i for i in items}
    assert len(origineel) == 37
    for item in regels["items"]:
        if item["id"] not in origineel:
            assert item["id"].startswith("10."), item["id"]
            continue
        assert item["label"] == origineel[item["id"]]["label"], item["id"]
        assert item["doel"] == origineel[item["id"]]["target"], item["id"]


def test_documentregels_komen_uit_de_applicatie(regels):
    """De trefwoorden en vensters van soort C zijn letterlijk SHALLOW_RULES uit app.py."""
    pad = bronrepo(POSTURE, "security-posture-tool")
    ruw = subprocess.run(["git", "show", f"{TAG}:v0.1/app.py"], cwd=pad,
                         capture_output=True, check=True).stdout.decode("utf-8")
    blok = ruw[ruw.index("SHALLOW_RULES = {"):]
    blok = blok[:blok.index("\n}") + 2]
    ruimte: dict = {}
    exec(blok.replace("SHALLOW_RULES", "REGELS"), ruimte)  # noqa: S102 - eigen repo, eigen tag
    origineel = ruimte["REGELS"]
    documenten = [i for i in regels["items"] if i["bron"] == "document"]
    assert {i["id"] for i in documenten} == set(origineel)
    for item in documenten:
        parameters = item["regel"]["parameters"]
        assert parameters["trefwoorden"] == origineel[item["id"]]["must_match"], item["id"]
        assert parameters["maximale_maanden"] == origineel[item["id"]]["max_age_months"], item["id"]
        assert parameters["parser"] == origineel[item["id"]]["parser"], item["id"]


@pytest.mark.parametrize("bestand", ["regels.json"])
def test_json_is_netjes(bestand):
    """Twee spaties inspringen en een afsluitende regel: diffs blijven leesbaar."""
    tekst = (METING / bestand).read_text(encoding="utf-8")
    assert tekst.endswith("\n")
    assert "\r" not in tekst
    json.loads(tekst)
