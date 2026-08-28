"""paden.json is de enige bron; deze tests bewaken vorm en inhoud.

Faalt hier iets, repareer dan paden.json, niet het schema of de test.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import paden as helper  # noqa: E402

PADEN = ROOT / "paden.json"
SCHEMA = ROOT / "tools" / "paden.schema.json"

# Redactiestatuut A2 en A3: geen organisatienamen, adressen of sociale media in de bron.
VERBODEN = re.compile(
    r"\balkmaar\b|\bleiden\b|\bleiderdorp\b|\boegstgeest\b|\bzoeterwoude\b|"
    r"@[a-z0-9.-]+\.(?:nl|com)|linkedin|gemeentelijk",
    re.I,
)


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(PADEN.read_text(encoding="utf-8"))


def test_valideert_tegen_schema(data):
    jsonschema.validate(data, json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_elk_pad_hoort_bij_precies_een_cluster(data):
    in_cluster = [b for c in data["clusters"] for b in c["bladeren"]]
    assert len(in_cluster) == len(set(in_cluster)), "een blad staat in twee clusters"
    for blad in data["bladeren"]:
        if blad["type"] == "impact":
            assert blad["id"] not in in_cluster, f"{blad['id']} is impact en hoort in geen cluster"
        else:
            assert blad["id"] in in_cluster, f"{blad['id']} hoort in geen enkel cluster"


def test_ids_zijn_uniek_en_chokepoints_horen_bij_hun_blad(data):
    ids = [b["id"] for b in data["bladeren"]]
    assert len(ids) == len(set(ids))
    alle_cp = []
    for blad in data["bladeren"]:
        for cp in blad["chokepoints"]:
            assert cp["id"].startswith(blad["id"] + "-"), f"{cp['id']} hoort niet bij {blad['id']}"
            alle_cp.append(cp["id"])
    assert len(alle_cp) == len(set(alle_cp)), "dubbel chokepoint-id"


def test_ap17_is_impact_en_de_ddos_paden_zijn_pad(data):
    per_id = {b["id"]: b for b in data["bladeren"]}
    assert per_id["AP17"]["type"] == "impact", "ransomware is het gevolg, geen voordeur"
    assert per_id["AP15"]["type"] == "pad"
    assert per_id["AP16"]["type"] == "pad"


def test_elke_vraag_heeft_een_claim_als_vraagzin_en_een_actie(data):
    for blad in data["bladeren"]:
        for cp in blad["chokepoints"]:
            v = cp["vraag"]
            assert v["claim"].endswith("?"), f"{cp['id']}: claim is geen vraag"
            assert len(v["actie"]) > 10, f"{cp['id']}: geen bruikbare actie"
            assert v["actie"][0].isupper(), f"{cp['id']}: actie begint niet met een hoofdletter"


def test_elk_chokepoint_zegt_welk_bewijs_het_groen_maakt(data):
    for blad in data["bladeren"]:
        for cp in blad["chokepoints"]:
            assert len(cp["bewijs"]) > 20, f"{cp['id']}: bewijs te vaag"


def test_geen_organisatienamen_of_adressen(data):
    treffer = VERBODEN.search(json.dumps(data, ensure_ascii=False))
    assert treffer is None, f"verboden term in paden.json: {treffer.group(0)}"


def test_geen_em_dash(data):
    assert "—" not in json.dumps(data, ensure_ascii=False)


def test_helpers_geven_de_juiste_doorsneden():
    assert len(helper.bladeren()) == 18
    assert len(helper.paden()) == 17, "zeventien paden plus AP17 als impact"
    assert helper.blad("AP01")["titel"].startswith("Phishing")
    assert helper.cluster_van("AP01")["id"] == "C1"
    assert helper.cluster_van("AP17") is None
    assert helper.chokepoint("AP01-1")["blad"] == "AP01"
    assert helper.chokepoint("bestaat-niet") is None
    assert len(helper.chokepoints()) > 50


def test_de_bron_bevat_alle_vierenveertig_vragen_uit_de_zelfcheck():
    """De app stelt 44 vragen; de bron moet ze alle 44 kennen, anders loopt hij achter."""
    assert len(helper.alle_vragen()) == 44


def test_er_is_een_randvoorwaarde_voor_de_hele_beoordeling(data):
    ids = [r["id"] for r in data["randvoorwaarden"]]
    assert "soc" in ids, "de 24/7-opvolgingsvraag weegt over alle paden mee"
    for r in data["randvoorwaarden"]:
        assert r["vraag"]["claim"].endswith("?")
        assert len(r["werking"]) > 20


def test_geen_onvertaalde_escapes(data):
    """De bron komt uit een JavaScript-bundel; escapes horen gedecodeerd te zijn, niet letterlijk."""
    tekst = json.dumps(data, ensure_ascii=False)
    assert not re.search(r'\\x[0-9a-fA-F]{2}', tekst), 'niet-gedecodeerde hex-escape in de bron'
    assert not re.search(r'\\u[0-9a-fA-F]{4}', tekst), 'niet-gedecodeerde unicode-escape in de bron'
