"""De scoreregels in paden.json, getoetst via de referentie-implementatie.

De drie doorlopen (alles ja, alles nee, alles onbekend) zijn de basis. Daarnaast de regels die
alleen in de bron staan en dus alleen hier bewezen kunnen worden: het plafond, de omgekeerde vragen,
de randvoorwaarde, de AP05-modellen en de samenstelling van AP17.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import score  # noqa: E402


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads((ROOT / "paden.json").read_text(encoding="utf-8"))


def _alle_vragen(data: dict) -> list[str]:
    ids = {cp["vraag_id"] for b in data["bladeren"] for cp in b["chokepoints"]}
    ids |= {rv["vraag_id"] for rv in data["randvoorwaarden"]}
    return sorted(ids)


def _negatief(data: dict) -> set[str]:
    return {cp["vraag_id"] for b in data["bladeren"] for cp in b["chokepoints"] if cp.get("negatief")}


def alles(data: dict, antwoord: str, model: str) -> dict[str, str]:
    """Iedere vraag hetzelfde antwoord, met de negatieve vragen omgedraaid zodat de betekenis gelijk is."""
    neg = _negatief(data)
    omgekeerd = {"yes": "no", "no": "yes"}.get(antwoord, antwoord)
    a = {v: (omgekeerd if v in neg else antwoord) for v in _alle_vragen(data)}
    a["model"] = model
    return a


def test_vraag_ids_dekken_de_regelsets(data):
    ids = set(_alle_vragen(data))
    for b in data["bladeren"]:
        for rol in ("vereist", "beperkt", "reactief"):
            for v in b["regels"][rol]:
                assert v in ids, f"{b['id']}.{rol}: onbekende vraag {v}"
    assert data["regels"]["randvoorwaarde"] in ids
    for cp in (cp for b in data["bladeren"] for cp in b["chokepoints"]):
        if "alleen_als" in cp:
            assert cp["alleen_als"] in ids


def test_dezelfde_vraag_heeft_overal_dezelfde_claim(data):
    claim_per_id: dict[str, str] = {}
    for b in data["bladeren"]:
        for cp in b["chokepoints"]:
            eerder = claim_per_id.setdefault(cp["vraag_id"], cp["vraag"]["claim"])
            assert eerder == cp["vraag"]["claim"], f"{cp['vraag_id']} heeft twee claims"
    assert len(claim_per_id) + len(data["randvoorwaarden"]) == 44


def test_alles_ja_geeft_overal_sterk_behalve_de_plafonds(data):
    uit = score.beoordeel(data, alles(data, "yes", "dedicated"))
    met_plafond = {b["id"] for b in data["bladeren"] if "plafond" in b["regels"]}
    assert met_plafond == {"AP07", "AP08", "AP18"}
    for b in data["bladeren"]:
        verwacht = "limited" if b["id"] in met_plafond or b["id"] == "AP17" else "strong"
        assert uit[b["id"]]["status"] == verwacht, b["id"]
    # AP17 erft het plafond van AP07: de slechtste toegangsroute is beperkt, herstel is sterk.
    assert uit["AP17"]["toegang"] == "limited" and uit["AP17"]["herstel"] == "strong"
    assert score.acties(data, alles(data, "yes", "dedicated"), uit) == []


def test_alles_nee_geeft_overal_open(data):
    uit = score.beoordeel(data, alles(data, "no", "permanent"))
    assert {u["status"] for u in uit.values()} == {"open"}
    assert uit["AP17"]["herstel"] == "open"


def test_alles_onbekend_geeft_overal_onbekend(data):
    uit = score.beoordeel(data, alles(data, "unknown", "unknown"))
    assert {u["status"] for u in uit.values()} == {"unknown"}


def test_lege_antwoorden_tellen_als_onbekend(data):
    uit = score.beoordeel(data, {})
    assert {u["status"] for u in uit.values()} == {"unknown"}


def test_reactief_vereist_de_randvoorwaarde(data):
    basis = alles(data, "yes", "dedicated")
    basis["pr"] = "no"                      # AP01 mist een vereiste barriere, concreet
    basis["soc"] = "yes"
    assert score.beoordeel(data, basis)["AP01"]["status"] == "reactive"
    basis["soc"] = "no"
    assert score.beoordeel(data, basis)["AP01"]["status"] == "open"
    basis["soc"] = "yes"
    basis["idresponse"] = "no"              # geen response meer aanwezig
    assert score.beoordeel(data, basis)["AP01"]["status"] == "open"


def test_beperkt_gaat_voor_reactief(data):
    basis = alles(data, "yes", "dedicated")
    basis["legacy"] = "no"                  # AP02: vereist mist legacy, beperkt (pr, fallback) is compleet
    assert score.beoordeel(data, basis)["AP02"]["status"] == "limited"


def test_negatieve_vraag_wordt_omgedraaid(data):
    basis = alles(data, "yes", "dedicated")
    basis["fallback"] = "yes"               # ja = er is nog een zwakke route = barriere ontbreekt
    assert "fallback" in score.beoordeel(data, basis)["AP01"]["ontbrekend"]
    basis["fallback"] = "no"
    assert "fallback" not in score.beoordeel(data, basis)["AP01"]["ontbrekend"]


def test_ap05_volgt_het_beheermodel(data):
    basis = alles(data, "yes", "dedicated")
    assert score.beoordeel(data, basis)["AP05"]["status"] == "strong"
    basis["model"] = "separate"
    assert score.beoordeel(data, basis)["AP05"]["status"] == "open"
    basis["model"] = "hardened"
    basis["key"] = "no"                     # concreet tekort, maar adminhard/jit/elevation staan
    assert score.beoordeel(data, basis)["AP05"]["status"] == "limited"
    basis["model"] = "unknown"
    assert score.beoordeel(data, basis)["AP05"]["status"] == "unknown"


def test_ap17_is_de_slechtste_van_toegang_en_herstel(data):
    basis = alles(data, "yes", "dedicated")
    basis["backup"] = "no"
    uit = score.beoordeel(data, basis)
    assert uit["AP17"]["status"] == "open" and uit["AP17"]["herstel"] == "open"
    basis["backup"] = "yes"
    basis["crisis"] = "no"                  # backup en restore ja: herstel beperkt
    uit = score.beoordeel(data, basis)
    assert uit["AP17"]["herstel"] == "limited" and uit["AP17"]["status"] == "limited"
    basis["pr"] = "no"                      # toegang wordt reactief (soc ja), en dat weegt zwaarder
    uit = score.beoordeel(data, basis)
    assert uit["AP17"]["toegang"] == "reactive" and uit["AP17"]["status"] == "reactive"
    assert "pr" in uit["AP17"]["ontbrekend"]


def test_acties_wegen_preventief_zwaarder_en_geven_er_drie(data):
    basis = alles(data, "yes", "dedicated")
    basis["pr"] = "no"                      # preventief, ontbreekt bij AP01, AP02, AP08 en AP17
    basis["restore"] = "no"                 # vereist bij AP17 alleen; crisis zou niet tellen, dat is reactief
    uit = score.beoordeel(data, basis)
    top = score.acties(data, basis, uit)
    assert len(top) <= data["regels"]["acties"]["aantal"]
    assert top[0]["vraag_id"] == "pr"
    assert {a["vraag_id"] for a in top} >= {"pr", "restore"}
    assert all(top[i]["gewicht"] >= top[i + 1]["gewicht"] for i in range(len(top) - 1))


def test_restore_valt_weg_als_actie_zonder_backup(data):
    basis = alles(data, "no", "permanent")
    top = score.acties(data, basis, score.beoordeel(data, basis))
    assert "restore" not in {a["vraag_id"] for a in top}


def test_referentie_geeft_dezelfde_uitslag_als_de_echte_app(data):
    """De doorloop van 28-08-2026: dezelfde antwoorden, dezelfde uitslag als de gecompileerde zelfcheck."""
    fx = json.loads((ROOT / "tests" / "fixtures" / "doorloop-2026-08-28.json").read_text(encoding="utf-8"))
    uit = score.beoordeel(data, fx["antwoorden"])
    verschil = {p: (uit[p]["status"], s) for p, s in fx["status_volgens_app"].items() if uit[p]["status"] != s}
    assert not verschil, f"(referentie, app): {verschil}"
    top = score.acties(data, fx["antwoorden"], uit)
    assert [a["vraag_id"] for a in top] == fx["acties_volgens_app"]
    for vid, paden in fx["acties_helpen_bij"].items():
        assert sorted(next(a for a in top if a["vraag_id"] == vid)["helpt"]) == paden
