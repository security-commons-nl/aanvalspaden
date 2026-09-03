#!/usr/bin/env python3
"""Eenmalige overname: van security-posture-tool en iamscan naar meting/regels.json.

De 37 checklistitems en hun koppeling aan pad en chokepoint komen uit de posture-tool op tag
`v0-applicatie`; de vier iamscan-items en hun constanten uit iamscan op dezelfde tag. Wat dit script
zelf toevoegt, staat hieronder als tabel: per item de bron waar het bewijs uit komt, de bewijssoort en
de toetsregel met zijn drempels. Die tabellen zijn met de hand gemaakt uit de 26 connectors; bij elke
regel staat waar hij vandaan komt.

Dit script draait niet in CI: de twee bronrepo's worden gearchiveerd zodra meting live is. Het staat er
als documentatie van de herkomst en om de overname te kunnen herhalen zolang de repo's er nog zijn.

Aanroep (met de bronrepo's als buurmappen van deze repo):
    python meting/overname.py            schrijft meting/regels.json
    python meting/overname.py --check     faalt als regels.json afwijkt van wat dit script maakt

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import importlib
import json
import pathlib
import subprocess
import sys
import tempfile

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent
DOEL = HIER / "regels.json"
TAG = "v0-applicatie"
POSTURE = REPO.parent / "security-posture-tool"
IAMSCAN = REPO.parent / "iamscan"

VERSIE = "2026-09"

# ── Wat dit script toevoegt aan de items uit checklist.py ────────────────────
#
# Per item: de bron (een record in BRONNEN), de bewijssoort en de toetsregel. De regel is data: het type
# zegt welke soort toets het is, de parameters dragen de drempels. `reken.py` heeft per bron een
# `toets_`-functie die deze parameters gebruikt; een drempel wijzigen is daarmee een wijziging in dit
# bestand, niet in code.
#
# Herkomst per regel staat in `uitleg`, met het connectorbestand erbij.

ITEM_EXTRA: dict[str, dict] = {
    "1.1": {"bron": "crown_jewels_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"velden": ["name", "owner"], "minimaal_een_rij": True},
        "uitleg": "Elke rij met een naam heeft ook een eigenaar, en er is minstens een rij "
                  "(crown_jewels_csv.py)."}},
    "1.2": {"bron": "crown_jewels_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"velden": ["vlan_or_subnet", "backup_type", "rto", "rpo"],
                                          "minimaal_een_rij": True},
        "uitleg": "Elke rij met een naam heeft alle vier de detailkolommen gevuld (crown_jewels_csv.py)."}},
    "1.3": {"bron": "asset_inventory_csv", "soort": "A", "regel": {
        "type": "spreiding", "parameters": {"bronnen": ["ad", "dhcp", "fw_arp"], "minimaal_pct_multi": 90,
                                            "maximale_spreiding_pct": 20},
        "uitleg": "Minstens 90 procent van de unieke ip-adressen komt in twee of meer bronnen voor, elke "
                  "bron heeft rijen, en de bronomvangen lopen hoogstens 20 procent uiteen "
                  "(asset_inventory.py)."}},
    "2.1": {"bron": "fw_config", "soort": "A", "regel": {
        "type": "firewall", "parameters": {"kenmerk": "jump_naar_ilo", "verwacht": True},
        "uitleg": "Er bestaat een regel van een jump-zone naar een iLO- of IPMI-zone "
                  "(fortigate_config.py, cisco_running_config.py, palo_config.py)."}},
    "2.2": {"bron": "fw_config", "soort": "A", "regel": {
        "type": "firewall", "parameters": {"kenmerk": "directe_rdp_user_naar_server", "verwacht": False},
        "uitleg": "Geen accept-regel van een user-zone naar een server-zone met rdp of poort 3389."}},
    "2.3": {"bron": "fw_config", "soort": "A", "regel": {
        "type": "firewall", "parameters": {"kenmerk": "any_any_in_mgmt", "verwacht": False},
        "uitleg": "Geen accept met bron en doel 'all' in een zone met mgmt, oob, tooling of aaa."}},
    "2.4": {"bron": "fw_config", "soort": "A", "regel": {
        "type": "firewall", "parameters": {"kenmerk": "guest_naar_internal", "verwacht": False},
        "uitleg": "Geen accept van een guest-zone naar een interne zone."}},
    "2.5": {"bron": "vpn_inventory_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"voorwaarde": "dst_subnet_niet_open", "minimaal_een_rij": True},
        "uitleg": "Elke peer heeft een dst_subnet dat gevuld is en niet 0.0.0.0/0 (vpn_inventory_csv.py)."}},
    "3.1": {"bron": "entra_privileged_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"waar_veld": "mfa_registered", "minimaal_een_rij": True},
        "uitleg": "Elk privileged account heeft MFA geregistreerd. In de applicatie kwam dit uit "
                  "fetch_privileged_accounts en fetch_mfa_registrations (entra.py, item 3.1)."}},
    "3.2": {"bron": "ad_tier0_csv", "bron_alternatief": "gpo_export_xml", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"waar_veld": "logon_workstations_set", "minimaal_een_rij": True},
        "uitleg": "Elk tier-0-account heeft LogonWorkstations gezet (ad_tier0_csv.py); via een "
                  "GPO-export telt het kenmerk LogonWorkstations (gpo_export_xml.py)."}},
    "3.3": {"bron": "ad_svc_accounts_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"voorwaarde": "gmsa_of_lang_wachtwoord", "minimale_lengte": 25,
                                          "geen_in_da": True, "minimaal_een_rij": True},
        "uitleg": "Elk serviceaccount staat buiten Domain Admins en gebruikt gMSA of een wachtwoord van "
                  "minstens 25 tekens; nul accounts in DA (ad_svc_accounts_csv.py)."}},
    "3.4": {"bron": "laps_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"waar_veld": "laps_configured", "minimaal_een_rij": True},
        "uitleg": "Elk apparaat heeft LAPS ingericht (laps_csv.py)."}},
    "3.5": {"bron": "entra_users_csv", "soort": "A", "regel": {
        "type": "geen_rij", "parameters": {"voorwaarde": "actief_en_lang_niet_ingelogd", "dagen": 90},
        "uitleg": "Geen enkel account is nog ingeschakeld terwijl het langer dan 90 dagen niet is "
                  "gebruikt. In de applicatie was dit db.fetch_inactive_accounts(90) (entra.py, 3.5)."}},
    "4.1": {"bron": "siem_flow_csv", "soort": "B", "regel": {
        "type": "drempel", "parameters": {"tellen": "rijen_in_venster", "venster_uren": 24, "minimaal": 1},
        "uitleg": "Minstens een flow-regel in de 24 uur voor de peildatum (siem_flow_csv.py)."}},
    "4.2": {"bron": "sysmon_config_xml", "soort": "A", "regel": {
        "type": "aanwezig", "parameters": {"kenmerk": "bekende_vingerafdruk", "minimaal_rulegroups": 5},
        "uitleg": "De config draagt een herkenbare vingerafdruk (SwiftOnSecurity, sysmon-modular of Hartong) "
                  "en heeft minstens vijf RuleGroups; minder is een lege stub en dus fail, een onbekende "
                  "config met genoeg groepen is unparsed (sysmon_config_xml.py)."}},
    "4.3": {"bron": "entra_risky_csv", "soort": "B", "regel": {
        "type": "geen_rij", "parameters": {"voorwaarde": "risico_in_venster", "venster_dagen": 7},
        "uitleg": "Geen sign-in met een risiconiveau anders dan none in de zeven dagen voor de "
                  "peildatum (entra.py, item 4.3: fetch_risky_signins(window_days=7))."}},
    "4.4": {"bron": "fw_flow_csv", "soort": "B", "regel": {
        "type": "drempel_pct", "parameters": {"veld": "fqdn", "minimaal_pct": 95},
        "uitleg": "Minstens 95 procent van de flow-regels heeft een fqdn (fw_flow_csv.py)."}},
    "4.5": {"bron": "siem_rules_json", "soort": "A", "regel": {
        "type": "drempel", "parameters": {"tellen": "regels_met_tag", "tag": "gemeente", "minimaal": 10},
        "uitleg": "Minstens tien detectieregels dragen een tag die 'gemeente' bevat (siem_rules_json.py)."}},
    "4.6": {"bron": "siem_flow_csv", "soort": "B", "regel": {
        "type": "drempel", "parameters": {"tellen": "east_west_flows", "minimaal": 1,
                                          "externe_zones": ["wan", "internet", "external", "", "any"]},
        "uitleg": "Minstens een flow tussen twee verschillende interne vlans (siem_flow_csv.py)."}},
    "5.1": {"bron": "nessus_xml", "soort": "A", "regel": {
        "type": "geen_bevinding", "parameters": {"severity": 4, "stale_na_dagen": 14},
        "uitleg": "Nul bevindingen met severity 4; een scan ouder dan 14 dagen is stale (nessus_xml.py)."}},
    "5.2": {"bron": "edge_devices_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"voorwaarde": "gepatcht_binnen", "maximale_uren": 72,
                                          "minimaal_een_rij": True},
        "uitleg": "Elk edge- of VPN-apparaat is binnen 72 uur voor de peildatum gepatcht "
                  "(edge_devices_csv.py)."}},
    "5.3": {"bron": "eol_inventory_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"velden": ["migration_date"], "minimaal_een_rij": True},
        "uitleg": "Elk end-of-life-systeem heeft een migratiedatum (eol_inventory_csv.py)."}},
    "5.4": {"bron": "nmap_xml", "soort": "A", "regel": {
        "type": "datum", "parameters": {"maximale_dagen": 7, "minimaal_een_host": True},
        "uitleg": "De scan is hoogstens zeven dagen oud en bevat hosts; ouder is stale (nmap_xml.py)."}},
    "6.1": {"bron": "veeam_report_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"voorwaarde": "immutable_zonder_fouten", "maximale_uren": 24,
                                          "minimaal_een_rij": True},
        "uitleg": "Elke job is onveranderbaar, foutloos en binnen 24 uur voor de peildatum geslaagd "
                  "(veeam_report.py)."}},
    "6.2": {"bron": "backup_ad_audit_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"onwaar_veld": "prod_ad_trust", "minimaal_een_rij": True},
        "uitleg": "Geen enkel backupsysteem vertrouwt het productie-AD (backup_ad_audit_csv.py)."}},
    "6.3": {"bron": "document", "soort": "C", "regel": {
        "type": "document", "parameters": {"trefwoorden": ["restore", "rto", "rpo"], "maximale_maanden": 12,
                                           "parser": "shallow_restoretest_v1"},
        "uitleg": "Rapport met de trefwoorden en een datum binnen twaalf maanden (app.py, PDF-regels)."}},
    "7.1": {"bron": "wdac_policy_xml", "soort": "A", "regel": {
        "type": "aanwezig", "parameters": {"kenmerk": "enforce_met_regels"},
        "uitleg": "WDAC staat in enforce (geen audit-optie) met minstens een regel, of AppLocker heeft "
                  "EnforcementMode Enabled met minstens een regel (wdac_policy_xml.py)."}},
    "7.2": {"bron": "asr_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"waar_veld": "asr_office_macros_blocked", "minimaal_een_rij": True},
        "uitleg": "Op elk apparaat zijn Office-macro's uit internetbestanden geblokkeerd (asr_csv.py)."}},
    "7.3": {"bron": "local_admins_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"nul_veld": "user_count_in_admins", "minimaal_een_rij": True},
        "uitleg": "Op elk apparaat staan nul gebruikers in de lokale Administrators (local_admins_csv.py)."}},
    "7.4": {"bron": "intune_usb_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"waar_veld": "usb_blocked_default", "minimaal_een_rij": True},
        "uitleg": "Op elk apparaat staat USB standaard geblokkeerd (intune_usb_csv.py)."}},
    "8.1": {"bron": "entra_admins_csv", "soort": "A", "regel": {
        "type": "dekking", "parameters": {"voorwaarde": "phishingbestendige_methode", "minimaal_een_rij": True,
                                          "methoden": ["fido2", "windowshelloforbusiness", "x509certificate"]},
        "uitleg": "Elke beheerder heeft een phishingbestendige methode. In de applicatie was dat "
                  "PHISHING_RESISTANT_TYPES uit entra.py: fido2, Windows Hello for Business en "
                  "x509-certificaat (item 8.1)."}},
    "8.2": {"bron": "siem_behavior_rules_json", "soort": "A", "regel": {
        "type": "drempel", "parameters": {"tellen": "regels_met_type", "waarde": "behavior", "minimaal": 3},
        "uitleg": "Minstens drie detectieregels van het type behavior (siem_behavior_rules_json.py)."}},
    "8.3": {"bron": "document", "soort": "C", "regel": {
        "type": "document", "parameters": {"trefwoorden": ["scenario", "respons", "verbeter|lessons"],
                                           "maximale_maanden": 6, "parser": "shallow_tabletop_v1"},
        "uitleg": "Verslag met de trefwoorden en een datum binnen zes maanden (app.py, PDF-regels)."}},
    "8.4": {"bron": "fw_category_csv", "soort": "A", "regel": {
        "type": "drempel", "parameters": {"tellen": "ai_categorie_gelogd", "minimaal": 1},
        "uitleg": "Minstens een categorieregel met 'ai' in de naam staat aan en wordt gelogd "
                  "(fw_category_csv.py)."}},
    "9.1": {"bron": "document", "soort": "C", "regel": {
        "type": "document", "parameters": {"trefwoorden": ["patch", "mfa", "incident"],
                                           "maximale_maanden": 1, "parser": "shallow_kpi_v1"},
        "uitleg": "Rapport met de trefwoorden en een datum binnen een maand (app.py, PDF-regels)."}},
    "9.2": {"bron": "document", "soort": "C", "regel": {
        "type": "document", "parameters": {"trefwoorden": ["bio\\s*2", "gap", "remediat|aanbeveling"],
                                           "maximale_maanden": 12, "parser": "shallow_bio2_v1"},
        "uitleg": "Rapport met de trefwoorden en een datum binnen twaalf maanden (app.py, PDF-regels)."}},
    "9.3": {"bron": "document", "soort": "C", "regel": {
        "type": "document", "parameters": {"trefwoorden": ["scope", "finding|bevinding", "cvss|severity|risico"],
                                           "maximale_maanden": 12, "parser": "shallow_pentest_v1"},
        "uitleg": "Rapport met de trefwoorden en een datum binnen twaalf maanden (app.py, PDF-regels)."}},
}

# De vier items die uit iamscan komen. Nieuw ten opzichte van de posture-tool; de koppeling aan een
# chokepoint is een keuze van dit plan, met de reden erbij. De checks zijn de namen uit
# iamscan/analysis.py.
IAMSCAN_ITEMS: list[dict] = [
    {"id": "10.1", "categorie": 10, "label": "Geen tweede root en geen sudo ALL zonder wachtwoord",
     "doel": "0 accounts met UID 0 naast root; 0 regels met ALL en NOPASSWD",
     "bron": "iamscan_dump", "soort": "A", "pad": "AP05", "chokepoint": "AP05-1", "kill_chain": [],
     "regel": {"type": "iamscan", "parameters": {"checks": ["uid0-naast-root", "sudo-all-nopasswd"]},
               "uitleg": "Een tweede root en volledige rootrechten zonder wachtwoord zijn precies het "
                         "tegendeel van privileged access dat gescheiden is van dagelijks gebruik."}},
    {"id": "10.2", "categorie": 10, "label": "Geen root via shell-escape in sudo",
     "doel": "0 sudo-regels op commando's die als root een shell teruggeven",
     "bron": "iamscan_dump", "soort": "A", "pad": "AP05", "chokepoint": "AP05-1", "kill_chain": [],
     "regel": {"type": "iamscan", "parameters": {"checks": ["sudo-shell-escape"]},
               "uitleg": "Een regel die beperkt oogt maar via bijvoorbeeld vim of find volledige "
                         "rootrechten geeft, is alsnog ongescheiden beheertoegang."}},
    {"id": "10.3", "categorie": 10, "label": "SSH zonder rootlogin en zonder wachtwoorden",
     "doel": "PermitRootLogin no en PasswordAuthentication no op elke host",
     "bron": "iamscan_dump", "soort": "A", "pad": "AP11", "chokepoint": "AP11-3", "kill_chain": [],
     "regel": {"type": "iamscan", "parameters": {"checks": ["permitrootlogin", "passwordauth"]},
               "uitleg": "Directe rootlogin en wachtwoorden op SSH zijn de twee makkelijkste routes voor "
                         "laterale beweging tussen hosts."}},
    {"id": "10.4", "categorie": 10, "label": "Sleutels met eigenaar, niet gedeeld over accounts",
     "doel": "0 sleutels die meerdere accounts openen",
     "bron": "iamscan_dump", "soort": "A", "pad": "AP11", "chokepoint": "AP11-3", "kill_chain": [],
     "regel": {"type": "iamscan", "parameters": {"checks": ["sleutel-meerdere-accounts"],
                                                 "waarschuwing": ["sleutel-zonder-eigenaar",
                                                                  "sleutel-breed-rootbereik"]},
               "uitleg": "Een sleutel die meerdere accounts opent, vermengt identiteiten en maakt "
                         "laterale beweging triviaal. Een sleutel zonder comment en een sleutel met "
                         "breed rootbereik zijn een waarschuwing, geen fail."}},
]

CATEGORIE_10 = {"nummer": 10, "titel": "Linux-hosts (iamscan)"}

# ── De bronnen: wat de gebruiker aanlevert ──────────────────────────────────

# `wie` zegt wie de export kan leveren, en bepaalt daarmee de volgorde van een eerste ronde: begin met
# wat je zelf kunt trekken, dan pas de vragen aan een ander. De waarden staan in WIE_UITLEG hieronder.
WIE_UITLEG = {
    "zelf": "Zelf te trekken: een portaalexport, een eigen lijst of een eigen rapport.",
    "beheer": "Vraag aan beheer: werkplekbeheer, netwerk, de SIEM-partij of backup.",
    "afspraak": "Aparte afspraak: hiervoor draait er iets op productiehosts.",
}

#
# `kolommen` is wat de lezer eist (hoofdletterongevoelig; ontbreekt er een, dan is het verdict
# unparsed). `optioneel` gaat mee in de samenvatting maar is niet verplicht. `uitleg` staat bij de
# bron op de pagina; `hoe` zegt waar de export vandaan komt.

BRONNEN: list[dict] = [
    {"id": "crown_jewels_csv", "wie": "zelf", "titel": "Kroonjuwelenlijst", "formaat": "csv",
     "kolommen": ["name"], "optioneel": ["owner", "vlan_or_subnet", "backup_type", "rto", "rpo"],
     "uitleg": "Een regel per kroonjuweel.",
     "hoe": "Uit je eigen lijst, of uit de uitdraai van procescheck (hoofdstuk Kroonjuwelen)."},
    {"id": "asset_inventory_csv", "wie": "beheer", "titel": "Asset-inventaris uit drie bronnen", "formaat": "csv",
     "kolommen": ["source", "ip"], "optioneel": ["hostname"],
     "uitleg": "Een regel per waarneming, met in source een van ad, dhcp of fw_arp.",
     "hoe": "Drie exports achter elkaar geplakt: AD-computers, DHCP-leases en de ARP-tabel van de firewall."},
    {"id": "fw_config", "wie": "beheer", "titel": "Firewall running-config", "formaat": "tekst",
     "kolommen": [], "optioneel": [],
     "uitleg": "De configuratie zoals het apparaat hem uitschrijft. Herkent FortiGate, Cisco ASA/IOS en "
               "Palo Alto set-formaat; een ander formaat geeft unparsed.",
     "hoe": "show running-config (Cisco), show full-configuration (FortiGate) of set-export (Palo Alto). "
            "De toets kijkt naar zonenamen met mgmt, oob, tooling, aaa, guest, jump, ilo, ipmi, user en "
            "server; heten je zones anders, dan is de uitkomst unparsed en niet pass."},
    {"id": "vpn_inventory_csv", "wie": "beheer", "titel": "Vendor-VPN-peers", "formaat": "csv",
     "kolommen": ["peer", "dst_subnet"], "optioneel": ["leverancier"],
     "uitleg": "Een regel per VPN-peer met het subnet dat hij mag bereiken.",
     "hoe": "Uit de VPN-configuratie of het beheerportaal van de firewall."},
    {"id": "entra_privileged_csv", "wie": "zelf", "titel": "Privileged accounts met MFA-registratie", "formaat": "csv",
     "kolommen": ["upn", "mfa_registered"], "optioneel": ["display_name", "methods"],
     "uitleg": "Een regel per account met een directoryrol.",
     "hoe": "Entra-portaal, Rollen en beheerders, plus het rapport Authenticatiemethoden; of met Graph: "
            "/directoryRoles/{id}/members en /reports/authenticationMethods/userRegistrationDetails."},
    {"id": "ad_tier0_csv", "wie": "beheer", "titel": "Tier-0-accounts en LogonWorkstations", "formaat": "csv",
     "kolommen": ["account", "logon_workstations_set"], "optioneel": ["logon_workstations"],
     "uitleg": "Een regel per tier-0-account.",
     "hoe": "PowerShell: Get-ADUser -Filter * -Properties LogonWorkstations, gefilterd op je tier-0-OU."},
    {"id": "gpo_export_xml", "wie": "beheer", "titel": "GPO-export", "formaat": "xml",
     "kolommen": [], "optioneel": [],
     "uitleg": "Alternatief voor 3.2: de export moet LogonWorkstations bevatten.",
     "hoe": "PowerShell: Get-GPOReport -All -ReportType XML."},
    {"id": "ad_svc_accounts_csv", "wie": "beheer", "titel": "Serviceaccounts", "formaat": "csv",
     "kolommen": ["sam", "in_da", "auth_type", "pw_len"], "optioneel": ["ou"],
     "uitleg": "Een regel per serviceaccount; auth_type is gmsa of iets anders, pw_len is de "
               "wachtwoordlengte.",
     "hoe": "PowerShell over je serviceaccount-OU, aangevuld met het lidmaatschap van Domain Admins."},
    {"id": "laps_csv", "wie": "beheer", "titel": "LAPS-dekking", "formaat": "csv",
     "kolommen": ["device_name", "laps_configured"], "optioneel": ["os", "laps_last_rotation"],
     "uitleg": "Een regel per apparaat.",
     "hoe": "Intune-export of een AD-query op ms-Mcs-AdmPwdExpirationTime."},
    {"id": "entra_users_csv", "wie": "zelf", "titel": "Accounts met laatste aanmelding", "formaat": "csv",
     "kolommen": ["upn", "enabled", "last_signin"], "optioneel": ["display_name"],
     "uitleg": "Een regel per account; een lege last_signin telt als nooit aangemeld.",
     "hoe": "Entra-portaal, Gebruikers, export met de kolom Laatste aanmelding; of Graph "
            "/users?$select=userPrincipalName,accountEnabled,signInActivity."},
    {"id": "siem_flow_csv", "wie": "beheer", "titel": "Flow-logs uit de SIEM", "formaat": "csv",
     "kolommen": ["timestamp", "src_vlan", "dst_vlan"], "optioneel": ["src_ip", "dst_ip"],
     "uitleg": "Een steekproef van de flow-logs; timestamp in ISO-8601.",
     "hoe": "Een query op je SIEM over de laatste 24 uur, geexporteerd als CSV."},
    {"id": "sysmon_config_xml", "wie": "beheer", "titel": "Sysmon-configuratie", "formaat": "xml",
     "kolommen": [], "optioneel": [],
     "uitleg": "De actieve Sysmon-config.",
     "hoe": "sysmon -c op een werkplek of domeincontroller."},
    {"id": "entra_risky_csv", "wie": "zelf", "titel": "Riskante aanmeldingen", "formaat": "csv",
     "kolommen": ["user", "risk_level", "datum"], "optioneel": ["risk_state", "ip"],
     "uitleg": "Een regel per aanmelding met een risiconiveau; risk_level none telt niet mee.",
     "hoe": "Entra-portaal, Beveiliging, Riskante aanmeldingen, export; of Graph /auditLogs/signIns met "
            "filter riskLevelAggregated ne 'none'."},
    {"id": "fw_flow_csv", "wie": "beheer", "titel": "Egress-flows met FQDN", "formaat": "csv",
     "kolommen": ["fqdn"], "optioneel": ["timestamp", "src_ip", "dst_ip"],
     "uitleg": "Een steekproef van uitgaand verkeer.",
     "hoe": "Export uit de firewall of proxy over een representatief venster."},
    {"id": "siem_rules_json", "wie": "beheer", "titel": "Detectieregels", "formaat": "json",
     "kolommen": [], "optioneel": [],
     "uitleg": "Een lijst met regels, of een object met een sleutel rules; elke regel heeft tags.",
     "hoe": "Export van je SIEM-regels."},
    {"id": "nessus_xml", "wie": "beheer", "titel": "Kwetsbaarhedenscan", "formaat": "xml",
     "kolommen": [], "optioneel": [],
     "uitleg": "Een .nessus-bestand; severity 4 is critical.",
     "hoe": "Nessus of Qualys, export als XML."},
    {"id": "edge_devices_csv", "wie": "zelf", "titel": "Edge- en VPN-apparaten", "formaat": "csv",
     "kolommen": ["device", "last_patched_at"], "optioneel": ["type", "versie"],
     "uitleg": "Een regel per apparaat aan de rand; last_patched_at in ISO-8601.",
     "hoe": "Uit je patchbeheer of met de hand bijgehouden."},
    {"id": "eol_inventory_csv", "wie": "zelf", "titel": "End-of-life-systemen", "formaat": "csv",
     "kolommen": ["system", "eol_date", "migration_date"], "optioneel": ["eigenaar"],
     "uitleg": "Een regel per systeem dat uit ondersteuning loopt.",
     "hoe": "Uit je eigen lijst; migration_date is de datum waarop de migratie staat gepland."},
    {"id": "nmap_xml", "wie": "beheer", "titel": "Externe poortscan", "formaat": "xml",
     "kolommen": [], "optioneel": [],
     "uitleg": "Een nmap-XML met het attribuut start op de wortel.",
     "hoe": "nmap -oX van je externe adresruimte."},
    {"id": "veeam_report_csv", "wie": "beheer", "titel": "Backuprapport", "formaat": "csv",
     "kolommen": ["job_name", "last_success", "immutable", "errors"], "optioneel": ["repository"],
     "uitleg": "Een regel per backupjob.",
     "hoe": "Export uit Veeam, Rubrik of je eigen backupsoftware."},
    {"id": "backup_ad_audit_csv", "wie": "zelf", "titel": "Backup en het productie-AD", "formaat": "csv",
     "kolommen": ["backup_system", "prod_ad_trust"], "optioneel": ["eigen_ad", "mfa"],
     "uitleg": "Een regel per backupsysteem.",
     "hoe": "Met de hand vastgesteld: vertrouwt dit systeem het productie-AD voor authenticatie?"},
    {"id": "document", "wie": "zelf", "titel": "Rapport of verslag", "formaat": "tekst",
     "kolommen": [], "optioneel": [],
     "uitleg": "Plak de tekst van het rapport. De toets kijkt of de trefwoorden voorkomen en of er een "
               "datum in staat die vers genoeg is. Wat er inhoudelijk staat, beoordeel je zelf.",
     "hoe": "Uit een PDF of Word: alles selecteren en plakken. De eerste datum in de vorm 2026-03-12 of "
            "2026/03/12 telt als datum van het rapport."},
    {"id": "wdac_policy_xml", "wie": "beheer", "titel": "WDAC- of AppLocker-policy", "formaat": "xml",
     "kolommen": [], "optioneel": [],
     "uitleg": "De actieve policy.",
     "hoe": "De XML uit je WDAC-beheer, of Get-AppLockerPolicy -Effective -Xml."},
    {"id": "asr_csv", "wie": "beheer", "titel": "ASR-regel voor Office-macro's", "formaat": "csv",
     "kolommen": ["device_name", "asr_office_macros_blocked"], "optioneel": ["os"],
     "uitleg": "Een regel per apparaat.",
     "hoe": "Intune-export van de ASR-regels."},
    {"id": "local_admins_csv", "wie": "beheer", "titel": "Lokale administrators", "formaat": "csv",
     "kolommen": ["device", "user_count_in_admins"], "optioneel": ["members"],
     "uitleg": "Een regel per apparaat met het aantal gewone gebruikers in de lokale Administrators.",
     "hoe": "Intune of een script over je werkplekken."},
    {"id": "intune_usb_csv", "wie": "beheer", "titel": "USB-beleid", "formaat": "csv",
     "kolommen": ["device", "usb_blocked_default"], "optioneel": ["policy"],
     "uitleg": "Een regel per apparaat.",
     "hoe": "Intune-export van het apparaatbeperkingsprofiel."},
    {"id": "entra_admins_csv", "wie": "zelf", "titel": "Beheerders en hun authenticatiemethoden", "formaat": "csv",
     "kolommen": ["upn", "auth_methods"], "optioneel": ["role"],
     "uitleg": "Een regel per beheerder; auth_methods is een lijst gescheiden door komma's of "
               "puntkomma's.",
     "hoe": "Graph /users/{id}/authentication/methods per beheerder, of het rapport "
            "Authenticatiemethoden uit het Entra-portaal."},
    {"id": "siem_behavior_rules_json", "wie": "beheer", "titel": "Gedragsdetectieregels", "formaat": "json",
     "kolommen": [], "optioneel": [],
     "uitleg": "Een lijst met regels; elke regel heeft een type.",
     "hoe": "Export van je SIEM-regels, gefilterd of ongefilterd."},
    {"id": "fw_category_csv", "wie": "beheer", "titel": "Categorieregels van de firewall", "formaat": "csv",
     "kolommen": ["category", "action", "logged"], "optioneel": ["policy"],
     "uitleg": "Een regel per categorie; de toets zoekt een categorie met 'ai' in de naam.",
     "hoe": "Export van het URL- of applicatiefilter."},
    {"id": "iamscan_dump", "wie": "afspraak", "titel": "Linux-dump (iamscan)", "formaat": "tar.gz of map",
     "kolommen": [], "optioneel": [],
     "uitleg": "De tarball van collect.sh, of een uitgepakte map met een submap per host. Gelezen "
               "worden: etc/passwd, etc/group, etc/sudoers, etc/sudoers.d/*, etc/ssh/sshd_config en de "
               "authorized_keys per home-directory. Ontbrekende bestanden worden gemeld, niet verzwegen.",
     "hoe": "Draai collect.sh als root op elke host (leest alleen, verstuurt niets) en kies de tarballs "
            "hier. Het script staat in de gearchiveerde repo iamscan en in meting/collect.sh."},
]

TIJD = {
    "nmap_max_dagen": 7, "nessus_stale_dagen": 14, "edge_max_uren": 72, "veeam_max_uren": 24,
    "siem_flow_venster_uren": 24, "inactief_dagen": 90, "risky_venster_dagen": 7,
    "document_dagen_per_maand": 31,
}

SOORTEN = {
    "A": "Configuratie of export: wat is ingesteld.",
    "B": "Log: wat er gebeurt.",
    "C": "Document: wat A en B niet raken. Je plakt de tekst; de toets kijkt naar trefwoorden en datum.",
    "D": "Niet uit data te halen. Dat zegt het instrument hardop; zie de witte vlekken per pad.",
}

VERDICTS = ["pass", "fail", "stale", "unparsed", "geen_bewijs"]


def uit_tag(repo: pathlib.Path, pad: str) -> str:
    """Een bestand op tag v0-applicatie uit een buurrepo, met genormaliseerde regeleindes."""
    if not (repo / ".git").exists():
        sys.exit(f"{repo} staat niet naast deze repo; overname kan alleen met de bronrepo's ernaast.")
    uit = subprocess.run(["git", "show", f"{TAG}:{pad}"], cwd=repo, capture_output=True)
    if uit.returncode != 0:
        sys.exit(f"kan {pad} niet lezen op tag {TAG} in {repo.name}: "
                 f"{uit.stderr.decode('utf-8', 'replace').strip()}")
    return uit.stdout.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def posture_items() -> tuple[list[dict], dict[str, str], list[dict]]:
    """ALL_ITEMS en de koppeling uit de posture-tool op de tag, als losse module ingeladen."""
    with tempfile.TemporaryDirectory() as tmp:
        map_ = pathlib.Path(tmp)
        for naam in ("checklist.py", "paden_map.py"):
            (map_ / naam).write_text(uit_tag(POSTURE, f"v0.1/{naam}"), encoding="utf-8")
        sys.path.insert(0, str(map_))
        for naam in ("paden_map", "checklist"):
            sys.modules.pop(naam, None)
        paden_map = importlib.import_module("paden_map")
        checklist = importlib.import_module("checklist")
        items = [dict(i) for i in checklist.ALL_ITEMS]
        ongekoppeld = dict(paden_map.ONGEKOPPELD_MET_REDEN)
        categorieen = []
        for item in items:
            nummer, titel = item["category"].split(" ", 1)
            paar = {"nummer": int(nummer), "titel": titel}
            if paar not in categorieen:
                categorieen.append(paar)
        for naam in ("paden_map", "checklist"):
            sys.modules.pop(naam, None)
        sys.path.remove(str(map_))
    return items, ongekoppeld, categorieen


def iamscan_constanten() -> dict:
    """De lijsten die de analyse gebruikt, uit iamscan op de tag."""
    ruimte: dict = {}
    bron = uit_tag(IAMSCAN, "iamscan/analysis.py")
    begin = bron.index("SHELL_ESCAPE = {")
    einde = bron.index("}", bron.index("ADMIN_GROUPS = {")) + 1
    exec(compile(bron[begin:einde], "analysis.py", "exec"), ruimte)
    commit = subprocess.run(["git", "rev-list", "-n", "1", TAG], cwd=IAMSCAN, capture_output=True)
    return {
        "shell_escape": sorted(ruimte["SHELL_ESCAPE"]),
        "admin_groepen": sorted(ruimte["ADMIN_GROUPS"]),
        "uid_grens_systeem": 1000,
        "bestanden": ["etc/passwd", "etc/group", "etc/sudoers", "etc/sudoers.d", "etc/ssh/sshd_config"],
        "commit": commit.stdout.decode().strip() or "onbekend",
    }


def paden_versie() -> str:
    return json.loads((REPO / "paden.json").read_text(encoding="utf-8"))["versie"]


# ── Recepten: hoe je zo'n export in de praktijk maakt ───────────────────────
#
# Per bron: waar je moet zijn, welke stappen, optioneel een query, en hoe de kolommen van de export
# heten tegenover het contract. `gecontroleerd` is de maand waarin het menupad is nagelopen; portalen
# hernoemen hun schermen, dus dat hoort erbij te staan.
#
# Alleen ingevuld waar het klopt. Een bron zonder recept toont zijn korte `hoe`; een verzonnen menupad
# is erger dan geen menupad.
RECEPTEN: dict[str, dict] = {
    "entra_users_csv": {
        "waar": "Microsoft Entra admin center > Identiteit > Gebruikers > Alle gebruikers",
        "stappen": [
            "Zet via Kolommen de kolom Laatste aanmelding aan. Die verschijnt alleen met Entra ID P1 of hoger.",
            "Kies Downloaden > gebruikers en wacht tot het CSV-bestand klaarstaat.",
            "Hernoem de drie kolommen die de meting vraagt; de rest mag blijven staan.",
        ],
        "query": {"taal": "Microsoft Graph",
                  "tekst": "GET /v1.0/users?$select=userPrincipalName,accountEnabled,signInActivity&$top=999"},
        "kolommen": {"userPrincipalName": "upn", "accountEnabled": "enabled",
                     "signInActivity.lastSignInDateTime": "last_signin"},
        "let_op": "Een account dat nooit heeft ingelogd, heeft geen laatste aanmelding. Dat telt hier als "
                  "inactief, en dat is de bedoeling: een ingeschakeld account dat nooit gebruikt is, is "
                  "precies wat je zoekt. Via Graph vraagt signInActivity de rechten AuditLog.Read.All.",
        "gecontroleerd": "2026-09",
    },
    "entra_privileged_csv": {
        "waar": "Entra > Identiteit > Rollen en beheerders, plus Beveiliging > Verificatiemethoden > "
                "Gebruikersregistratiedetails",
        "stappen": [
            "Open elke rol met beheerrechten (Globaal beheerder, Beveiligingsbeheerder, Exchange-, "
            "Intune-, Toepassingsbeheerder) en exporteer de leden.",
            "Exporteer Gebruikersregistratiedetails; daar staat per gebruiker of MFA geregistreerd is.",
            "Combineer beide op UPN tot twee kolommen: upn en mfa_registered.",
        ],
        "query": {"taal": "Microsoft Graph",
                  "tekst": "GET /v1.0/directoryRoles/{id}/members\n"
                           "GET /beta/reports/authenticationMethods/userRegistrationDetails"},
        "kolommen": {"userPrincipalName": "upn", "isMfaRegistered": "mfa_registered"},
        "let_op": "Werk je met PIM, dan staan rollen die alleen 'in aanmerking komend' zijn niet bij de "
                  "leden. Haal die apart op, anders mist je lijst juist de accounts die het gevoeligst zijn.",
        "gecontroleerd": "2026-09",
    },
    "entra_admins_csv": {
        "waar": "Entra > Beveiliging > Verificatiemethoden > Gebruikersregistratiedetails",
        "stappen": [
            "Filter op je beheerders (of exporteer alles en filter in de CSV).",
            "Exporteer en zet de geregistreerde methoden per gebruiker in een kolom auth_methods, "
            "gescheiden door een komma.",
        ],
        "query": {"taal": "Microsoft Graph",
                  "tekst": "GET /v1.0/users/{id}/authentication/methods"},
        "kolommen": {"userPrincipalName": "upn", "methodsRegistered": "auth_methods"},
        "let_op": "De meting kijkt of er een phishingbestendige methode tussen staat: fido2, "
                  "windowsHelloForBusiness of een certificaat. Een authenticator-app of sms telt hier "
                  "niet mee; dat is geen vergissing maar de eis.",
        "gecontroleerd": "2026-09",
    },
    "entra_risky_csv": {
        "waar": "Entra > Beveiliging > Identity Protection > Riskante aanmeldingen",
        "stappen": [
            "Zet het filter op de laatste 7 dagen; dat is het venster waar de meting mee rekent.",
            "Kies Downloaden > CSV.",
        ],
        "query": {"taal": "Microsoft Graph",
                  "tekst": "GET /v1.0/auditLogs/signIns?$filter=riskLevelAggregated ne 'none'"},
        "kolommen": {"userPrincipalName": "user", "riskLevelAggregated": "risk_level",
                     "createdDateTime": "datum"},
        "let_op": "Identity Protection vraagt Entra ID P2. Heb je dat niet, laat dit item dan leeg: "
                  "'nog geen bewijs' is een eerlijker antwoord dan een lege lijst die als pass telt.",
        "gecontroleerd": "2026-09",
    },
    "laps_csv": {
        "waar": "Intune > Apparaten > Windows > Lokaal beheerderswachtwoord (LAPS), of Active Directory",
        "stappen": [
            "In Intune: open de lijst met apparaten en exporteer; per apparaat zie je of LAPS actief is.",
            "In AD: draai de query hiernaast over je werkplek-OU.",
            "Lever twee kolommen: device_name en laps_configured (true of false).",
        ],
        "query": {"taal": "PowerShell",
                  "tekst": "Get-ADComputer -Filter * -SearchBase 'OU=Werkplekken,DC=voorbeeld,DC=nl' "
                           "-Properties ms-LAPS-PasswordExpirationTime |"
                           "\n  Select-Object Name, @{n='laps_configured';"
                           "e={$null -ne $_.'ms-LAPS-PasswordExpirationTime'}} | Export-Csv laps.csv"},
        "let_op": "Windows LAPS gebruikt ms-LAPS-PasswordExpirationTime; het oude Microsoft LAPS gebruikt "
                  "ms-Mcs-AdmPwdExpirationTime. Draai je nog de oude, pas dan de attribuutnaam aan.",
        "gecontroleerd": "2026-09",
    },
    "asr_csv": {
        "waar": "Intune > Eindpuntbeveiliging > Kwetsbaarheid voor aanvallen verminderen",
        "stappen": [
            "Open het profiel waarin de ASR-regels staan en ga naar Apparaatstatus.",
            "Exporteer; je krijgt per apparaat de status van het profiel.",
            "Lever device_name en asr_office_macros_blocked (true of false).",
        ],
        "let_op": "De meting vraagt naar de ingestelde stand, niet naar het aantal blokkades. Een regel die "
                  "op Audit staat, is niet geblokkeerd: die telt als false.",
        "gecontroleerd": "2026-09",
    },
    "intune_usb_csv": {
        "waar": "Intune > Apparaten > Configuratieprofielen",
        "stappen": [
            "Open het profiel met apparaatbeperkingen waarin verwisselbare opslag geregeld is.",
            "Ga naar Apparaatstatus en exporteer.",
            "Lever device en usb_blocked_default (true of false).",
        ],
        "let_op": "Het gaat om de standaardstand. Uitzonderingen per groep zijn prima, maar dan is de "
                  "standaard nog steeds geblokkeerd; anders is het antwoord false.",
        "gecontroleerd": "2026-09",
    },
    "local_admins_csv": {
        "waar": "Intune > Apparaten > Scripts en herstel, of je eigen beheerscript",
        "stappen": [
            "Draai een script over je werkplekken dat de leden van de lokale groep Administrators telt, "
            "de beheeraccounts niet meegerekend.",
            "Lever device en user_count_in_admins (een getal).",
        ],
        "query": {"taal": "PowerShell",
                  "tekst": "$leden = Get-LocalGroupMember -Group 'Administrators' |"
                           "\n  Where-Object { $_.ObjectClass -eq 'User' -and $_.Name -notmatch "
                           "'\\\\(adm-|svc-)' }"
                           "\n[pscustomobject]@{ device = $env:COMPUTERNAME; "
                           "user_count_in_admins = $leden.Count }"},
        "let_op": "Advanced Hunting in Defender heeft hier geen tabel voor: het lidmaatschap van de lokale "
                  "groep staat wel op de apparaatpagina, maar is niet te bevragen. Een script is de weg.",
        "gecontroleerd": "2026-09",
    },
    "crown_jewels_csv": {
        "waar": "Je eigen lijst, of de uitdraai van procescheck (hoofdstuk Kroonjuwelen)",
        "stappen": [
            "Neem hoogstens twintig regels: de systemen waarvan uitval of lek de organisatie echt raakt.",
            "Vul per regel minstens name en owner; de eigenaar is een functie, geen persoonsnaam.",
            "vlan_or_subnet, backup_type, rto en rpo tellen mee als je ze hebt.",
        ],
        "let_op": "Een eigenaar die 'ICT' heet, is geen eigenaar. De meting kijkt alleen of het veld gevuld "
                  "is, maar een lijst zonder echte eigenaren helpt je in een crisis niet.",
        "gecontroleerd": "2026-09",
    },
    "eol_inventory_csv": {
        "waar": "Je eigen lijst, aangevuld uit de levenscyclusinformatie van je leveranciers",
        "stappen": [
            "Zet per systeem dat uit ondersteuning loopt: system, eol_date en migration_date.",
            "migration_date is de datum waarop de migratie gepland staat; leeg betekent: nog niet gepland.",
        ],
        "let_op": "De meting toetst of er een migratiedatum staat, niet of die datum realistisch is. "
                  "Een datum in het verleden is dus pass en tegelijk een probleem.",
        "gecontroleerd": "2026-09",
    },
    "edge_devices_csv": {
        "waar": "Je patchbeheer, of een lijst die je zelf bijhoudt",
        "stappen": [
            "Neem alles wat vanaf internet bereikbaar is: firewall, VPN-concentrator, reverse proxy, "
            "mailgateway, en wat er verder aan de rand hangt.",
            "Zet per apparaat device en last_patched_at (datum of tijdstip van de laatste update).",
        ],
        "let_op": "De drempel is 72 uur. Dat is streng, en met opzet: dit is de laag waar een lek binnen "
                  "een dag wordt misbruikt.",
        "gecontroleerd": "2026-09",
    },
    "backup_ad_audit_csv": {
        "waar": "Vraag aan je backupbeheerder, en stel het samen vast",
        "stappen": [
            "Vraag per backupsysteem: authenticeert dit systeem tegen het productie-AD, of tegen een eigen "
            "directory?",
            "Zet backup_system en prod_ad_trust (true of false).",
        ],
        "let_op": "Dit is de vraag of je backup overleeft als je AD wordt overgenomen. Een 'weet ik niet' "
                  "vul je niet als false in; laat het item dan leeg staan.",
        "gecontroleerd": "2026-09",
    },
    "document": {
        "waar": "Je eigen rapporten en verslagen",
        "stappen": [
            "Open het rapport, selecteer alles en plak het in het tekstvak bij het item.",
            "Zorg dat de datum in de tekst staat in de vorm 2026-03-12 of 2026/03/12; de eerste datum in "
            "de tekst telt als datum van het rapport.",
        ],
        "let_op": "De toets kijkt of de trefwoorden voorkomen en of het rapport vers genoeg is. Wat er "
                  "inhoudelijk staat, beoordeel je zelf: 'voldoet' betekent hier aanwezig en actueel, niet goed.",
        "gecontroleerd": "2026-09",
    },
}


def bouw_regels() -> dict:
    items_bron, ongekoppeld, categorieen = posture_items()
    iam = iamscan_constanten()

    items: list[dict] = []
    for bron_item in items_bron:
        extra = ITEM_EXTRA.get(bron_item["id"])
        if extra is None:
            sys.exit(f"item {bron_item['id']} heeft geen bron en regel in ITEM_EXTRA")
        items.append({
            "id": bron_item["id"],
            "categorie": int(bron_item["category"].split(" ", 1)[0]),
            "label": bron_item["label"],
            "doel": bron_item["target"],
            "bron": extra["bron"],
            **({"bron_alternatief": extra["bron_alternatief"]} if "bron_alternatief" in extra else {}),
            "soort": extra["soort"],
            "pad": bron_item.get("pad"),
            "chokepoint": bron_item.get("chokepoint"),
            "kill_chain": list(bron_item.get("kill_chain_phases") or []),
            "regel": extra["regel"],
        })
    items.extend(IAMSCAN_ITEMS)

    bronnen: list[dict] = []
    for bron in BRONNEN:
        if bron.get("wie") not in WIE_UITLEG:
            sys.exit(f"bron {bron['id']} heeft geen geldige wie: {sorted(WIE_UITLEG)}")
        recept = RECEPTEN.get(bron["id"])
        bronnen.append({**bron, "recept": recept} if recept else dict(bron))

    onbekend_recept = set(RECEPTEN) - {b["id"] for b in BRONNEN}
    if onbekend_recept:
        sys.exit(f"recept voor een onbekende bron: {sorted(onbekend_recept)}")

    gebruikt = {i["bron"] for i in items} | {i.get("bron_alternatief") for i in items} - {None}
    onbekend = gebruikt - {b["id"] for b in BRONNEN}
    if onbekend:
        sys.exit(f"items verwijzen naar onbekende bronnen: {sorted(onbekend)}")

    return {
        "versie": VERSIE,
        "bron": {
            "items": f"security-posture-tool v0.1/checklist.py (ALL_ITEMS) en v0.1/paden_map.py op tag {TAG}",
            "toetsregels": f"security-posture-tool v0.1/connectors/*.py en v0.1/app.py op tag {TAG}, "
                           "met de bronnen en drempels vastgelegd in meting/overname.py",
            "iamscan": f"iamscan/analysis.py en parsers.py op tag {TAG}, commit {iam['commit']}",
            "paden": f"paden.json in deze repo, versie {paden_versie()}",
            "gegenereerd_door": "meting/overname.py; wijzig regels.json alleen met een bewuste commit",
        },
        "verdicts": VERDICTS,
        "soorten": SOORTEN,
        "categorieen": categorieen + [CATEGORIE_10],
        "wie": WIE_UITLEG,
        "bronnen": bronnen,
        "items": items,
        "ongekoppeld": ongekoppeld,
        "tijd": TIJD,
        "iamscan": {k: v for k, v in iam.items() if k != "commit"},
    }


def als_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def main(argv: list[str]) -> int:
    tekst = als_json(bouw_regels())
    if "--check" in argv:
        if not DOEL.is_file():
            print("regels.json ontbreekt; draai meting/overname.py")
            return 1
        if DOEL.read_text(encoding="utf-8") != tekst:
            print("regels.json wijkt af van wat overname.py maakt; draai meting/overname.py")
            return 1
        print("regels.json klopt met de bronrepo's")
        return 0
    DOEL.write_bytes(tekst.encode("utf-8"))
    data = json.loads(tekst)
    print(f"{DOEL.name}: {len(data['items'])} items, {len(data['bronnen'])} bronnen, "
          f"{len(data['categorieen'])} categorieen, {len(data['ongekoppeld'])} bewust ongekoppeld")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
