"""De mappingen: vorm, volledigheid en de belofte die eronder ligt.

Een mapping is een uitspraak over andermans normenkader. Dat mag, mits hij precies is en mits stilte
nooit een vergissing kan zijn. Deze tests bewaken drie dingen:

1. Elke regel wijst naar een barriere die bestaat en naar een maatregel die bestaat.
2. Elke barriere staat of in de regels, of met een reden bij de ongekoppelde. Nooit geen van beide.
3. De relatie is er maar een, en hij heeft altijd een richting: een barriere levert bewijs, hij dekt
   niets af. Zodra hier "voldoet aan" verschijnt, is het een afvinkinstrument geworden.

Faalt hier iets, repareer dan de mapping, niet de test.
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

from tools import mappingen as helper  # noqa: E402
from tools import paden as paden_bron  # noqa: E402

SCHEMA = json.loads((ROOT / "mappingen" / "mapping.schema.json").read_text(encoding="utf-8"))
KADERS = helper.kaders()

# Woorden die een mapping tot iets anders maken dan hij is. "Dekt af" en "voldoet aan" zijn een
# oordeel over compliance; dat oordeel is niet aan een zelfcheck. Een "compliant apparaat" is wel
# toegestaan: dat is de vakterm uit apparaatbeheer voor een toestel dat aan het beleid voldoet, en
# geen uitspraak over de organisatie.
VERBODEN_TAAL = re.compile(
    r"\bvoldoet aan\b|\bdekt (?:het |de |)af\b|\bcompliant\b(?! apparaat)|\baantoonbaar voldaan\b", re.I
)
# Redactiestatuut: geen em-dashes, geen organisatienamen als herkomst.
EM_DASH = re.compile(r"[—–]")


def test_er_is_ten_minste_een_kader():
    assert KADERS, "geen enkele mapping gevonden in mappingen/"


@pytest.mark.parametrize("kader", KADERS)
def test_valideert_tegen_schema(kader):
    jsonschema.validate(helper.mapping(kader), SCHEMA)


@pytest.mark.parametrize("kader", KADERS)
def test_kader_verwijst_naar_een_bestaande_bron(kader):
    bron = helper.bron(kader)
    assert bron["kader"] == kader
    assert bron["maatregelen"], "een bron zonder maatregelen kan niets verankeren"
    assert bron["bron"], "een bron zonder herkomst is niet te controleren"


@pytest.mark.parametrize("kader", KADERS)
def test_elke_regel_wijst_naar_een_bestaande_barriere(kader):
    bekend = set(helper.barrieres())
    onbekend = sorted({r["barriere"] for r in helper.mapping(kader)["regels"]} - bekend)
    assert not onbekend, f"{kader}: regels voor barrieres die niet in paden.json staan: {onbekend}"


@pytest.mark.parametrize("kader", KADERS)
def test_elke_regel_wijst_naar_een_bestaande_maatregel(kader):
    bekend = {m["id"] for m in helper.maatregelen(kader)}
    onbekend = sorted({r["norm"] for r in helper.mapping(kader)["regels"]} - bekend)
    assert not onbekend, f"{kader}: regels voor maatregelen die niet in de bron staan: {onbekend}"


@pytest.mark.parametrize("kader", KADERS)
def test_elke_barriere_is_gemapt_of_met_reden_ongekoppeld(kader):
    """Stilte mag geen vergissing kunnen zijn. Dit is de kern van de belofte."""
    data = helper.mapping(kader)
    gemapt = {r["barriere"] for r in data["regels"]}
    ongekoppeld = {x["barriere"] for x in data["ongekoppeld"]}
    alle = set(helper.barrieres())

    vergeten = sorted(alle - gemapt - ongekoppeld)
    assert not vergeten, (
        f"{kader}: deze barrieres staan nergens. Zet ze in regels, of in ongekoppeld met de reden "
        f"waarom dit kader er niets over zegt: {vergeten}"
    )
    beide = sorted(gemapt & ongekoppeld)
    assert not beide, f"{kader}: barriere staat zowel gemapt als ongekoppeld: {beide}"


@pytest.mark.parametrize("kader", KADERS)
def test_geen_dubbele_paren(kader):
    paren = [(r["barriere"], r["norm"]) for r in helper.mapping(kader)["regels"]]
    dubbel = sorted({p for p in paren if paren.count(p) > 1})
    assert not dubbel, f"{kader}: dezelfde barriere en maatregel staan twee keer: {dubbel}"


@pytest.mark.parametrize("kader", KADERS)
def test_de_relatie_is_er_maar_een(kader):
    relaties = {r["relatie"] for r in helper.mapping(kader)["regels"]}
    assert relaties == {"levert-bewijs-voor"}, (
        f"{kader}: er is precies een relatie. Een tweede relatie is het begin van een afvinklijst: {relaties}"
    )


@pytest.mark.parametrize("kader", KADERS)
def test_geen_taal_die_compliance_belooft(kader):
    data = helper.mapping(kader)
    teksten = [(r["barriere"], r["norm"], r["reden"]) for r in data["regels"]]
    teksten += [(x["barriere"], "ongekoppeld", x["reden"]) for x in data["ongekoppeld"]]
    fout = [(b, n, VERBODEN_TAAL.search(t).group(0)) for b, n, t in teksten if VERBODEN_TAAL.search(t)]
    assert not fout, (
        f"{kader}: een reden belooft compliance in plaats van bewijs. Schrijf wat het bewijs aantoont: {fout}"
    )


@pytest.mark.parametrize("kader", KADERS)
def test_redenen_zijn_een_leesbare_zin_zonder_em_dash(kader):
    data = helper.mapping(kader)
    teksten = [(r["barriere"], r["reden"]) for r in data["regels"]]
    teksten += [(x["barriere"], x["reden"]) for x in data["ongekoppeld"]]
    for barriere, tekst in teksten:
        assert not EM_DASH.search(tekst), f"{kader}/{barriere}: em-dash in de reden (redactiestatuut)"
        assert tekst[0].isupper(), f"{kader}/{barriere}: reden begint niet met een hoofdletter"
        assert tekst.rstrip().endswith("."), f"{kader}/{barriere}: reden eindigt niet op een punt"


@pytest.mark.parametrize("kader", KADERS)
def test_elke_barriere_heeft_ten_minste_een_regel_die_niet_alleen_raakvlak_is(kader):
    """Een barriere die in een kader alleen raakvlakken heeft, hoort bij de ongekoppelde te staan.

    Anders suggereert de pagina dekking waar alleen verwantschap is.
    """
    data = helper.mapping(kader)
    per_barriere: dict[str, set[str]] = {}
    for regel in data["regels"]:
        per_barriere.setdefault(regel["barriere"], set()).add(regel["sterkte"])
    alleen_raakvlak = sorted(b for b, s in per_barriere.items() if s == {"raakvlak"})
    assert not alleen_raakvlak, (
        f"{kader}: deze barrieres hebben alleen raakvlakken. Zet ze bij ongekoppeld met de reden, "
        f"of onderbouw een sterkere regel: {alleen_raakvlak}"
    )


def test_barrieres_zijn_consistent_in_de_bron():
    """Dezelfde barriere bij meer paden moet overal dezelfde vraag en hetzelfde bewijs hebben.

    De mapping hangt aan de barriere. Zouden twee chokepoints met hetzelfde vraag_id uit elkaar lopen,
    dan zou een mapping-regel bij het ene wel en bij het andere niet kloppen, zonder dat het opvalt.
    """
    data = paden_bron.laad()
    losse = [cp for b in data["bladeren"] for cp in b["chokepoints"]] + data.get("randvoorwaarden", [])
    per_id: dict[str, list[dict]] = {}
    for cp in losse:
        per_id.setdefault(cp["vraag_id"], []).append(cp)

    for vraag_id, groep in per_id.items():
        titels = {cp["titel"] for cp in groep}
        claims = {cp["vraag"]["claim"] for cp in groep}
        bewijzen = {cp.get("bewijs", "") for cp in groep}
        assert len(titels) == 1, f"{vraag_id}: verschillende titels bij dezelfde barriere: {titels}"
        assert len(claims) == 1, f"{vraag_id}: verschillende claims bij dezelfde barriere: {claims}"
        assert len(bewijzen) == 1, f"{vraag_id}: verschillend bewijs bij dezelfde barriere: {bewijzen}"


@pytest.mark.parametrize("kader", KADERS)
def test_de_witte_vlekken_zijn_echt_niet_aangetoond(kader):
    """Een raakvlak is geen bewijs, dus een maatregel met alleen raakvlakken blijft een witte vlek.

    Zou een raakvlak wel als dekking tellen, dan gaf de pagina precies de valse zekerheid die dit
    instrument probeert te vermijden. De raakvlakken gaan wel mee, zodat de lezer ziet waarom het
    in de buurt komt en toch niet telt.
    """
    aangetoond = helper.aangetoond(kader)
    for maatregel in helper.witte_vlekken(kader):
        assert maatregel["id"] not in aangetoond
        for regel in maatregel["raakvlakken"]:
            assert regel["sterkte"] == "raakvlak"


@pytest.mark.parametrize("kader", KADERS)
def test_een_raakvlak_telt_nooit_als_dekking(kader):
    alleen_raakvlak = [m for m in helper.witte_vlekken(kader) if m["raakvlakken"]]
    telling = helper.dekking(kader)
    assert len(alleen_raakvlak) == telling["alleen_raakvlak"]
    assert telling["geraakt"] <= len({r["norm"] for r in helper.mapping(kader)["regels"]})


def test_bio2_verwijst_naar_de_gedeelde_dataset():
    """De BIO2-bron is een kopie. Een kopie zonder herkomst is een tweede waarheid."""
    bron = helper.bron("bio2")["bron"]
    assert "normen" in bron["herkomst"], "de herkomst van de BIO2-kopie moet naar de bron wijzen"
    assert re.fullmatch(r"[0-9a-f]{40}|onbekend", bron["commit"]), "commit is geen geldige hash"


def test_bio2_bevat_geen_iso_maatregelteksten():
    """ISO 27002-teksten zijn auteursrechtelijk beschermd; we hebben ze hier niet nodig.

    De bron draagt alleen nummer, titel, thema en de overheidsmaatregel-ids. Verschijnt hier ooit een
    veld met de normtekst zelf, dan publiceren we andermans auteursrechtelijk werk.
    """
    toegestaan = {"id", "titel", "thema", "overheidsmaatregelen"}
    for maatregel in helper.maatregelen("bio2"):
        extra = set(maatregel) - toegestaan
        assert not extra, f"{maatregel['id']}: onverwachte velden in de BIO2-bron: {extra}"
        assert len(maatregel["titel"]) < 120, f"{maatregel['id']}: titel is te lang voor een titel"


def test_wpg_dekt_het_hele_toetsingskader():
    """31 beheersingsmaatregelen plus de vijf uit bijlage 4."""
    ids = [m["id"] for m in helper.maatregelen("wpg")]
    genummerd = [i for i in ids if i.startswith("W")]
    bijlage = [i for i in ids if i.startswith("B4-")]
    assert len(genummerd) == 31, f"het Wpg-kader heeft 31 beheersingsmaatregelen, gevonden: {len(genummerd)}"
    assert len(bijlage) == 5, f"bijlage 4 heeft vijf maatregelen, gevonden: {len(bijlage)}"


def test_wpg_laat_zien_dat_een_zelfcheck_niet_het_hele_kader_raakt():
    """Het punt van dit kader: security is niet alles.

    Zou dit ooit omslaan, dan is er iets mis: of de mapping is te ruim geworden, of iemand heeft
    normen weggelaten die niet uitkwamen.
    """
    telling = helper.dekking("wpg")
    assert telling["witte_vlekken"] > telling["geraakt"], (
        "in het Wpg-kader horen meer maatregelen ongeraakt te blijven dan geraakt: het kader gaat "
        "over rechtmatige verwerking, de zelfcheck over aanvalspaden"
    )


@pytest.mark.parametrize("kader", KADERS)
def test_dekking_telt_op(kader):
    telling = helper.dekking(kader)
    assert telling["geraakt"] + telling["witte_vlekken"] == telling["maatregelen"]
    assert telling["barrieres_gemapt"] + telling["barrieres_ongekoppeld"] == len(helper.barrieres())


def test_elk_kader_staat_in_de_redactionele_volgorde():
    """De volgorde bepaalt welk kader de pagina opent, dus die keuze is bewust en niet alfabetisch.

    Een nieuw kader dat hier niet in staat, belandt achteraan zonder dat iemand daar iets van vindt.
    Deze test dwingt af dat je er een plek voor kiest.
    """
    ongeplaatst = [k for k in KADERS if k not in helper.VOLGORDE]
    assert not ongeplaatst, (
        f"deze kaders staan niet in tools/mappingen.py VOLGORDE: {ongeplaatst}. "
        "Kies een plek; de eerste in de rij is wat de pagina opent."
    )


def test_de_pagina_opent_op_bio2():
    """BIO 2.0 is het kader waar de doelgroep op wordt bevraagd, dus dat staat voorop."""
    assert KADERS[0] == "bio2"
