"""reken.py: de referentie. Getoetst op de voorbeeldexports, op de peildatum en op de applicatie.

Drie soorten tests staan hier naast elkaar:
  1. de rekenhulpjes zelf (tijd, csv, xml), waar de scherpe randjes zitten;
  2. elke bron een keer door zijn toets, met de verwachte uitkomst per item;
  3. de vergelijking met de applicatie op tag v0-applicatie: dezelfde export, hetzelfde oordeel.
De derde soort wordt overgeslagen zodra de bronrepo's niet meer als buurmap staan (ze worden na de
overname gearchiveerd). Wat dan overblijft, is de referentie zelf, en die is hier vastgelegd.
"""
from __future__ import annotations

import datetime
import importlib
import io
import json
import sys
import tarfile

import pytest

from conftest import (BESTAND_PER_BRON, DOCUMENT_PER_ITEM, FIXTURES, IAMSCAN, POSTURE, bronrepo,
                      lees)

# Wat de voorbeeldexports horen op te leveren. Drie regels vallen bewust om: 3.4 (LAPS ontbreekt op
# SRV-010), 10.1 en 10.2 (de dump van web01 heeft een sudo-shell-escape en een tweede UID 0).
VERWACHT = {
    "1.1": "pass", "1.2": "pass", "1.3": "pass", "2.1": "pass", "2.2": "pass", "2.3": "pass",
    "2.4": "pass", "2.5": "pass", "3.1": "pass", "3.2": "pass", "3.3": "pass", "3.4": "fail",
    "3.5": "pass", "4.1": "pass", "4.2": "pass", "4.3": "pass", "4.4": "pass", "4.5": "pass",
    "4.6": "pass", "5.1": "pass", "5.2": "pass", "5.3": "pass", "5.4": "pass", "6.1": "pass",
    "6.2": "pass", "6.3": "pass", "7.1": "pass", "7.2": "pass", "7.3": "pass", "7.4": "pass",
    "8.1": "pass", "8.2": "pass", "8.3": "pass", "8.4": "pass", "9.1": "pass", "9.2": "pass",
    "9.3": "pass", "10.1": "fail", "10.2": "fail", "10.3": "pass", "10.4": "pass",
}

# De connector in de applicatie die hetzelfde meet. De vier entra-bronnen staan er niet in: die
# haalde de applicatie via Graph op, hier zijn het exports (zie verantwoording.md).
CONNECTOR_PER_BRON = {
    "crown_jewels_csv": "crown_jewels_csv", "asset_inventory_csv": "asset_inventory",
    "fw_config": "fortigate_config", "vpn_inventory_csv": "vpn_inventory_csv",
    "ad_tier0_csv": "ad_tier0_csv", "gpo_export_xml": "gpo_export_xml",
    "ad_svc_accounts_csv": "ad_svc_accounts_csv", "laps_csv": "laps_csv",
    "siem_flow_csv": "siem_flow_csv", "sysmon_config_xml": "sysmon_config_xml",
    "fw_flow_csv": "fw_flow_csv", "siem_rules_json": "siem_rules_json",
    "nessus_xml": "nessus_xml", "edge_devices_csv": "edge_devices_csv",
    "eol_inventory_csv": "eol_inventory_csv", "nmap_xml": "nmap_xml",
    "veeam_report_csv": "veeam_report", "backup_ad_audit_csv": "backup_ad_audit_csv",
    "wdac_policy_xml": "wdac_policy_xml", "asr_csv": "asr_csv",
    "local_admins_csv": "local_admins_csv", "intune_usb_csv": "intune_usb_csv",
    "siem_behavior_rules_json": "siem_behavior_rules_json", "fw_category_csv": "fw_category_csv",
}

# Deze connectors rekenen met datetime.now(); meting rekent met de peildatum. Op de peildatum van de
# fixtures vallen ze samen, daarna niet meer. De vergelijking slaat ze over, de peildatum-tests
# hieronder dekken ze wel.
KLOKGEVOELIG = {"edge_devices_csv", "nessus_xml", "nmap_xml", "siem_flow_csv", "veeam_report_csv"}

# Hier wijkt meting bewust af van de applicatie; de reden staat in verantwoording.md en in de test
# onderaan dit bestand.
AFWIJKEND = {"wdac_policy_xml"}


# ── De rekenhulpjes ──────────────────────────────────────────────────────────


def test_rond_half_omhoog(reken):
    """Python rondt bankiersgewijs af (round(0.5) is 0); dat mag hier niet gebeuren."""
    assert reken.rond_half_omhoog(0.5) == 1
    assert reken.rond_half_omhoog(1.5) == 2
    assert reken.rond_half_omhoog(2.5) == 3
    assert reken.rond_half_omhoog(-0.5) == 0


def test_procent(reken):
    assert reken.procent(0, 0) == 0
    assert reken.procent(1, 3) == 33
    assert reken.procent(2, 3) == 67
    assert reken.procent(12, 12) == 100


@pytest.mark.parametrize("waarde,verwacht", [
    # De zone blijft staan zoals hij er staat; het moment telt, niet de schrijfwijze.
    ("2026-09-03", "2026-09-03T00:00:00+00:00"),
    ("2026-09-03T14:30:00", "2026-09-03T14:30:00+00:00"),
    ("2026-09-03T14:30:00Z", "2026-09-03T14:30:00+00:00"),
    ("2026-09-03T14:30:00+02:00", "2026-09-03T14:30:00+02:00"),
    ("laatste test op 2026/03/12 door de leverancier", "2026-03-12T00:00:00+00:00"),
])
def test_lees_datum(reken, waarde, verwacht):
    assert reken.lees_datum(waarde).isoformat() == verwacht


@pytest.mark.parametrize("waarde", ["", None, "onbekend", "31-13-2026", "2026-02-30"])
def test_lees_datum_zonder_datum(reken, waarde):
    assert reken.lees_datum(waarde) is None


def test_peil_is_einde_van_de_dag(reken):
    """Een artefact van de peildatum zelf is nul dagen oud, niet een dag."""
    assert reken.peil("2026-09-03").isoformat() == "2026-09-03T23:59:59+00:00"
    assert reken.dagen_tussen("2026-09-03", "2026-09-03") == 0
    assert reken.dagen_tussen("2026-09-02", "2026-09-03") == 1


def test_tijd_rekent_vanaf_de_peildatum(reken):
    """Niet vanaf de klok: dezelfde export geeft over een jaar hetzelfde antwoord."""
    assert reken.dagen_tussen("2026-01-01", "2026-09-03") == 245
    assert reken.dagen_tussen("2030-01-01", "2026-09-03") == 0, "toekomst telt als nul, niet negatief"
    assert reken.uren_tussen("2026-09-03T00:00:00", "2026-09-03") == pytest.approx(23.99972, abs=1e-3)
    assert reken.dagen_tussen("geen datum", "2026-09-03") is None


def test_lees_csv(reken):
    koppen, rijen = reken.lees_csv("﻿Naam , owner\nBRP,Team A\n")
    assert koppen == ["naam", "owner"], "BOM weg en koppen in kleine letters"
    assert rijen == [{"naam": "BRP", "owner": "Team A"}]

    koppen, rijen = reken.lees_csv("naam;owner\nBRP;Team A\n")
    assert koppen == ["naam", "owner"], "puntkomma als terugval"

    _, rijen = reken.lees_csv('naam,owner\n"Burgerzaken, balie",Team A\n')
    assert rijen[0]["naam"] == "Burgerzaken, balie"

    _, rijen = reken.lees_csv("naam,owner\nBRP\n")
    assert rijen[0]["owner"] == "", "te korte rij vult aan met lege cellen"

    assert reken.lees_csv("") == ([], [])


def test_truthy_en_falsy(reken):
    for waarde in ("true", "Ja", "1", "ENABLED", " yes "):
        assert reken.truthy(waarde), waarde
    for waarde in ("false", "nee", "0", "disabled"):
        assert reken.falsy(waarde), waarde
    assert not reken.truthy("")
    assert not reken.truthy(None)
    assert not reken.truthy("misschien")


def test_lees_xml_faalt_zacht(reken):
    assert reken.lees_xml("<a><b></a>") is None
    assert reken.lees_xml("geen xml") is None
    assert reken.lees_xml("<Sysmon/>") is not None


# ── Elke bron een keer ───────────────────────────────────────────────────────


@pytest.mark.parametrize("bron,bestand", sorted(BESTAND_PER_BRON.items()))
def test_toets_per_bron(reken, regels, peildatum, bron, bestand):
    uit = reken.toets(bron, lees(bestand), peildatum, regels)
    assert uit["verdicts"], f"{bron} levert geen enkel verdict"
    for item_id, verdict in uit["verdicts"].items():
        assert verdict == VERWACHT[item_id], f"{bron} → {item_id}: {uit['samenvatting']}"


@pytest.mark.parametrize("item_id,bestand", sorted(DOCUMENT_PER_ITEM.items()))
def test_toets_document(reken, regels, peildatum, item_id, bestand):
    uit = reken.toets("document", lees(bestand), peildatum, regels, item_id)
    assert uit["verdicts"] == {item_id: VERWACHT[item_id]}, uit["fouten"]
    assert uit["artefact_datum"], "een document zonder datum is niet te dateren"


def test_alle_items_zijn_gedekt(regels, doorloop):
    """De doorloop raakt alle 41 items; anders is er een bron zonder voorbeeldexport."""
    gemeten = set(doorloop["metingen"])
    assert gemeten == {i["id"] for i in regels["items"]}
    assert {i: m["verdict"] for i, m in doorloop["metingen"].items()} == VERWACHT


def test_ontbrekende_kolom_is_unparsed(reken, regels, peildatum):
    """Een export met de verkeerde kolommen is niet fout maar onleesbaar; dat is een ander oordeel."""
    uit = reken.toets("crown_jewels_csv", "titel,eigenaar\nBRP,Jan\n", peildatum, regels)
    assert uit["verdicts"] == {"1.1": "unparsed", "1.2": "unparsed"}
    assert "name" in uit["fouten"][0]

    uit = reken.toets("fw_config", "dit is geen firewallconfig", peildatum, regels)
    assert set(uit["verdicts"].values()) == {"unparsed"}

    uit = reken.toets("siem_rules_json", "{geen json", peildatum, regels)
    assert uit["verdicts"] == {"4.5": "unparsed"}


def test_lege_lijst_is_fail_geen_pass(reken, regels, peildatum):
    """Nul rijen is geen honderd procent dekking. Een lege export bewijst niets."""
    uit = reken.toets("crown_jewels_csv", "name,owner\n", peildatum, regels)
    assert uit["verdicts"] == {"1.1": "fail", "1.2": "fail"}
    uit = reken.toets("laps_csv", "device_name,laps_configured\n", peildatum, regels)
    assert uit["verdicts"] == {"3.4": "fail"}


def test_verouderd_artefact_is_stale(reken, regels):
    """Dezelfde export, een latere peildatum: een scan die te oud is heet stale, niet fail."""
    nmap = lees("nmap-extern.xml")
    assert reken.toets("nmap_xml", nmap, "2026-09-03", regels)["verdicts"] == {"5.4": "pass"}
    later = reken.toets("nmap_xml", nmap, "2026-10-03", regels)
    assert later["verdicts"] == {"5.4": "stale"}
    assert later["samenvatting"]["dagen_oud"] > regels["tijd"]["nmap_max_dagen"]

    nessus = lees("nessus-scan.nessus")
    assert reken.toets("nessus_xml", nessus, "2026-11-01", regels)["verdicts"] == {"5.1": "stale"}


def test_document_zonder_trefwoord_of_datum(reken, regels, peildatum):
    zonder_trefwoord = reken.toets("document", "Verslag van 2026-08-01 zonder de gevraagde woorden.",
                                   peildatum, regels, "6.3")
    assert zonder_trefwoord["verdicts"] == {"6.3": "unparsed"}
    assert any("trefwoord" in f for f in zonder_trefwoord["fouten"])

    zonder_datum = reken.toets("document", "Restore getest, RTO en RPO gehaald.", peildatum, regels,
                               "6.3")
    assert zonder_datum["verdicts"] == {"6.3": "unparsed"}
    assert any("datum" in f for f in zonder_datum["fouten"])

    oud = lees("restore-test.txt")
    assert reken.toets("document", oud, "2028-01-01", regels, "6.3")["verdicts"] == {"6.3": "stale"}


def test_sysmon_stub_is_fail(reken, regels, peildatum):
    """Een config met een bekende vingerafdruk maar minder dan vijf RuleGroups is een lege huls."""
    stub = ('<?xml version="1.0"?><Sysmon schemaversion="4.90">'
            "<!-- sysmonconfig-export door SwiftOnSecurity -->"
            '<EventFiltering><RuleGroup name="een"/></EventFiltering></Sysmon>')
    assert reken.toets("sysmon_config_xml", stub, peildatum, regels)["verdicts"] == {"4.2": "fail"}

    onbekend = lees("sysmon-config.xml").replace("SwiftOnSecurity", "Eigen bouw") \
        .replace("sysmonconfig-export", "eigenconfig")
    uit = reken.toets("sysmon_config_xml", onbekend, peildatum, regels)
    assert uit["verdicts"] == {"4.2": "unparsed"}, "onbekend is niet fout, wel onbeoordeeld"


def test_firewall_drie_dialecten(reken, regels, peildatum):
    """Cisco en Palo geven op dezelfde situatie hetzelfde oordeel als FortiGate."""
    assert reken.herken_fw(lees("fortigate-config.txt")) == "fortigate"
    cisco = ("access-list jump_ilo extended permit tcp any host 10.9.0.5 eq 443 ilo\n"
             "access-list mgmt_in extended permit ip any any\n")
    uit = reken.toets("fw_config", cisco, peildatum, regels)
    assert uit["samenvatting"]["formaat"] == "cisco"
    assert uit["verdicts"]["2.1"] == "pass", "jump naar iLO gevonden"
    assert uit["verdicts"]["2.3"] == "fail", "any-any in een mgmt-acl"

    palo = ("set rulebase security rules jump-ilo from jump\n"
            "set rulebase security rules jump-ilo to ilo\n"
            "set rulebase security rules jump-ilo action allow\n")
    uit = reken.toets("fw_config", palo, peildatum, regels)
    assert uit["samenvatting"]["formaat"] == "palo"
    assert uit["verdicts"]["2.1"] == "pass"


def test_asset_inventaris_eist_alle_drie_de_bronnen(reken, regels, peildatum):
    """Ontbreekt een bron helemaal, dan is de inventaris niet vergelijkbaar: fail, geen unparsed."""
    zonder_dhcp = "source,ip\n" + "".join(f"{bron},10.0.0.{n}\n"
                                          for n in range(1, 11) for bron in ("ad", "fw_arp"))
    assert reken.toets("asset_inventory_csv", zonder_dhcp, peildatum, regels)["verdicts"] == \
        {"1.3": "fail"}


def test_vpn_verboden_subnetten(reken, regels, peildatum):
    for subnet in ("0.0.0.0/0", "::/0", "any", ""):
        uit = reken.toets("vpn_inventory_csv", f"peer,dst_subnet\np1,{subnet}\n", peildatum, regels)
        assert uit["verdicts"] == {"2.5": "fail"}, subnet


def test_east_west_telt_geen_externe_zone(reken, regels, peildatum):
    """Verkeer naar wan is geen east-west; anders zou elke internetverbinding als segmentatie tellen."""
    naar_wan = "timestamp,src_vlan,dst_vlan\n2026-09-03T09:00:00Z,user,wan\n"
    uit = reken.toets("siem_flow_csv", naar_wan, "2026-09-03", regels)
    assert uit["verdicts"]["4.1"] == "pass", "de flow is wel vers"
    assert uit["verdicts"]["4.6"] == "fail", "maar hij zegt niets over segmentatie"


def test_inactief_account_zonder_aanmelding(reken, regels, peildatum):
    """Een ingeschakeld account dat nooit inlogde, telt als inactief."""
    nooit = "upn,enabled,last_signin\nnieuw@voorbeeld.nl,true,\n"
    assert reken.toets("entra_users_csv", nooit, peildatum, regels)["verdicts"] == {"3.5": "fail"}
    uit = "upn,enabled,last_signin\nweg@voorbeeld.nl,false,\n"
    assert reken.toets("entra_users_csv", uit, peildatum, regels)["verdicts"] == {"3.5": "pass"}


# ── De vergelijking met de applicatie ────────────────────────────────────────


def posture_module(naam: str):
    pad = bronrepo(POSTURE, "security-posture-tool")
    if str(pad / "v0.1") not in sys.path:
        sys.path.insert(0, str(pad / "v0.1"))
    return importlib.import_module(f"connectors.{naam}")


def items_van_bron(regels: dict, bron: str) -> list[str]:
    """De items die deze bron meet, inclusief de items waarvoor hij het alternatief is (3.2)."""
    return [i["id"] for i in regels["items"]
            if bron in (i["bron"], i.get("bron_alternatief"))]


def verdicts_uit_applicatie(uitkomst: dict, items: list[str]) -> dict:
    if "per_item" in uitkomst:
        return {i: uitkomst["per_item"][i]["verdict"] for i in items if i in uitkomst["per_item"]}
    if "verdicts" in uitkomst:
        return {i: uitkomst["verdicts"][i] for i in items if i in uitkomst["verdicts"]}
    return {items[0]: uitkomst["verdict"]}


@pytest.mark.parametrize("bron", sorted(set(CONNECTOR_PER_BRON) - KLOKGEVOELIG - AFWIJKEND))
def test_gelijk_aan_de_applicatie(reken, regels, peildatum, bron):
    """Dezelfde export door de connector van de applicatie en door reken.py: hetzelfde oordeel."""
    module = posture_module(CONNECTOR_PER_BRON[bron])
    ruw = (FIXTURES / BESTAND_PER_BRON[bron]).read_bytes()
    items = items_van_bron(regels, bron)
    origineel = verdicts_uit_applicatie(module.parse(ruw), items)
    van_ons = reken.toets(bron, lees(BESTAND_PER_BRON[bron]), peildatum, regels)["verdicts"]
    for item_id, verdict in origineel.items():
        assert van_ons[item_id] == verdict, f"{bron} {item_id}: applicatie {verdict}"


@pytest.mark.parametrize("bron", sorted(KLOKGEVOELIG))
def test_klokgevoelige_connectors_op_de_peildatum(reken, regels, bron):
    """Deze connectors rekenden met de klok. Op de dag van de fixtures moet het oordeel gelijk zijn.

    Draait deze test later dan de peildatum, dan is de applicatie inmiddels strenger geworden en
    vergelijken we niet meer; dat verschil is precies de reden dat meting een peildatum kent.
    """
    if datetime.date.today().isoformat() != "2026-09-03":
        pytest.skip("de applicatie rekent met de klok; alleen op de peildatum vergelijkbaar")
    module = posture_module(CONNECTOR_PER_BRON[bron])
    ruw = (FIXTURES / BESTAND_PER_BRON[bron]).read_bytes()
    items = items_van_bron(regels, bron)
    origineel = verdicts_uit_applicatie(module.parse(ruw), items)
    van_ons = reken.toets(bron, lees(BESTAND_PER_BRON[bron]), "2026-09-03", regels)["verdicts"]
    for item_id, verdict in origineel.items():
        assert van_ons[item_id] == verdict, f"{bron} {item_id}"


def test_wdac_namespace_is_een_bewuste_afwijking(reken, regels, peildatum):
    """De applicatie telde nul regels in een echte WDAC-export; meting telt ze wel.

    `wdac_policy_xml.py` zoekt met `root.iter("Allow")`. Een echte SiPolicy staat in de namespace
    urn:schemas-microsoft-com:sipolicy, dus die zoekopdracht vindt niets en elke echte policy werd
    fail. Meting kijkt naar de tagnaam zonder namespace. De rest van de regel is ongewijzigd.
    """
    module = posture_module("wdac_policy_xml")
    ruw = (FIXTURES / "wdac-policy.xml").read_bytes()
    applicatie = module.parse(ruw)
    assert applicatie["verdict"] == "fail" and applicatie["rule_count"] == 0

    van_ons = reken.toets("wdac_policy_xml", lees("wdac-policy.xml"), peildatum, regels)
    assert van_ons["verdicts"] == {"7.1": "pass"}
    assert van_ons["samenvatting"]["regels"] == 1

    zonder_namespace = lees("wdac-policy.xml").replace(
        ' xmlns="urn:schemas-microsoft-com:sipolicy"', "")
    assert module.parse(zonder_namespace.encode("utf-8"))["verdict"] == "pass", \
        "zonder namespace is de applicatie het gewoon met ons eens"

    audit = zonder_namespace.replace("Enabled:Unsigned System Integrity Policy",
                                     "Enabled:Audit Mode")
    assert reken.toets("wdac_policy_xml", audit, peildatum, regels)["verdicts"] == {"7.1": "fail"}


# ── iamscan ──────────────────────────────────────────────────────────────────


def test_parse_passwd(reken):
    accounts = reken.parse_passwd("root:x:0:0:root:/root:/bin/bash\n"
                                  "# commentaar\n"
                                  "kapot:x:geen:0::/:/bin/sh\n"
                                  "deploy:x:1001:1001::/home/deploy:/bin/bash\n")
    assert [a["naam"] for a in accounts] == ["root", "deploy"]
    assert accounts[0]["uid"] == 0
    assert accounts[1]["shell"] == "/bin/bash"


def test_parse_group(reken):
    groepen = reken.parse_group("sudo:x:27:alice,bob\nleeg:x:28:\n")
    assert groepen[0]["leden"] == ["alice", "bob"]
    assert groepen[1]["leden"] == []


def test_parse_sudoers(reken):
    regels = reken.parse_sudoers(
        "Defaults env_reset\n"
        "%sudo ALL=(ALL:ALL) ALL\n"
        "deploy ALL=(root) NOPASSWD: /usr/bin/vim, /bin/systemctl restart nginx\n"
        "# commentaar\n", "etc/sudoers")
    assert len(regels) == 2
    assert regels[0]["wie"] == "%sudo"
    assert regels[0]["commandos"] == ["ALL"]
    assert regels[1]["nopasswd"] is True
    assert regels[1]["commandos"] == ["/usr/bin/vim", "/bin/systemctl restart nginx"]
    assert regels[1]["runas"] == "root"


def test_parse_authorized_keys(reken):
    sleutels = reken.parse_authorized_keys(
        'command="/usr/bin/rsync",no-pty ssh-ed25519 AAAAC3Nza deploy@bouwstraat\n'
        "ssh-rsa AAAAB3Nza\n", "deploy", "home/deploy/.ssh/authorized_keys")
    assert sleutels[0]["opties"].startswith("command=")
    assert sleutels[0]["comment"] == "deploy@bouwstraat"
    assert sleutels[1]["comment"] == "", "een sleutel zonder comment is een eigenaarloze sleutel"


def test_parse_sshd_config(reken):
    config = reken.parse_sshd_config("# kop\nPermitRootLogin yes\nPermitRootLogin no\nPort 22\n")
    assert config["permitrootlogin"] == "yes", "de eerste regel wint, als bij sshd zelf"
    assert config["port"] == "22"


def test_lees_dump_en_analyse(reken, regels, dump_map):
    hosts = reken.lees_dump(dump_map)
    assert [h["naam"] for h in hosts] == ["app01", "db01", "web01"]
    analyse = reken.analyseer(hosts, regels["iamscan"])
    assert analyse["telling"]["hoog"] > 0
    checks = {b["check"] for b in analyse["bevindingen"]}
    assert "sudo-all-nopasswd" in checks or "sudo-shell-escape" in checks
    assert analyse["routes"], "geen enkele route naar root gevonden in de voorbeelddump"
    for route in analyse["routes"]:
        assert route["principal"] != "root"


def test_ontbrekend_bronbestand_wordt_gemeld(reken, regels):
    """Afwezigheid van bewijs is geen bewijs van afwezigheid; de dump zegt wat hij niet zag."""
    analyse = reken.analyseer(reken.lees_dump({"web01/etc/passwd": "root:x:0:0::/root:/bin/bash\n"}),
                              regels["iamscan"])
    ontbreekt = [b for b in analyse["bevindingen"] if b["check"] == "bron-ontbreekt"]
    assert {b["bewijs"] for b in ontbreekt} == {"etc/group", "etc/sudoers", "etc/ssh/sshd_config"}
    assert all(b["ernst"] == "info" for b in ontbreekt)


def test_gedeelde_sleutel_over_hosts(reken, regels):
    """Dezelfde sleutel op twee accounts is een pad: identiteiten vermengen."""
    dump = {
        "a/etc/passwd": "root:x:0:0::/root:/bin/bash\n",
        "a/root/.ssh/authorized_keys": "ssh-ed25519 AAAAGEDEELD beheer@laptop\n",
        "b/etc/passwd": "deploy:x:1001:1001::/home/deploy:/bin/bash\n",
        "b/home/deploy/.ssh/authorized_keys": "ssh-ed25519 AAAAGEDEELD beheer@laptop\n",
    }
    analyse = reken.analyseer(reken.lees_dump(dump), regels["iamscan"])
    gedeeld = [b for b in analyse["bevindingen"] if b["check"] == "sleutel-meerdere-accounts"]
    assert len(gedeeld) == 1
    assert sorted(gedeeld[0]["principals"]) == ["deploy", "root"]


def test_iamscan_verdicts(reken, regels, dump_map, peildatum):
    uit = reken.toets("iamscan_dump", dump_map, peildatum, regels)
    assert set(uit["verdicts"]) == {"10.1", "10.2", "10.3", "10.4"}
    assert uit["samenvatting"]["hosts"] == 3
    assert uit["analyse"]["routes"]

    leeg = reken.toets("iamscan_dump", {}, peildatum, regels)
    assert set(leeg["verdicts"].values()) == {"unparsed"}


def test_gelijk_aan_iamscan(reken, regels, dump_map):
    """Dezelfde dump door iamscan.analysis en door reken.py: dezelfde bevindingen en routes."""
    pad = bronrepo(IAMSCAN, "iamscan")
    if str(pad) not in sys.path:
        sys.path.insert(0, str(pad))
    from iamscan.analysis import analyze  # noqa: E402
    from iamscan.parsers import load_hosts  # noqa: E402

    origineel = analyze(load_hosts(pad / "testdata" / "hosts"))
    van_ons = reken.analyseer(reken.lees_dump(dump_map), regels["iamscan"])

    per_check_origineel = {}
    for bevinding in origineel.findings:
        per_check_origineel[bevinding.check] = per_check_origineel.get(bevinding.check, 0) + 1
    per_check_van_ons = {}
    for bevinding in van_ons["bevindingen"]:
        per_check_van_ons[bevinding["check"]] = per_check_van_ons.get(bevinding["check"], 0) + 1
    assert per_check_van_ons == per_check_origineel
    assert len(van_ons["routes"]) == len(origineel.root_paths)


def test_dump_uit_tar(reken, regels, peildatum):
    """Een tar en dezelfde tar gezipt geven hetzelfde resultaat."""
    ruw = (FIXTURES / "web01-iamscan.tar").read_bytes()
    uit_tar = reken.dump_uit_tar(ruw)
    assert any(pad.endswith("etc/passwd") for pad in uit_tar)

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for naam, inhoud in sorted(uit_tar.items()):
            info = tarfile.TarInfo(naam)
            ruwe_inhoud = inhoud.encode("utf-8")
            info.size = len(ruwe_inhoud)
            tar.addfile(info, io.BytesIO(ruwe_inhoud))
    assert reken.dump_uit_tar(buffer.getvalue()) == uit_tar


# ── Van metingen naar paden ──────────────────────────────────────────────────


def test_per_chokepoint(reken, regels, paden, doorloop):
    cps = reken.per_chokepoint(regels, paden, doorloop)
    assert len(cps) == 76
    gemeten = [c for c in cps.values() if c["afgeleid"] != "geen_meting"]
    assert len(gemeten) == 22
    assert cps["AP18-1"]["items"] == [{"id": "1.1", "verdict": "pass"}]
    assert cps["AP18-1"]["afgeleid"] == "yes"
    assert cps["AP05-1"]["afgeleid"] == "no", "10.1 en 10.2 vallen om"
    assert cps["AP03-1"]["afgeleid"] == "geen_meting"


def test_afgeleid_antwoord_is_het_strengste(reken, regels, paden):
    """Een fail bij een van de items maakt het antwoord nee, ook als de rest pass is."""
    dossier = reken.nieuw_dossier(regels, paden, "2026-09-03")
    dossier["metingen"] = {
        "1.1": {"verdict": "pass"}, "1.2": {"verdict": "fail"},
    }
    cps = reken.per_chokepoint(regels, paden, dossier)
    assert cps["AP18-1"]["afgeleid"] == "yes"
    assert cps["AP18-2"]["afgeleid"] == "no"
    antwoorden = reken.afgeleide_antwoorden(regels, paden, dossier)
    assert antwoorden == {"critical": "yes", "dependencies": "no"}


def test_model_krijgt_nooit_een_afgeleid_antwoord(reken, regels, paden, doorloop):
    """AP05 vraagt naar het beheermodel; dat is een keuze, geen meting. Bewijs erbij, oordeel bij de mens."""
    antwoorden = reken.afgeleide_antwoorden(regels, paden, doorloop)
    assert "model" not in antwoorden
    cps = reken.per_chokepoint(regels, paden, doorloop)
    assert cps["AP05-1"]["vraag_id"] == "model"
    assert cps["AP05-1"]["items"], "het bewijs staat er wel"


def test_witte_vlekken(reken, regels, paden):
    vlekken = reken.witte_vlekken(regels, paden)
    assert len(vlekken) == 54
    assert all(v["bewijs"] for v in vlekken), "zeg erbij wat je zou moeten aanleveren"
    gemeten = {i["chokepoint"] for i in regels["items"] if i.get("chokepoint")}
    assert not ({v["chokepoint"] for v in vlekken} & gemeten)


def test_dashboard(reken, regels, paden, doorloop):
    stand = reken.dashboard(regels, paden, doorloop)
    assert stand["items"] == {"totaal": 41, "gemeten": 41}
    assert stand["verdict"] == {"pass": 38, "fail": 3, "stale": 0, "unparsed": 0, "geen_bewijs": 0}
    assert stand["soort"] == {"A": 32, "B": 4, "C": 5, "D": 0}
    assert stand["chokepoints"] == {"totaal": 76, "gemeten": 22, "witte_vlekken": 54}
    assert "paden" not in stand, "meting rekent geen status per pad uit (besluit 12)"

    leeg = reken.dashboard(regels, paden, reken.nieuw_dossier(regels, paden, "2026-09-03"))
    assert leeg["items"]["gemeten"] == 0
    assert leeg["verdict"]["geen_bewijs"] == 41


def test_zelfcheck_export(reken, regels, paden, doorloop, peildatum):
    uit = reken.zelfcheck_export(regels, paden, doorloop, peildatum)
    assert uit["formaat"] == "zelfcheck-antwoorden"
    assert uit["versie"] == 1
    assert uit["bron"] == "meting"
    assert uit["paden_versie"] == paden["versie"]
    assert set(uit["antwoorden"].values()) <= {"yes", "no"}
    for vraag, antwoord in uit["antwoorden"].items():
        assert vraag in uit["herkomst"], vraag
        assert uit["herkomst"][vraag]["items"], vraag
        if antwoord == "no":
            assert "fail" in uit["herkomst"][vraag]["verdicts"], vraag


def test_afgeleide_antwoorden_in_de_zelfcheck(reken, regels, paden, doorloop, peildatum):
    """De export door tools/score.py: wat zeggen deze 41 metingen over de achttien paden?

    Meting rekent zelf geen status uit (besluit 12); dit is de proef dat de export bruikbaar is.
    AP09 en AP10 worden strong omdat al hun vereiste vragen gemeten zijn en pass geven. AP05 blijft
    unknown: `model` krijgt nooit een afgeleid antwoord, en zonder dat antwoord doet score.py geen
    uitspraak. AP18 blijft unknown omdat meting twee van zijn zeven vereiste vragen raakt.
    """
    sys.path.insert(0, str(FIXTURES.parent.parent.parent))
    from tools import score  # noqa: E402

    uit = reken.zelfcheck_export(regels, paden, doorloop, peildatum)
    statussen = {k: v["status"] for k, v in score.beoordeel(paden, uit["antwoorden"]).items()}
    assert statussen["AP09"] == "strong"
    assert statussen["AP10"] == "strong"
    assert statussen["AP05"] == "unknown"
    assert statussen["AP18"] == "unknown"
    assert statussen["AP11"] == "open", "3.4 (LAPS) valt om en trekt het pad open"


# ── Dossier ──────────────────────────────────────────────────────────────────


def test_nieuw_dossier(reken, regels, paden):
    dossier = reken.nieuw_dossier(regels, paden, "2026-09-03")
    assert dossier["formaat"] == "meting-dossier"
    assert dossier["versie"] == 1
    assert dossier["regels_sha256"] == reken.vingerafdruk(regels)
    assert dossier["paden_versie"] == paden["versie"]
    assert dossier["organisatie"]["peildatum"] == "2026-09-03"
    assert dossier["metingen"] == {}


def test_slug_en_bestandsnaam(reken, regels, paden):
    assert reken.slug("Gemeente Voorbeeld") == "gemeente-voorbeeld"
    assert reken.slug("  ") == "organisatie"
    assert reken.slug("Sint-Michielsgestel/Boxtel") == "sint-michielsgestel-boxtel"
    assert len(reken.slug("x" * 80)) <= 40
    dossier = reken.nieuw_dossier(regels, paden, "2026-09-03")
    dossier["organisatie"]["naam"] = "Gemeente Voorbeeld"
    assert reken.bestandsnaam(dossier, "2026-09-03") == \
        "meting-dossier-gemeente-voorbeeld-2026-09-03.json"


def test_verdict_van(reken, regels, paden):
    dossier = reken.nieuw_dossier(regels, paden, "2026-09-03")
    assert reken.verdict_van(dossier, "1.1") == "geen_bewijs"
    dossier["metingen"]["1.1"] = {"verdict": "pass"}
    assert reken.verdict_van(dossier, "1.1") == "pass"


def test_dossier_is_json(reken, doorloop):
    """Het dossier moet zonder verlies door JSON kunnen; anders is opslaan en laden niet gelijk."""
    heen = json.dumps(doorloop, ensure_ascii=False)
    assert json.loads(heen) == doorloop
