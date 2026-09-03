"""Gedeelde fixtures: de meetregels, de paden, de voorbeeldexports en een volledige doorloop.

De peildatum staat vast op 2026-09-03; de fixtures zijn daar omheen gemaakt (maak_fixtures.py rekent
met dagen_terug en uren_terug vanaf die datum). Zo blijft de uitkomst gelijk, ook over een jaar.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
METING = HIER.parent
REPO = METING.parent
FIXTURES = HIER / "fixtures"
sys.path.insert(0, str(METING))
sys.path.insert(0, str(REPO))

import reken as rekenaar  # noqa: E402

# De zelfchecktest leent deze conftest om het echte exportbestand te maken; daar heet de
# referentie reken_module. Een alias, zodat beide kanten dezelfde naam zien.
reken_module = rekenaar

PEILDATUM = "2026-09-03"
TAG = "v0-applicatie"
POSTURE = REPO.parent / "security-posture-tool"
IAMSCAN = REPO.parent / "iamscan"

# Welk voorbeeldbestand hoort bij welke bron. Eén bestand kan meer items dekken (siem-flow.csv dekt
# 4.1 en 4.6, fortigate-config.txt dekt 2.1 tot en met 2.4).
BESTAND_PER_BRON = {
    "crown_jewels_csv": "crown-jewels.csv", "asset_inventory_csv": "asset-inventaris.csv",
    "fw_config": "fortigate-config.txt", "vpn_inventory_csv": "vpn-peers.csv",
    "entra_privileged_csv": "entra-privileged.csv", "ad_tier0_csv": "ad-tier0.csv",
    "gpo_export_xml": "gpo-export.xml", "ad_svc_accounts_csv": "ad-serviceaccounts.csv",
    "laps_csv": "laps.csv", "entra_users_csv": "entra-accounts.csv",
    "siem_flow_csv": "siem-flow.csv", "sysmon_config_xml": "sysmon-config.xml",
    "entra_risky_csv": "entra-risky.csv", "fw_flow_csv": "fw-flow.csv",
    "siem_rules_json": "siem-regels.json", "nessus_xml": "nessus-scan.nessus",
    "edge_devices_csv": "edge-apparaten.csv", "eol_inventory_csv": "eol-systemen.csv",
    "nmap_xml": "nmap-extern.xml", "veeam_report_csv": "backup-rapport.csv",
    "backup_ad_audit_csv": "backup-ad.csv", "wdac_policy_xml": "wdac-policy.xml",
    "asr_csv": "intune-asr.csv", "local_admins_csv": "lokale-admins.csv",
    "intune_usb_csv": "intune-usb.csv", "entra_admins_csv": "entra-beheerders.csv",
    "siem_behavior_rules_json": "siem-gedrag.json", "fw_category_csv": "fw-categorieen.csv",
}
DOCUMENT_PER_ITEM = {"6.3": "restore-test.txt", "8.3": "tabletop.txt", "9.1": "kpi-rapport.txt",
                     "9.2": "bio2-gap.txt", "9.3": "pentest.txt"}


@pytest.fixture(scope="session")
def reken():
    return rekenaar


@pytest.fixture(scope="session")
def regels() -> dict:
    return json.loads((METING / "regels.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def paden() -> dict:
    return json.loads((REPO / "paden.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def peildatum() -> str:
    return PEILDATUM


def lees(naam: str) -> str:
    return (FIXTURES / naam).read_text(encoding="utf-8")


def doorloop_dossier(regels: dict, paden: dict) -> dict:
    """Alle 41 items gemeten met de voorbeeldexports: de doorloop waar de tests op rekenen."""
    dossier = rekenaar.nieuw_dossier(regels, paden, PEILDATUM)
    dossier["organisatie"]["naam"] = "Gemeente Voorbeeld"

    def leg_vast(bron: str, bestand: str, uit: dict) -> None:
        for item_id, verdict in uit["verdicts"].items():
            dossier["metingen"][item_id] = {
                "bron": bron, "bestand": bestand, "sha256": rekenaar.sha256_tekst(bestand),
                "gemeten": PEILDATUM, "artefact_datum": uit["artefact_datum"], "verdict": verdict,
                "samenvatting": uit["samenvatting"], "voorbeeld": uit["voorbeeld"],
                "fouten": uit["fouten"], "notitie": "",
            }

    for bron, naam in BESTAND_PER_BRON.items():
        leg_vast(bron, naam, rekenaar.toets(bron, lees(naam), PEILDATUM, regels))
    for item_id, naam in DOCUMENT_PER_ITEM.items():
        leg_vast("document", naam, rekenaar.toets("document", lees(naam), PEILDATUM, regels, item_id))
    dump = rekenaar.dump_uit_tar((FIXTURES / "web01-iamscan.tar").read_bytes())
    uit = rekenaar.toets("iamscan_dump", dump, PEILDATUM, regels)
    leg_vast("iamscan_dump", "web01-iamscan.tar", uit)
    dossier["iamscan"] = uit["analyse"]
    return dossier


@pytest.fixture(scope="session")
def doorloop(regels: dict, paden: dict) -> dict:
    return doorloop_dossier(regels, paden)


@pytest.fixture(scope="session")
def dump_map() -> dict:
    """De drie hosts uit de uitgepakte dump, als pad naar tekst."""
    wortel = FIXTURES / "iamscan-dump"
    uit = {}
    for pad in sorted(wortel.rglob("*")):
        if pad.is_file():
            uit[str(pad.relative_to(wortel)).replace("\\", "/")] = pad.read_text(encoding="utf-8")
    return uit


def bronrepo(pad: pathlib.Path, naam: str) -> pathlib.Path:
    """De bronrepo als buurmap, of de test overslaan: na archivering staat hij niet overal meer."""
    if not (pad / ".git").exists():
        pytest.skip(f"{naam} staat niet als buurmap; de vergelijking met de applicatie is overgeslagen")
    uit = subprocess.run(["git", "rev-parse", "--verify", TAG], cwd=pad, capture_output=True)
    if uit.returncode != 0:
        pytest.skip(f"tag {TAG} ontbreekt in {naam} (git fetch --tags)")
    return pad


@pytest.fixture(scope="session")
def gebouwd(tmp_path_factory) -> pathlib.Path:
    """De pagina een keer bouwen per testsessie; alle tests lezen dezelfde uitvoer."""
    import bouw as bouwer

    return bouwer.bouw(tmp_path_factory.mktemp("meting-dist"))


@pytest.fixture(scope="session")
def html(gebouwd: pathlib.Path) -> str:
    return gebouwd.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def app_js() -> str:
    return (METING / "bron" / "app.js").read_text(encoding="utf-8")
