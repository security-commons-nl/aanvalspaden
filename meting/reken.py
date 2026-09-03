#!/usr/bin/env python3
"""De rekenregels van meting: lezen, toetsen, en de uitkomst op de aanvalspaden leggen.

Dit is de referentie. `meting/bron/app.js` heeft dezelfde functies onder dezelfde namen in het object
`reken`, zodat browser en referentie hetzelfde uitrekenen en een test dat kan vergelijken.

Twee regels die overal gelden:
  1. Tijd rekent vanaf de peildatum uit het dossier, nooit vanaf de klok. Anders geeft dezelfde export
     morgen een ander verdict en is geen enkele test herhaalbaar.
  2. Afronden gaat half omhoog, nooit met round(): Python rondt 12,5 naar 12, JavaScript naar 13.

De drempels staan niet hier maar in regels.json; deze module leest ze uit `regel.parameters`. Een
drempel wijzigen is daarmee een wijziging in data, niet in code.

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import math
import pathlib
import re
import sys
import tarfile
from collections import defaultdict
from xml.etree import ElementTree

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent

# Meting rekent geen status per aanvalspad uit. Die regels wonen in tools/score.py en in de zelfcheck;
# een derde kopie zou een derde waarheid worden. Meting levert bewijs per chokepoint en een afgeleid
# antwoord per vraag, en exporteert die naar de zelfcheck. Daar staat de status.

VERDICTS = ("pass", "fail", "stale", "unparsed", "geen_bewijs")
TRUTHY = {"true", "yes", "ja", "1", "enabled", "on", "y", "t"}
FALSY = {"false", "no", "nee", "0", "disabled", "off", "n", "f"}
DATUM_PATROON = re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b")


# ── Getallen en tijd ─────────────────────────────────────────────────────────


def rond_half_omhoog(x: float) -> int:
    return int(math.floor(x + 0.5))


def procent(gedekt: int, totaal: int) -> int:
    return 0 if totaal <= 0 else rond_half_omhoog(gedekt / totaal * 100)


def lees_datum(waarde) -> datetime.datetime | None:
    """ISO-8601 met of zonder tijd en zone, of een datum in een lap tekst. None als er niets in zit."""
    if waarde is None:
        return None
    tekst = str(waarde).strip()
    if not tekst:
        return None
    kaal = tekst.replace("Z", "+00:00")
    try:
        stamp = datetime.datetime.fromisoformat(kaal)
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        pass
    treffer = DATUM_PATROON.search(tekst)
    if treffer:
        jaar, maand, dag = (int(g) for g in treffer.groups())
        try:
            return datetime.datetime(jaar, maand, dag, tzinfo=datetime.timezone.utc)
        except ValueError:
            return None
    return None


def peil(peildatum: str) -> datetime.datetime:
    """De peildatum als moment: einde van de dag, zodat een artefact van vandaag nul dagen oud is."""
    stamp = lees_datum(peildatum) or datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
    return stamp.replace(hour=23, minute=59, second=59)


def dagen_tussen(waarde, peildatum: str) -> int | None:
    stamp = lees_datum(waarde)
    return None if stamp is None else max(0, (peil(peildatum) - stamp).days)


def uren_tussen(waarde, peildatum: str) -> float | None:
    stamp = lees_datum(waarde)
    return None if stamp is None else max(0.0, (peil(peildatum) - stamp).total_seconds() / 3600)


# ── Lezen ────────────────────────────────────────────────────────────────────


def _splits_csv_regel(regel: str, scheider: str) -> list[str]:
    uit, huidig, in_aanhaling, i = [], "", False, 0
    while i < len(regel):
        teken = regel[i]
        if in_aanhaling:
            if teken == '"' and i + 1 < len(regel) and regel[i + 1] == '"':
                huidig += '"'
                i += 1
            elif teken == '"':
                in_aanhaling = False
            else:
                huidig += teken
        elif teken == '"':
            in_aanhaling = True
        elif teken == scheider:
            uit.append(huidig)
            huidig = ""
        else:
            huidig += teken
        i += 1
    uit.append(huidig)
    return uit


def lees_csv(tekst: str) -> tuple[list[str], list[dict]]:
    """(koppen, rijen). BOM weg, koppen kleine letters en gestript, puntkomma als terugval."""
    tekst = tekst.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    regels = [r for r in tekst.split("\n") if r.strip()]
    if not regels:
        return [], []
    scheider = ","
    if len(_splits_csv_regel(regels[0], ",")) == 1 and len(_splits_csv_regel(regels[0], ";")) > 1:
        scheider = ";"
    koppen = [k.strip().lstrip("﻿").lower() for k in _splits_csv_regel(regels[0], scheider)]
    rijen = []
    for regel in regels[1:]:
        cellen = _splits_csv_regel(regel, scheider)
        rijen.append({koppen[i]: (cellen[i] if i < len(cellen) else "") for i in range(len(koppen))})
    return koppen, rijen


def truthy(waarde) -> bool:
    return str(waarde or "").strip().lower() in TRUTHY


def falsy(waarde) -> bool:
    return str(waarde or "").strip().lower() in FALSY


def ontbrekende_kolommen(vereist, koppen) -> list[str]:
    return sorted(set(vereist) - set(koppen))


def dekking(rijen: list[dict], voorwaarde) -> tuple[int, int]:
    return len(rijen), sum(1 for r in rijen if voorwaarde(r))


def lees_xml(tekst: str):
    """De wortel, of None bij een parseerfout. In de browser doet DOMParser hetzelfde."""
    try:
        return ElementTree.fromstring(tekst.lstrip("﻿"))
    except ElementTree.ParseError:
        return None


def _naam(element) -> str:
    return element.tag.split("}")[-1]


def _voorbeeld(rijen: list[dict], velden: list[str], maximaal: int = 10) -> list[str]:
    uit = []
    for rij in rijen[:maximaal]:
        uit.append(" | ".join(str(rij.get(v, "")) for v in velden))
    return uit


def _uitkomst(verdicts: dict, samenvatting: dict | None = None, voorbeeld=None,
              artefact_datum=None, fouten=None) -> dict:
    return {"verdicts": verdicts, "samenvatting": samenvatting or {},
            "voorbeeld": voorbeeld or [], "artefact_datum": artefact_datum, "fouten": fouten or []}


def _unparsed(items: list[str], fouten: list[str]) -> dict:
    return _uitkomst({i: "unparsed" for i in items}, fouten=fouten)


def _param(regels: dict, item_id: str) -> dict:
    for item in regels["items"]:
        if item["id"] == item_id:
            return item["regel"]["parameters"]
    return {}


def _dekkingsuitkomst(item_id: str, totaal: int, gedekt: int, minimaal_een: bool,
                      extra: dict | None = None, voorbeeld=None) -> dict:
    if minimaal_een and totaal == 0:
        verdict = "fail"
    else:
        verdict = "pass" if gedekt == totaal else "fail"
    samenvatting = {"totaal": totaal, "gedekt": gedekt, "pct": procent(gedekt, totaal)}
    samenvatting.update(extra or {})
    return _uitkomst({item_id: verdict}, samenvatting, voorbeeld)


# ── Toetsen per bron ─────────────────────────────────────────────────────────


def toets_crown_jewels_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["name"], koppen)
    if mist:
        return _unparsed(["1.1", "1.2"], [f"kolom ontbreekt: {', '.join(mist)}"])
    genoemd = [r for r in rijen if str(r.get("name") or "").strip()]
    totaal = len(genoemd)
    met_eigenaar = sum(1 for r in genoemd if str(r.get("owner") or "").strip())
    detail = _param(regels, "1.2")["velden"]
    compleet = sum(1 for r in genoemd if all(str(r.get(c) or "").strip() for c in detail))
    verdicts = {
        "1.1": "fail" if totaal == 0 else ("pass" if met_eigenaar == totaal else "fail"),
        "1.2": "fail" if totaal == 0 else ("pass" if compleet == totaal else "fail"),
    }
    return _uitkomst(verdicts,
                     {"totaal": totaal, "met_eigenaar": met_eigenaar, "compleet": compleet,
                      "pct": procent(compleet, totaal)},
                     _voorbeeld(genoemd, ["name", "owner"]))


def toets_asset_inventory_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["source", "ip"], koppen)
    if mist:
        return _unparsed(["1.3"], [f"kolom ontbreekt: {', '.join(mist)}"])
    parameters = _param(regels, "1.3")
    verwacht = parameters["bronnen"]
    per_bron = {b: set() for b in verwacht}
    per_ip: dict[str, set] = defaultdict(set)
    for rij in rijen:
        bron = str(rij.get("source") or "").strip().lower()
        ip = str(rij.get("ip") or "").strip()
        if not bron or not ip:
            continue
        if bron in per_bron:
            per_bron[bron].add(ip)
        per_ip[ip].add(bron)
    tellingen = {b: len(ips) for b, ips in per_bron.items()}
    totaal_uniek = len(per_ip)
    in_meer = sum(1 for bronnen in per_ip.values() if len(bronnen) >= 2)
    pct_meer = procent(in_meer, totaal_uniek)
    if any(t == 0 for t in tellingen.values()):
        verdict = "fail"
    else:
        hoog, laag = max(tellingen.values()), min(tellingen.values())
        spreiding_ok = (hoog - laag) / hoog * 100 <= parameters["maximale_spreiding_pct"] if hoog else False
        verdict = "pass" if pct_meer >= parameters["minimaal_pct_multi"] and spreiding_ok else "fail"
    return _uitkomst({"1.3": verdict},
                     {"totaal": totaal_uniek, "gedekt": in_meer, "pct": pct_meer,
                      "per_bron": tellingen})


_FW_ITEMS = ["2.1", "2.2", "2.3", "2.4"]
_MGMT_WOORDEN = ("mgmt", "oob", "tooling", "aaa")


def _fw_kenmerken_fortigate(tekst: str) -> dict:
    kenmerken = {"jump_naar_ilo": False, "directe_rdp_user_naar_server": False,
                 "any_any_in_mgmt": 0, "guest_naar_internal": 0, "regels": 0}
    for blok in re.findall(r"edit\s+\d+\s*\n(.*?)\n\s*next", tekst, re.DOTALL):
        velden = {m.group(1): m.group(2).strip().strip('"').strip()
                  for m in re.finditer(r"set\s+(\S+)\s+(.+)", blok)}
        kenmerken["regels"] += 1
        src = velden.get("srcintf", "").lower()
        dst = velden.get("dstintf", "").lower()
        src_addr = [t.strip('"').lower() for t in velden.get("srcaddr", "").split()]
        dst_addr = [t.strip('"').lower() for t in velden.get("dstaddr", "").split()]
        dienst = velden.get("service", "").lower()
        actie = velden.get("action", "accept").lower()
        zones = f"{src} {dst}"
        if actie == "accept" and any(w in zones for w in _MGMT_WOORDEN) and "all" in src_addr and "all" in dst_addr:
            kenmerken["any_any_in_mgmt"] += 1
        if "guest" in src and ("internal" in dst or any("internal" in a for a in dst_addr)) and actie == "accept":
            kenmerken["guest_naar_internal"] += 1
        if "jump" in src and ("ilo" in dst or "ipmi" in dst):
            kenmerken["jump_naar_ilo"] = True
        if "user" in src and "server" in dst and ("rdp" in dienst or "3389" in dienst) and actie == "accept":
            kenmerken["directe_rdp_user_naar_server"] = True
    return kenmerken


def _fw_kenmerken_cisco(tekst: str) -> dict:
    kenmerken = {"jump_naar_ilo": False, "directe_rdp_user_naar_server": False,
                 "any_any_in_mgmt": 0, "guest_naar_internal": 0, "regels": 0}
    for treffer in re.finditer(r"access-list\s+(\S+)\s+(?:extended\s+)?(permit|deny)\s+(\S+)\s+(.+)", tekst):
        acl, actie, proto, rest = (t.lower() for t in treffer.groups())
        kenmerken["regels"] += 1
        if "mgmt" in acl and "any any" in rest and proto in ("ip", "any"):
            kenmerken["any_any_in_mgmt"] += 1
        if "guest" in acl and "any any" not in rest and actie == "permit":
            if any(t in rest for t in ("10.", "172.16.", "192.168.", "internal")):
                kenmerken["guest_naar_internal"] += 1
        if "jump" in acl and "ilo" in rest:
            kenmerken["jump_naar_ilo"] = True
        if "user" in acl and ("eq 3389" in rest or "rdp" in rest):
            kenmerken["directe_rdp_user_naar_server"] = True
    return kenmerken


def _fw_kenmerken_palo(tekst: str) -> dict:
    kenmerken = {"jump_naar_ilo": False, "directe_rdp_user_naar_server": False,
                 "any_any_in_mgmt": 0, "guest_naar_internal": 0, "regels": 0}
    regels: dict[str, dict[str, str]] = defaultdict(dict)
    for treffer in re.finditer(r"set rulebase security rules (\S+) (\S+) (.+)", tekst):
        naam, veld, waarde = treffer.groups()
        regels[naam][veld] = waarde.strip().strip("[]").strip().lower()
    for velden in regels.values():
        kenmerken["regels"] += 1
        van, naar = velden.get("from", ""), velden.get("to", "")
        bron, doel = velden.get("source", ""), velden.get("destination", "")
        dienst = velden.get("service", "") + " " + velden.get("application", "")
        actie = velden.get("action", "allow")
        zones = f"{van} {naar}"
        if actie == "allow" and any(w in zones for w in _MGMT_WOORDEN) and "any" in bron and "any" in doel:
            kenmerken["any_any_in_mgmt"] += 1
        if "guest" in van and ("internal" in naar or "internal" in doel) and actie == "allow":
            kenmerken["guest_naar_internal"] += 1
        if "jump" in van and ("ilo" in naar or "ipmi" in naar):
            kenmerken["jump_naar_ilo"] = True
        if "user" in van and "server" in naar and ("rdp" in dienst or "3389" in dienst) and actie == "allow":
            kenmerken["directe_rdp_user_naar_server"] = True
    return kenmerken


def herken_fw(tekst: str) -> str | None:
    laag = tekst.lower()
    if "config firewall policy" in laag:
        return "fortigate"
    if "access-list" in laag:
        return "cisco"
    if "set rulebase security rules" in laag:
        return "palo"
    return None


def toets_fw_config(inhoud, peildatum, regels):
    soort = herken_fw(inhoud)
    if soort is None:
        return _unparsed(_FW_ITEMS, ["formaat niet herkend; verwacht FortiGate, Cisco of Palo Alto"])
    kenmerken = {"fortigate": _fw_kenmerken_fortigate, "cisco": _fw_kenmerken_cisco,
                 "palo": _fw_kenmerken_palo}[soort](inhoud)
    verdicts = {}
    for item in _FW_ITEMS:
        parameters = _param(regels, item)
        waarde = kenmerken[parameters["kenmerk"]]
        gevonden = bool(waarde) if isinstance(waarde, bool) else waarde > 0
        verdicts[item] = "pass" if gevonden == parameters["verwacht"] else "fail"
    return _uitkomst(verdicts, {"formaat": soort, **kenmerken})


def toets_vpn_inventory_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["peer", "dst_subnet"], koppen)
    if mist:
        return _unparsed(["2.5"], [f"kolom ontbreekt: {', '.join(mist)}"])

    def scoped(rij):
        subnet = str(rij.get("dst_subnet") or "").strip()
        return bool(subnet) and subnet not in ("0.0.0.0/0", "::/0", "any")

    totaal, gedekt = dekking(rijen, scoped)
    return _dekkingsuitkomst("2.5", totaal, gedekt, True, voorbeeld=_voorbeeld(rijen, ["peer", "dst_subnet"]))


def _waar_veld(item_id, kolommen, veld, inhoud, regels, voorbeeldvelden):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(kolommen, koppen)
    if mist:
        return _unparsed([item_id], [f"kolom ontbreekt: {', '.join(mist)}"])
    totaal, gedekt = dekking(rijen, lambda r: truthy(r.get(veld)))
    return _dekkingsuitkomst(item_id, totaal, gedekt, True, voorbeeld=_voorbeeld(rijen, voorbeeldvelden))


def toets_entra_privileged_csv(inhoud, peildatum, regels):
    return _waar_veld("3.1", ["upn", "mfa_registered"], "mfa_registered", inhoud, regels,
                      ["upn", "mfa_registered"])


def toets_ad_tier0_csv(inhoud, peildatum, regels):
    return _waar_veld("3.2", ["account", "logon_workstations_set"], "logon_workstations_set", inhoud,
                      regels, ["account", "logon_workstations_set"])


def toets_gpo_export_xml(inhoud, peildatum, regels):
    wortel = lees_xml(inhoud)
    if wortel is None:
        return _unparsed(["3.2"], ["XML niet te lezen"])
    gevonden = "logonworkstations" in inhoud.lower()
    return _uitkomst({"3.2": "pass" if gevonden else "fail"},
                     {"kenmerk": "LogonWorkstations", "gevonden": gevonden})


def toets_ad_svc_accounts_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["sam", "in_da", "auth_type", "pw_len"], koppen)
    if mist:
        return _unparsed(["3.3"], [f"kolom ontbreekt: {', '.join(mist)}"])
    minimaal = _param(regels, "3.3")["minimale_lengte"]

    def goed(rij):
        if truthy(rij.get("in_da")):
            return False
        if str(rij.get("auth_type") or "").strip().lower() == "gmsa":
            return True
        try:
            return int(str(rij.get("pw_len") or 0).strip() or 0) >= minimaal
        except ValueError:
            return False

    totaal, gedekt = dekking(rijen, goed)
    in_da = sum(1 for r in rijen if truthy(r.get("in_da")))
    verdict = "pass" if totaal and gedekt == totaal and in_da == 0 else "fail"
    return _uitkomst({"3.3": verdict},
                     {"totaal": totaal, "gedekt": gedekt, "pct": procent(gedekt, totaal), "in_da": in_da},
                     _voorbeeld(rijen, ["sam", "auth_type", "pw_len"]))


def toets_laps_csv(inhoud, peildatum, regels):
    return _waar_veld("3.4", ["device_name", "laps_configured"], "laps_configured", inhoud, regels,
                      ["device_name", "laps_configured"])


def toets_entra_users_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["upn", "enabled", "last_signin"], koppen)
    if mist:
        return _unparsed(["3.5"], [f"kolom ontbreekt: {', '.join(mist)}"])
    grens = _param(regels, "3.5")["dagen"]

    def inactief(rij):
        if not truthy(rij.get("enabled")):
            return False
        dagen = dagen_tussen(rij.get("last_signin"), peildatum)
        return dagen is None or dagen > grens

    slapend = [r for r in rijen if inactief(r)]
    return _uitkomst({"3.5": "pass" if not slapend else "fail"},
                     {"totaal": len(rijen), "inactief": len(slapend), "dagen": grens},
                     _voorbeeld(slapend, ["upn", "last_signin"]))


def toets_siem_flow_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["timestamp", "src_vlan", "dst_vlan"], koppen)
    if mist:
        return _unparsed(["4.1", "4.6"], [f"kolom ontbreekt: {', '.join(mist)}"])
    venster = _param(regels, "4.1")["venster_uren"]
    extern = set(_param(regels, "4.6")["externe_zones"])
    recent = 0
    east_west = 0
    for rij in rijen:
        uren = uren_tussen(rij.get("timestamp"), peildatum)
        if uren is not None and uren <= venster:
            recent += 1
        bron = str(rij.get("src_vlan") or "").strip().lower()
        doel = str(rij.get("dst_vlan") or "").strip().lower()
        if bron and doel and bron != doel and bron not in extern and doel not in extern:
            east_west += 1
    return _uitkomst({"4.1": "pass" if recent > 0 else "fail",
                      "4.6": "pass" if east_west > 0 else "fail"},
                     {"totaal": len(rijen), "in_venster": recent, "east_west": east_west,
                      "venster_uren": venster})


_SYSMON_VINGERAFDRUKKEN = ("swiftonsecurity", "sysmon-modular", "olaf hartong", "hartong", "sysmonconfig-export")


def toets_sysmon_config_xml(inhoud, peildatum, regels):
    """Als sysmon_config_xml.py: een bekende vingerafdruk en minstens vijf RuleGroups; minder is een stub."""
    wortel = lees_xml(inhoud)
    if wortel is None:
        return _unparsed(["4.2"], ["XML niet te lezen"])
    if _naam(wortel).lower() != "sysmon":
        return _unparsed(["4.2"], ["dit is geen Sysmon-configuratie"])
    minimaal = _param(regels, "4.2")["minimaal_rulegroups"]
    groepen = sum(1 for e in wortel.iter() if _naam(e) == "RuleGroup")
    laag = inhoud.lower()
    gevonden = [v for v in _SYSMON_VINGERAFDRUKKEN if v in laag]
    if groepen < minimaal:
        verdict = "fail"
    elif gevonden:
        verdict = "pass"
    else:
        verdict = "unparsed"
    return _uitkomst({"4.2": verdict},
                     {"vingerafdruk": gevonden[0] if gevonden else None, "rulegroups": groepen,
                      "minimaal_rulegroups": minimaal},
                     fouten=[] if (gevonden or groepen < minimaal) else
                     ["onbekende configuratie; beoordeel hem zelf"])


def toets_entra_risky_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["user", "risk_level", "datum"], koppen)
    if mist:
        return _unparsed(["4.3"], [f"kolom ontbreekt: {', '.join(mist)}"])
    venster = _param(regels, "4.3")["venster_dagen"]

    def risico(rij):
        niveau = str(rij.get("risk_level") or "").strip().lower()
        if niveau in ("", "none"):
            return False
        dagen = dagen_tussen(rij.get("datum"), peildatum)
        return dagen is not None and dagen <= venster

    risky = [r for r in rijen if risico(r)]
    return _uitkomst({"4.3": "pass" if not risky else "fail"},
                     {"totaal": len(rijen), "risky": len(risky), "venster_dagen": venster},
                     _voorbeeld(risky, ["user", "risk_level", "datum"]))


def toets_fw_flow_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["fqdn"], koppen)
    if mist:
        return _unparsed(["4.4"], [f"kolom ontbreekt: {', '.join(mist)}"])
    drempel = _param(regels, "4.4")["minimaal_pct"]
    totaal, gedekt = dekking(rijen, lambda r: bool(str(r.get("fqdn") or "").strip()))
    pct = procent(gedekt, totaal)
    verdict = "pass" if totaal > 0 and pct >= drempel else "fail"
    return _uitkomst({"4.4": verdict},
                     {"totaal": totaal, "gedekt": gedekt, "pct": pct, "drempel_pct": drempel})


def _json_lijst(inhoud: str, sleutel: str):
    try:
        data = json.loads(inhoud.lstrip("﻿"))
    except (json.JSONDecodeError, TypeError) as fout:
        return None, f"JSON niet te lezen: {fout}"
    lijst = data if isinstance(data, list) else data.get(sleutel)
    if not isinstance(lijst, list):
        return None, f"verwacht een lijst of een object met de sleutel {sleutel}"
    return lijst, None


def toets_siem_rules_json(inhoud, peildatum, regels):
    lijst, fout = _json_lijst(inhoud, "rules")
    if lijst is None:
        return _unparsed(["4.5"], [fout])
    parameters = _param(regels, "4.5")
    tag = parameters["tag"].lower()
    treffers = [r.get("id") or r.get("name") or "?" for r in lijst
                if isinstance(r, dict) and any(tag in str(t).lower() for t in (r.get("tags") or []))]
    verdict = "pass" if len(treffers) >= parameters["minimaal"] else "fail"
    return _uitkomst({"4.5": verdict},
                     {"totaal": len(lijst), "gedekt": len(treffers), "drempel": parameters["minimaal"]},
                     [str(t) for t in treffers[:10]])


def toets_siem_behavior_rules_json(inhoud, peildatum, regels):
    lijst, fout = _json_lijst(inhoud, "rules")
    if lijst is None:
        return _unparsed(["8.2"], [fout])
    parameters = _param(regels, "8.2")
    treffers = [r.get("id") or r.get("name") or "?" for r in lijst
                if isinstance(r, dict) and str(r.get("type") or "").lower() == parameters["waarde"]]
    verdict = "pass" if len(treffers) >= parameters["minimaal"] else "fail"
    return _uitkomst({"8.2": verdict},
                     {"totaal": len(lijst), "gedekt": len(treffers), "drempel": parameters["minimaal"]},
                     [str(t) for t in treffers[:10]])


def toets_nessus_xml(inhoud, peildatum, regels):
    wortel = lees_xml(inhoud)
    if wortel is None:
        return _unparsed(["5.1"], ["XML niet te lezen"])
    parameters = _param(regels, "5.1")
    kritiek = []
    scan_datum = None
    for item in wortel.iter():
        if _naam(item) == "ReportItem" and str(item.attrib.get("severity")) == str(parameters["severity"]):
            kritiek.append(item.attrib.get("pluginName") or item.attrib.get("port") or "?")
        if _naam(item) == "tag" and item.attrib.get("name") in ("HOST_START", "HOST_END"):
            scan_datum = scan_datum or lees_datum(item.text)
    dagen = dagen_tussen(scan_datum.isoformat() if scan_datum else None, peildatum)
    if dagen is not None and dagen > parameters["stale_na_dagen"]:
        verdict = "stale"
    else:
        verdict = "pass" if not kritiek else "fail"
    return _uitkomst({"5.1": verdict},
                     {"kritiek": len(kritiek), "dagen_oud": dagen,
                      "stale_na_dagen": parameters["stale_na_dagen"]},
                     [str(k) for k in kritiek[:10]],
                     scan_datum.isoformat() if scan_datum else None)


def toets_edge_devices_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["device", "last_patched_at"], koppen)
    if mist:
        return _unparsed(["5.2"], [f"kolom ontbreekt: {', '.join(mist)}"])
    maximaal = _param(regels, "5.2")["maximale_uren"]

    def op_tijd(rij):
        uren = uren_tussen(rij.get("last_patched_at"), peildatum)
        return uren is not None and uren <= maximaal

    totaal, gedekt = dekking(rijen, op_tijd)
    return _dekkingsuitkomst("5.2", totaal, gedekt, True, {"maximale_uren": maximaal},
                             _voorbeeld(rijen, ["device", "last_patched_at"]))


def toets_eol_inventory_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["system", "eol_date", "migration_date"], koppen)
    if mist:
        return _unparsed(["5.3"], [f"kolom ontbreekt: {', '.join(mist)}"])
    totaal, gedekt = dekking(rijen, lambda r: bool(str(r.get("migration_date") or "").strip()))
    return _dekkingsuitkomst("5.3", totaal, gedekt, True,
                             voorbeeld=_voorbeeld(rijen, ["system", "migration_date"]))


def toets_nmap_xml(inhoud, peildatum, regels):
    wortel = lees_xml(inhoud)
    if wortel is None:
        return _unparsed(["5.4"], ["XML niet te lezen"])
    parameters = _param(regels, "5.4")
    start = wortel.attrib.get("start")
    scan_datum = None
    if start and str(start).isdigit():
        scan_datum = datetime.datetime.fromtimestamp(int(start), tz=datetime.timezone.utc)
    hosts = [h for h in wortel if _naam(h) == "host"]
    open_poorten = []
    for host in hosts:
        adres = next((a.attrib.get("addr") for a in host if _naam(a) == "address"), "?")
        for poort in host.iter():
            if _naam(poort) != "port":
                continue
            staat = next((s for s in poort if _naam(s) == "state"), None)
            if staat is not None and staat.attrib.get("state") == "open":
                open_poorten.append(f"{adres}:{poort.attrib.get('portid')}")
    dagen = dagen_tussen(scan_datum.isoformat() if scan_datum else None, peildatum)
    if scan_datum is None:
        verdict = "unparsed"
    elif dagen is not None and dagen > parameters["maximale_dagen"]:
        verdict = "stale"
    else:
        verdict = "pass" if hosts else "fail"
    return _uitkomst({"5.4": verdict},
                     {"hosts": len(hosts), "open_poorten": len(open_poorten), "dagen_oud": dagen,
                      "maximale_dagen": parameters["maximale_dagen"]},
                     open_poorten[:10],
                     scan_datum.isoformat() if scan_datum else None)


def toets_veeam_report_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["job_name", "last_success", "immutable", "errors"], koppen)
    if mist:
        return _unparsed(["6.1"], [f"kolom ontbreekt: {', '.join(mist)}"])
    maximaal = _param(regels, "6.1")["maximale_uren"]

    def goed(rij):
        if not truthy(rij.get("immutable")):
            return False
        try:
            if int(str(rij.get("errors") or 0).strip() or 0) != 0:
                return False
        except ValueError:
            return False
        uren = uren_tussen(rij.get("last_success"), peildatum)
        return uren is not None and uren <= maximaal

    totaal, gedekt = dekking(rijen, goed)
    return _dekkingsuitkomst("6.1", totaal, gedekt, True, {"maximale_uren": maximaal},
                             _voorbeeld(rijen, ["job_name", "last_success", "immutable", "errors"]))


def toets_backup_ad_audit_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["backup_system", "prod_ad_trust"], koppen)
    if mist:
        return _unparsed(["6.2"], [f"kolom ontbreekt: {', '.join(mist)}"])
    totaal, gedekt = dekking(rijen, lambda r: not truthy(r.get("prod_ad_trust")))
    return _dekkingsuitkomst("6.2", totaal, gedekt, True,
                             voorbeeld=_voorbeeld(rijen, ["backup_system", "prod_ad_trust"]))


# De regeltags waar wdac_policy_xml.py op telt. Een verschil met de applicatie staat in
# verantwoording.md: zij telde met root.iter("Allow"), en dat vindt niets in een echte WDAC-export,
# want die staat in de namespace urn:schemas-microsoft-com:sipolicy. Hier telt de tagnaam zonder
# namespace, zodat een echte policy ook echt geteld wordt.
_WDAC_REGELTAGS = ("Allow", "Deny", "FileRule", "FileAttrib", "Signer", "FilePathRule",
                   "FilePublisherRule", "FileHashRule")


def toets_wdac_policy_xml(inhoud, peildatum, regels):
    wortel = lees_xml(inhoud)
    if wortel is None:
        return _unparsed(["7.1"], ["XML niet te lezen"])
    naam = _naam(wortel).lower()
    if naam not in ("sipolicy", "applockerpolicy"):
        return _unparsed(["7.1"], ["geen WDAC- of AppLocker-policy"])
    audit = "Enabled:Audit Mode" in inhoud
    afgedwongen = [e for e in wortel.iter()
                   if _naam(e) == "RuleCollection"
                   and e.attrib.get("EnforcementMode", "").lower() == "enabled"]
    aantal = sum(1 for e in wortel.iter() if _naam(e) in _WDAC_REGELTAGS)
    if audit and not afgedwongen:
        verdict = "fail"
    else:
        verdict = "pass" if aantal > 0 else "fail"
    return _uitkomst({"7.1": verdict},
                     {"formaat": "applocker" if naam == "applockerpolicy" else "wdac",
                      "audit_mode": audit, "afgedwongen": len(afgedwongen), "regels": aantal})


def toets_asr_csv(inhoud, peildatum, regels):
    return _waar_veld("7.2", ["device_name", "asr_office_macros_blocked"], "asr_office_macros_blocked",
                      inhoud, regels, ["device_name", "asr_office_macros_blocked"])


def toets_local_admins_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["device", "user_count_in_admins"], koppen)
    if mist:
        return _unparsed(["7.3"], [f"kolom ontbreekt: {', '.join(mist)}"])

    def nul(rij):
        try:
            return int(str(rij.get("user_count_in_admins") or "").strip() or -1) == 0
        except ValueError:
            return False

    totaal, gedekt = dekking(rijen, nul)
    return _dekkingsuitkomst("7.3", totaal, gedekt, True,
                             voorbeeld=_voorbeeld(rijen, ["device", "user_count_in_admins"]))


def toets_intune_usb_csv(inhoud, peildatum, regels):
    return _waar_veld("7.4", ["device", "usb_blocked_default"], "usb_blocked_default", inhoud, regels,
                      ["device", "usb_blocked_default"])


def toets_entra_admins_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["upn", "auth_methods"], koppen)
    if mist:
        return _unparsed(["8.1"], [f"kolom ontbreekt: {', '.join(mist)}"])
    methoden = [m.lower() for m in _param(regels, "8.1")["methoden"]]

    def bestendig(rij):
        waarde = str(rij.get("auth_methods") or "").lower()
        return any(m in waarde for m in methoden)

    totaal, gedekt = dekking(rijen, bestendig)
    return _dekkingsuitkomst("8.1", totaal, gedekt, True,
                             voorbeeld=_voorbeeld(rijen, ["upn", "auth_methods"]))


def toets_fw_category_csv(inhoud, peildatum, regels):
    koppen, rijen = lees_csv(inhoud)
    mist = ontbrekende_kolommen(["category", "action", "logged"], koppen)
    if mist:
        return _unparsed(["8.4"], [f"kolom ontbreekt: {', '.join(mist)}"])
    treffers = [r for r in rijen
                if "ai" in str(r.get("category") or "").lower() and truthy(r.get("logged"))]
    drempel = _param(regels, "8.4")["minimaal"]
    return _uitkomst({"8.4": "pass" if len(treffers) >= drempel else "fail"},
                     {"totaal": len(rijen), "gedekt": len(treffers), "drempel": drempel},
                     _voorbeeld(treffers, ["category", "action", "logged"]))


def toets_document(inhoud, peildatum, regels, item_id=None):
    """Een geplakt rapport: staan de trefwoorden erin, en is de datum vers genoeg?"""
    if item_id is None:
        return _unparsed(["?"], ["geen item gekozen voor dit document"])
    parameters = _param(regels, item_id)
    dagen_per_maand = regels["tijd"]["document_dagen_per_maand"]
    ontbreekt = [t for t in parameters["trefwoorden"]
                 if not re.search(t, inhoud, re.IGNORECASE | re.DOTALL)]
    datum = lees_datum(inhoud)
    dagen = dagen_tussen(datum.isoformat() if datum else None, peildatum)
    maximaal = parameters["maximale_maanden"] * dagen_per_maand
    samenvatting = {"trefwoorden": list(parameters["trefwoorden"]),
                    "gevonden": len(parameters["trefwoorden"]) - len(ontbreekt),
                    "dagen_oud": dagen, "maximale_maanden": parameters["maximale_maanden"],
                    "parser": parameters["parser"]}
    if ontbreekt:
        return _uitkomst({item_id: "unparsed"}, samenvatting,
                         fouten=[f"trefwoord niet gevonden: {t}" for t in ontbreekt])
    if dagen is None:
        return _uitkomst({item_id: "unparsed"}, samenvatting,
                         fouten=["geen datum gevonden in de tekst (verwacht bijvoorbeeld 2026-03-12)"])
    if dagen > maximaal:
        return _uitkomst({item_id: "stale"}, samenvatting, artefact_datum=datum.isoformat())
    return _uitkomst({item_id: "pass"}, samenvatting, artefact_datum=datum.isoformat())


# ── iamscan: de Linux-dump ───────────────────────────────────────────────────
#
# Overgenomen uit iamscan/parsers.py en iamscan/analysis.py. De vier verdicts staan in regels.json;
# de bevindingen zelf zijn het bewijs en gaan mee in het dossier.

PASSWD, GROUP, SUDOERS, SUDOERS_D, SSHD = ("etc/passwd", "etc/group", "etc/sudoers",
                                           "etc/sudoers.d", "etc/ssh/sshd_config")
_SUDO_TAGS = ("NOPASSWD:", "PASSWD:", "NOEXEC:", "EXEC:", "SETENV:", "NOSETENV:", "LOG_INPUT:", "LOG_OUTPUT:")
_SKIP = ("Defaults", "User_Alias", "Runas_Alias", "Host_Alias", "Cmnd_Alias", "@include")
ERNST = ("hoog", "midden", "laag", "info")


def parse_passwd(tekst: str) -> list[dict]:
    uit = []
    for regel in tekst.splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#"):
            continue
        delen = regel.split(":")
        if len(delen) < 7:
            continue
        try:
            uid, gid = int(delen[2]), int(delen[3])
        except ValueError:
            continue
        uit.append({"naam": delen[0], "uid": uid, "gid": gid, "gecos": delen[4],
                    "home": delen[5], "shell": delen[6]})
    return uit


def parse_group(tekst: str) -> list[dict]:
    uit = []
    for regel in tekst.splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#"):
            continue
        delen = regel.split(":")
        if len(delen) < 4:
            continue
        try:
            gid = int(delen[2])
        except ValueError:
            continue
        uit.append({"naam": delen[0], "gid": gid, "leden": [m for m in delen[3].split(",") if m]})
    return uit


def parse_sudoers(tekst: str, herkomst: str) -> list[dict]:
    uit = []
    for ruw in tekst.splitlines():
        regel = ruw.split("#")[0].strip()
        if not regel or regel.startswith(_SKIP):
            continue
        treffer = re.match(r"^(?P<wie>[%+\w.\-]+)\s+(?P<spec>\S+)\s*=\s*(?P<rest>.*)$", regel)
        if not treffer:
            continue
        rest = treffer.group("rest").strip()
        runas = "ALL"
        als_wie = re.match(r"^\((?P<runas>[^)]*)\)\s*(?P<staart>.*)$", rest)
        if als_wie:
            runas = als_wie.group("runas").strip() or "ALL"
            rest = als_wie.group("staart").strip()
        nopasswd = False
        while True:
            tag = next((t for t in _SUDO_TAGS if rest.upper().startswith(t)), None)
            if tag is None:
                break
            if tag == "NOPASSWD:":
                nopasswd = True
            rest = rest[len(tag):].strip()
        commandos = [c.strip() for c in rest.split(",") if c.strip()]
        if not commandos:
            continue
        uit.append({"wie": treffer.group("wie"), "runas": runas, "commandos": commandos,
                    "nopasswd": nopasswd, "herkomst": herkomst})
    return uit


def parse_authorized_keys(tekst: str, account: str, herkomst: str) -> list[dict]:
    uit = []
    for ruw in tekst.splitlines():
        regel = ruw.strip()
        if not regel or regel.startswith("#"):
            continue
        treffer = re.search(r"(?<![\w-])(ssh-[\w-]+|ecdsa-[\w@.-]+|sk-[\w@.-]+)\s", regel)
        if treffer is None:
            continue
        opties = regel[:treffer.start()].strip().rstrip(",") if treffer.start() > 0 else ""
        delen = regel[treffer.start():].split()
        if len(delen) < 2:
            continue
        uit.append({"account": account, "type": delen[0], "vingerafdruk": delen[1],
                    "comment": " ".join(delen[2:]), "opties": opties, "herkomst": herkomst})
    return uit


def parse_sshd_config(tekst: str) -> dict:
    uit: dict[str, str] = {}
    for ruw in tekst.splitlines():
        regel = ruw.split("#")[0].strip()
        if not regel:
            continue
        delen = regel.split(None, 1)
        if len(delen) != 2:
            continue
        sleutel = delen[0].lower()
        uit.setdefault(sleutel, delen[1].strip())
    return uit


def lees_dump(bestanden: dict[str, str]) -> list[dict]:
    """bestanden: pad binnen de dump naar tekst. Elk eerste padsegment is een host."""
    per_host: dict[str, dict[str, str]] = defaultdict(dict)
    for pad, tekst in bestanden.items():
        schoon = pad.replace("\\", "/").lstrip("./")
        delen = schoon.split("/")
        if len(delen) < 2:
            continue
        if delen[0] == "hosts" and len(delen) > 2:
            delen = delen[1:]
        per_host[delen[0]]["/".join(delen[1:])] = tekst

    hosts = []
    for naam in sorted(per_host):
        inhoud = per_host[naam]
        host = {"naam": naam, "accounts": [], "groepen": [], "sudo": [], "sleutels": [],
                "sshd": {}, "ontbreekt": []}
        for pad, lezer, doel in ((PASSWD, parse_passwd, "accounts"), (GROUP, parse_group, "groepen")):
            if pad in inhoud:
                host[doel] = lezer(inhoud[pad])
            else:
                host["ontbreekt"].append(pad)
        if SUDOERS in inhoud:
            host["sudo"].extend(parse_sudoers(inhoud[SUDOERS], SUDOERS))
        else:
            host["ontbreekt"].append(SUDOERS)
        for pad in sorted(p for p in inhoud if p.startswith(SUDOERS_D + "/")):
            host["sudo"].extend(parse_sudoers(inhoud[pad], pad))
        if SSHD in inhoud:
            host["sshd"] = parse_sshd_config(inhoud[SSHD])
        else:
            host["ontbreekt"].append(SSHD)
        for pad in sorted(p for p in inhoud if p.endswith(".ssh/authorized_keys")):
            delen = pad.split("/")
            account = "root" if delen[0] == "root" else (delen[1] if len(delen) > 2 else delen[0])
            host["sleutels"].extend(parse_authorized_keys(inhoud[pad], account, pad))
        hosts.append(host)
    return hosts


def _leden_van(host: dict, groep: str) -> list[str]:
    gevonden = next((g for g in host["groepen"] if g["naam"] == groep), None)
    if gevonden is None:
        return []
    leden = list(gevonden["leden"])
    for account in host["accounts"]:
        if account["gid"] == gevonden["gid"] and account["naam"] not in leden:
            leden.append(account["naam"])
    return leden


def _principals(host: dict, regel: dict) -> list[str]:
    if not regel["wie"].startswith("%"):
        return [regel["wie"]]
    leden = _leden_van(host, regel["wie"][1:])
    return leden if leden else [regel["wie"]]


def _basisnaam(commando: str) -> str:
    delen = commando.split()
    eerste = delen[0] if delen else commando
    return eerste.rsplit("/", 1)[-1]


def routes_naar_root(host: dict, shell_escape: set) -> list[dict]:
    routes, gezien = [], set()

    def voeg_toe(principal, route, via, nopasswd=False):
        if (principal, via) in gezien:
            return
        gezien.add((principal, via))
        routes.append({"host": host["naam"], "principal": principal, "route": route,
                       "via": via, "nopasswd": nopasswd})

    for account in host["accounts"]:
        if account["uid"] == 0 and account["naam"] != "root":
            voeg_toe(account["naam"], "account heeft UID 0 (naast root)", "uid0")
    for regel in host["sudo"]:
        for principal in _principals(host, regel):
            if principal == "root":
                continue
            if any(c.upper() == "ALL" for c in regel["commandos"]):
                voeg_toe(principal, f"sudo ALL via {regel['wie']} ({regel['herkomst']})",
                         "sudo-all", regel["nopasswd"])
                continue
            escapes = [c for c in regel["commandos"] if _basisnaam(c) in shell_escape]
            if escapes:
                voeg_toe(principal,
                         f"sudo op {', '.join(escapes)} via {regel['wie']} ({regel['herkomst']})",
                         "shell-escape", regel["nopasswd"])
    return sorted(routes, key=lambda r: (r["principal"], r["via"]))


def analyseer(hosts: list[dict], iamscan_regels: dict) -> dict:
    """Bevindingen en routes naar root, letterlijk de controles uit iamscan/analysis.py."""
    shell_escape = set(iamscan_regels["shell_escape"])
    grens = iamscan_regels["uid_grens_systeem"]
    bevindingen: list[dict] = []
    routes: list[dict] = []

    def melden(check, ernst, host, titel, detail, bewijs="", principals=None):
        bevindingen.append({"check": check, "ernst": ernst, "host": host, "titel": titel,
                            "detail": detail, "bewijs": bewijs, "principals": principals or []})

    for host in hosts:
        routes.extend(routes_naar_root(host, shell_escape))
        for ontbreekt in host["ontbreekt"]:
            melden("bron-ontbreekt", "info", host["naam"],
                   f"Bronbestand niet aangetroffen: {ontbreekt}",
                   "De dump is onvolledig; over dit onderdeel is geen conclusie te trekken. "
                   "Afwezigheid van bewijs is hier geen bewijs van afwezigheid.", ontbreekt)
        for account in host["accounts"]:
            interactief = not any(account["shell"].endswith(s)
                                  for s in ("nologin", "false", "sync", "shutdown", "halt"))
            if account["uid"] == 0 and account["naam"] != "root":
                melden("uid0-naast-root", "hoog", host["naam"],
                       f"Account {account['naam']} heeft UID 0",
                       "Een tweede account met UID 0 is technisch root, maar valt buiten alles wat op "
                       "de naam root is ingeregeld.",
                       f"etc/passwd: {account['naam']}:x:{account['uid']}:{account['gid']}",
                       [account["naam"]])
            if account["uid"] < grens and account["uid"] != 0 and interactief:
                melden("serviceaccount-met-shell", "midden", host["naam"],
                       f"Serviceaccount {account['naam']} heeft een interactieve shell",
                       "Serviceaccounts horen niet interactief te zijn. Wie het account overneemt, "
                       "krijgt nu meteen een werkbare shell.",
                       f"etc/passwd: {account['naam']} shell={account['shell']}", [account["naam"]])
        for regel in host["sudo"]:
            principals = [p for p in _principals(host, regel) if p != "root"]
            if not principals:
                continue
            alles = any(c.upper() == "ALL" for c in regel["commandos"])
            if alles and regel["nopasswd"]:
                melden("sudo-all-nopasswd", "hoog", host["naam"],
                       f"{regel['wie']} mag alles als root, zonder wachtwoord",
                       "Volledige rootrechten zonder wachtwoordbevestiging. Een overgenomen sessie of "
                       "sleutel is daarmee direct root, zonder tweede horde.",
                       f"{regel['herkomst']}: {regel['wie']} ... NOPASSWD: {', '.join(regel['commandos'])}",
                       principals)
            elif alles:
                melden("sudo-all", "midden", host["naam"], f"{regel['wie']} mag alles als root",
                       "Volledige rootrechten. Verwacht bij beheerders, te toetsen bij de rest.",
                       f"{regel['herkomst']}: {regel['wie']} ({regel['runas']}) {', '.join(regel['commandos'])}",
                       principals)
            else:
                escapes = [c for c in regel["commandos"] if _basisnaam(c) in shell_escape]
                if escapes:
                    melden("sudo-shell-escape", "hoog", host["naam"],
                           f"{regel['wie']} kan via {', '.join(_basisnaam(c) for c in escapes)} root worden",
                           "De regel oogt beperkt, maar deze commando's geven als root een shell terug "
                           "of laten willekeurig schrijven toe.",
                           f"{regel['herkomst']}: {regel['wie']} ... {', '.join(escapes)}", principals)
        sshd = host["sshd"]
        if sshd.get("permitrootlogin", "").lower() == "yes":
            melden("permitrootlogin", "hoog", host["naam"],
                   "SSH staat rechtstreeks inloggen als root toe",
                   "Directe rootlogin maakt niet herleidbaar wie er handelde en omzeilt sudo-logging.",
                   "etc/ssh/sshd_config: PermitRootLogin yes")
        if sshd.get("passwordauthentication", "").lower() == "yes":
            melden("passwordauth", "midden", host["naam"], "SSH accepteert wachtwoorden",
                   "Wachtwoordauthenticatie maakt de host een bruikbaar doelwit voor brute force en "
                   "voor wachtwoorden die elders al gelekt zijn.",
                   "etc/ssh/sshd_config: PasswordAuthentication yes")
        for sleutel in host["sleutels"]:
            if not sleutel["comment"]:
                melden("sleutel-zonder-eigenaar", "laag", host["naam"],
                       f"Sleutel zonder comment op account {sleutel['account']}",
                       "Zonder comment is niet vast te stellen van wie de sleutel is; bij "
                       "uitdiensttreding wordt zo een sleutel niet ingetrokken.",
                       f"{sleutel['herkomst']}: {sleutel['type']} ...{sleutel['vingerafdruk'][-12:]}",
                       [sleutel["account"]])

    _gedeelde_sleutels(hosts, routes, bevindingen)
    telling = {e: sum(1 for b in bevindingen if b["ernst"] == e) for e in ERNST}
    volgorde = {e: i for i, e in enumerate(ERNST)}
    bevindingen.sort(key=lambda b: (volgorde[b["ernst"]], b["host"], b["check"]))
    return {"hosts": [h["naam"] for h in hosts], "routes": routes, "bevindingen": bevindingen,
            "telling": telling}


def _gedeelde_sleutels(hosts, routes, bevindingen) -> None:
    per_vingerafdruk: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for host in hosts:
        for sleutel in host["sleutels"]:
            per_vingerafdruk[sleutel["vingerafdruk"]].append((host["naam"], sleutel["account"]))
    root_per_host: dict[str, set] = defaultdict(set)
    for route in routes:
        root_per_host[route["host"]].add(route["principal"])

    def bereikt_root(host, account):
        return account == "root" or account in root_per_host.get(host, set())

    for vingerafdruk, plekken in per_vingerafdruk.items():
        if len(plekken) < 2:
            continue
        hosts_geraakt = sorted({h for h, _ in plekken})
        accounts = sorted({a for _, a in plekken})
        label = next((s["comment"] or f"(zonder comment, ...{vingerafdruk[-12:]})"
                      for h in hosts for s in h["sleutels"] if s["vingerafdruk"] == vingerafdruk),
                     vingerafdruk)
        root_op = sorted({h for h, a in plekken if bereikt_root(h, a)})
        bewijs = "; ".join(f"{h}:{a}" for h, a in sorted(plekken))
        if len(accounts) > 1:
            ernst = "hoog" if root_op else "midden"
            detail = (f"Dezelfde sleutel opent {len(accounts)} verschillende accounts "
                      f"({', '.join(accounts)})")
            detail += (f", en bereikt root op {', '.join(root_op)}. Achteraf is niet vast te stellen "
                       "wie er handelde." if root_op else
                       ". Dat vermengt identiteiten en maakt laterale beweging triviaal.")
            bevindingen.append({"check": "sleutel-meerdere-accounts", "ernst": ernst,
                                "host": ", ".join(hosts_geraakt),
                                "titel": f"Sleutel {label} opent {len(accounts)} accounts op "
                                         f"{len(hosts_geraakt)} hosts",
                                "detail": detail, "bewijs": bewijs, "principals": accounts})
            continue
        if len(root_op) > 1:
            bevindingen.append({"check": "sleutel-breed-rootbereik", "ernst": "midden",
                                "host": ", ".join(hosts_geraakt),
                                "titel": f"Sleutel {label} geeft root op {len(root_op)} hosts",
                                "detail": "Een persoonlijke sleutel op meerdere hosts is normaal beheer, "
                                          f"maar deze geeft root op {', '.join(root_op)}.",
                                "bewijs": bewijs, "principals": accounts})


def verdicts_iamscan(analyse: dict, regels: dict) -> dict:
    uit = {}
    aanwezig = {b["check"] for b in analyse["bevindingen"]}
    for item in regels["items"]:
        if item["regel"]["type"] != "iamscan":
            continue
        checks = item["regel"]["parameters"]["checks"]
        uit[item["id"]] = "fail" if any(c in aanwezig for c in checks) else "pass"
    return uit


def toets_iamscan_dump(inhoud, peildatum, regels):
    """inhoud is hier een dict pad naar tekst (de uitgepakte dump)."""
    if not isinstance(inhoud, dict) or not inhoud:
        return _unparsed([i["id"] for i in regels["items"] if i["bron"] == "iamscan_dump"],
                         ["geen leesbare bestanden in de dump"])
    hosts = lees_dump(inhoud)
    if not hosts:
        return _unparsed([i["id"] for i in regels["items"] if i["bron"] == "iamscan_dump"],
                         ["geen host gevonden; verwacht een map per host met etc/passwd erin"])
    analyse = analyseer(hosts, regels["iamscan"])
    uitkomst = _uitkomst(verdicts_iamscan(analyse, regels),
                         {"hosts": len(hosts), "routes": len(analyse["routes"]),
                          "bevindingen": analyse["telling"]},
                         [f"{r['host']} {r['principal']} via {r['via']}" for r in analyse["routes"][:10]])
    uitkomst["analyse"] = analyse
    return uitkomst


TOETSEN = {
    "crown_jewels_csv": toets_crown_jewels_csv, "asset_inventory_csv": toets_asset_inventory_csv,
    "fw_config": toets_fw_config, "vpn_inventory_csv": toets_vpn_inventory_csv,
    "entra_privileged_csv": toets_entra_privileged_csv, "ad_tier0_csv": toets_ad_tier0_csv,
    "gpo_export_xml": toets_gpo_export_xml, "ad_svc_accounts_csv": toets_ad_svc_accounts_csv,
    "laps_csv": toets_laps_csv, "entra_users_csv": toets_entra_users_csv,
    "siem_flow_csv": toets_siem_flow_csv, "sysmon_config_xml": toets_sysmon_config_xml,
    "entra_risky_csv": toets_entra_risky_csv, "fw_flow_csv": toets_fw_flow_csv,
    "siem_rules_json": toets_siem_rules_json, "nessus_xml": toets_nessus_xml,
    "edge_devices_csv": toets_edge_devices_csv, "eol_inventory_csv": toets_eol_inventory_csv,
    "nmap_xml": toets_nmap_xml, "veeam_report_csv": toets_veeam_report_csv,
    "backup_ad_audit_csv": toets_backup_ad_audit_csv, "document": toets_document,
    "wdac_policy_xml": toets_wdac_policy_xml, "asr_csv": toets_asr_csv,
    "local_admins_csv": toets_local_admins_csv, "intune_usb_csv": toets_intune_usb_csv,
    "entra_admins_csv": toets_entra_admins_csv,
    "siem_behavior_rules_json": toets_siem_behavior_rules_json,
    "fw_category_csv": toets_fw_category_csv, "iamscan_dump": toets_iamscan_dump,
}


def toets(bron_id: str, inhoud, peildatum: str, regels: dict, item_id: str | None = None) -> dict:
    functie = TOETSEN.get(bron_id)
    if functie is None:
        return _uitkomst({}, fouten=[f"onbekende bron: {bron_id}"])
    if bron_id == "document":
        return functie(inhoud, peildatum, regels, item_id)
    return functie(inhoud, peildatum, regels)


def dump_uit_tar(ruw: bytes) -> dict[str, str]:
    """De bestanden uit een tar of tar.gz, als pad naar tekst. Alleen in Python; JS leest zelf."""
    bestanden: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(ruw)) as tar:
        for lid in tar.getmembers():
            if not lid.isfile():
                continue
            stroom = tar.extractfile(lid)
            if stroom is None:
                continue
            bestanden[lid.name] = stroom.read().decode("utf-8", "replace")
    return bestanden


# ── Van metingen naar de aanvalspaden ────────────────────────────────────────


def items_per_chokepoint(regels: dict) -> dict[str, list[str]]:
    uit: dict[str, list[str]] = defaultdict(list)
    for item in regels["items"]:
        if item.get("chokepoint"):
            uit[item["chokepoint"]].append(item["id"])
    return {k: sorted(v) for k, v in uit.items()}


def verdict_van(dossier: dict, item_id: str) -> str:
    meting = (dossier.get("metingen") or {}).get(item_id)
    return meting["verdict"] if meting else "geen_bewijs"


def per_chokepoint(regels: dict, paden: dict, dossier: dict) -> dict:
    per_item = items_per_chokepoint(regels)
    uit = {}
    for blad in paden["bladeren"]:
        for cp in blad["chokepoints"]:
            items = per_item.get(cp["id"], [])
            metingen = [{"id": i, "verdict": verdict_van(dossier, i)} for i in items]
            gemeten = [m for m in metingen if m["verdict"] != "geen_bewijs"]
            if not items:
                afgeleid = "geen_meting"
            elif not gemeten:
                afgeleid = "unknown"
            elif any(m["verdict"] == "fail" for m in gemeten):
                afgeleid = "no"
            elif all(m["verdict"] == "pass" for m in gemeten):
                afgeleid = "yes"
            else:
                afgeleid = "unknown"
            uit[cp["id"]] = {"pad": blad["id"], "vraag_id": cp["vraag_id"], "titel": cp["titel"],
                             "drp": cp["drp"], "bewijs": cp["bewijs"], "items": metingen,
                             "afgeleid": afgeleid}
    return uit


_STRENGSTE = {"no": 0, "unknown": 1, "yes": 2}


def afgeleide_antwoorden(regels: dict, paden: dict, dossier: dict) -> dict[str, str]:
    """Per vraag_id het strengste antwoord uit de chokepoints die erop meten. `model` nooit."""
    uit: dict[str, str] = {}
    for cp in per_chokepoint(regels, paden, dossier).values():
        if cp["afgeleid"] in ("geen_meting", "unknown"):
            continue
        vraag = cp["vraag_id"]
        if vraag == "model":
            continue
        huidig = uit.get(vraag)
        if huidig is None or _STRENGSTE[cp["afgeleid"]] < _STRENGSTE[huidig]:
            uit[vraag] = cp["afgeleid"]
    return uit


def witte_vlekken(regels: dict, paden: dict) -> list[dict]:
    per_item = items_per_chokepoint(regels)
    uit = []
    for blad in paden["bladeren"]:
        for cp in blad["chokepoints"]:
            if not per_item.get(cp["id"]):
                uit.append({"pad": blad["id"], "pad_titel": blad["titel"], "chokepoint": cp["id"],
                            "titel": cp["titel"], "drp": cp["drp"], "bewijs": cp["bewijs"]})
    return uit


def dashboard(regels: dict, paden: dict, dossier: dict) -> dict:
    items = regels["items"]
    verdicts = {i["id"]: verdict_van(dossier, i["id"]) for i in items}
    tel_verdict = {v: sum(1 for x in verdicts.values() if x == v) for v in VERDICTS}
    tel_soort = {s: sum(1 for i in items if i["soort"] == s) for s in ("A", "B", "C", "D")}
    per_categorie = {}
    for categorie in regels["categorieen"]:
        nummer = categorie["nummer"]
        eigen = [i["id"] for i in items if i["categorie"] == nummer]
        per_categorie[str(nummer)] = {v: sum(1 for i in eigen if verdicts[i] == v) for v in VERDICTS}
    cps = per_chokepoint(regels, paden, dossier)
    gemeten = sum(1 for c in cps.values()
                  if any(m["verdict"] != "geen_bewijs" for m in c["items"]))
    return {
        "items": {"totaal": len(items),
                  "gemeten": sum(1 for v in verdicts.values() if v != "geen_bewijs")},
        "verdict": tel_verdict,
        "soort": tel_soort,
        "categorie": per_categorie,
        "chokepoints": {"totaal": len(cps), "gemeten": gemeten,
                        "witte_vlekken": len(witte_vlekken(regels, paden))},
    }


def zelfcheck_export(regels: dict, paden: dict, dossier: dict, vandaag: str) -> dict:
    antwoorden = afgeleide_antwoorden(regels, paden, dossier)
    herkomst = {}
    for cp in per_chokepoint(regels, paden, dossier).values():
        if cp["vraag_id"] in antwoorden:
            regel = herkomst.setdefault(cp["vraag_id"], {"items": [], "verdicts": []})
            for meting in cp["items"]:
                if meting["verdict"] != "geen_bewijs" and meting["id"] not in regel["items"]:
                    regel["items"].append(meting["id"])
                    regel["verdicts"].append(meting["verdict"])
    return {"formaat": "zelfcheck-antwoorden", "versie": 1, "bron": "meting", "gemaakt": vandaag,
            "paden_versie": paden["versie"], "antwoorden": antwoorden, "herkomst": herkomst}


# ── Dossier ──────────────────────────────────────────────────────────────────


def vingerafdruk(regels: dict) -> str:
    kern = {s: regels[s] for s in ("items", "bronnen", "tijd", "iamscan", "soorten")}
    ruw = json.dumps(kern, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(ruw.encode("utf-8")).hexdigest()


def sha256_tekst(inhoud) -> str:
    ruw = inhoud if isinstance(inhoud, bytes) else str(inhoud).encode("utf-8")
    return hashlib.sha256(ruw).hexdigest()


def slug(tekst: str) -> str:
    schoon = "".join(t if ("a" <= t <= "z" or "0" <= t <= "9") else "-" for t in str(tekst or "").lower())
    uit = "-".join(d for d in schoon.split("-") if d)[:40].strip("-")
    return uit or "organisatie"


def bestandsnaam(dossier: dict, vandaag: str) -> str:
    return f"meting-dossier-{slug((dossier.get('organisatie') or {}).get('naam'))}-{vandaag}.json"


def nieuw_dossier(regels: dict, paden: dict, peildatum: str) -> dict:
    return {"formaat": "meting-dossier", "versie": 1, "regels_versie": regels["versie"],
            "regels_sha256": vingerafdruk(regels), "paden_versie": paden["versie"], "bijgewerkt": "",
            "organisatie": {"naam": "", "peildatum": peildatum},
            "metingen": {}, "documenten": {}}
