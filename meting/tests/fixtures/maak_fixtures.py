#!/usr/bin/env python3
"""Maakt de voorbeeldbestanden voor de tests van meting: een per bron, plus een Linux-dump.

Alles verzonnen: Gemeente Voorbeeld. Namen als alice, bob, carol en deploy komen uit de testdata van
iamscan en duiden geen persoon aan. De datums zijn zo gekozen dat elk bestand met peildatum 2026-09-03
het bedoelde verdict geeft; wie de peildatum verzet, ziet de verdicts kantelen, en dat is precies wat
`test_tijd_rekent_vanaf_peildatum` toetst.

De tar wordt ongecomprimeerd geschreven, met vaste datum en zonder OS-velden: gzip is niet
byte-reproduceerbaar tussen platforms (de les van de xlsx-fixture in procescheck). De tests maken de
.tar.gz zelf.

Aanroep:
    python meting/tests/fixtures/maak_fixtures.py
"""
from __future__ import annotations

import calendar
import datetime
import io
import pathlib
import shutil
import tarfile

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent.parent
PEILDATUM = datetime.date(2026, 9, 3)


def dagen_terug(n: int) -> str:
    return (PEILDATUM - datetime.timedelta(days=n)).isoformat()


def uren_terug(n: int) -> str:
    stamp = datetime.datetime(2026, 9, 3, 12, 0, tzinfo=datetime.timezone.utc) - datetime.timedelta(hours=n)
    return stamp.isoformat().replace("+00:00", "Z")


BESTANDEN: dict[str, str] = {}


# ── 1 Inventaris ────────────────────────────────────────────────────────────
BESTANDEN["crown-jewels.csv"] = """name,owner,vlan_or_subnet,backup_type,rto,rpo
Paspoortuitgifte,Teamleider Burgerzaken,VLAN 42 / 10.20.42.0/24,immutable + offsite,4 uur,1 uur
Uitkeringsadministratie,Afdelingshoofd Werk en Inkomen,VLAN 44 / 10.20.44.0/24,immutable + offsite,8 uur,4 uur
Financieel systeem,Concerncontroller,VLAN 46 / 10.20.46.0/24,snapshot + tape,24 uur,12 uur
"""

# Drie bronnen. Tien adressen staan in alle drie; de AD-export heeft er een extra die de andere twee
# niet kennen. Dat is 10 van 11 unieke adressen in twee of meer bronnen (91 procent, boven de 90) en een
# spreiding van 11 tegen 10 (9 procent, onder de 20).
_ips = [f"10.20.42.{n}" for n in range(11, 21)]
_asset = ["source,ip,hostname"]
for _bron in ("ad", "dhcp", "fw_arp"):
    for _n, _ip in enumerate(_ips):
        _asset.append(f"{_bron},{_ip},host-{_n + 1:02d}")
_asset.append("ad,10.20.42.99,host-alleen-in-ad")
BESTANDEN["asset-inventaris.csv"] = "\n".join(_asset) + "\n"

# ── 2 Segmentatie ───────────────────────────────────────────────────────────
BESTANDEN["fortigate-config.txt"] = """config firewall policy
    edit 1
        set name "jump-naar-ilo"
        set srcintf "jump"
        set dstintf "ilo"
        set srcaddr "jumphosts"
        set dstaddr "ilo-net"
        set service "HTTPS"
        set action accept
    next
    edit 2
        set name "mgmt-beheer"
        set srcintf "mgmt"
        set dstintf "tooling"
        set srcaddr "mgmt-hosts"
        set dstaddr "tooling-net"
        set service "SSH"
        set action accept
    next
    edit 3
        set name "gast-naar-internet"
        set srcintf "guest"
        set dstintf "wan"
        set srcaddr "all"
        set dstaddr "all"
        set service "ALL"
        set action accept
    next
    edit 4
        set name "kantoor-naar-server"
        set srcintf "user"
        set dstintf "server"
        set srcaddr "werkplekken"
        set dstaddr "app-servers"
        set service "HTTPS"
        set action accept
    next
end
"""

BESTANDEN["vpn-peers.csv"] = """peer,dst_subnet,leverancier
leverancier-zaaksysteem,10.20.50.0/24,ZaakSoft
leverancier-toegangscontrole,10.20.60.8/29,SecuDoor
onderhoud-klimaat,10.20.61.0/28,KlimaatBeheer
"""

# ── 3 Identity ──────────────────────────────────────────────────────────────
BESTANDEN["entra-privileged.csv"] = """upn,display_name,mfa_registered,methods
beheer1@voorbeeld.nl,Beheerder een,true,fido2;authenticator
beheer2@voorbeeld.nl,Beheerder twee,true,fido2
beheer3@voorbeeld.nl,Beheerder drie,true,windowsHelloForBusiness
"""

BESTANDEN["ad-tier0.csv"] = """account,logon_workstations_set,logon_workstations
adm-burgerzaken,true,PAW-01;PAW-02
adm-infra,true,PAW-01
adm-backup,true,PAW-03
"""

BESTANDEN["gpo-export.xml"] = """<?xml version="1.0" encoding="utf-8"?>
<GPOS>
  <GPO><Name>Tier-0 beperking</Name>
    <Computer><ExtensionData><Extension>
      <Policy><Name>LogonWorkstations</Name><State>Enabled</State><Value>PAW-01,PAW-02</Value></Policy>
    </Extension></ExtensionData></Computer>
  </GPO>
</GPOS>
"""

BESTANDEN["ad-serviceaccounts.csv"] = """sam,in_da,auth_type,pw_len,ou
svc-zaaksysteem,false,gmsa,0,OU=Service
svc-backup,false,password,32,OU=Service
svc-monitoring,false,gmsa,0,OU=Service
"""

# Bewust een apparaat zonder LAPS: dit item hoort fail te geven, zodat de doorloop niet alleen groen is.
BESTANDEN["laps.csv"] = """device_name,os,laps_configured,laps_last_rotation
WKS-001,Windows 11,true,2026-08-28T08:12:00Z
WKS-002,Windows 11,true,2026-08-29T09:00:00Z
SRV-010,Windows Server 2022,false,
"""

BESTANDEN["entra-accounts.csv"] = f"""upn,display_name,enabled,last_signin
medewerker1@voorbeeld.nl,Medewerker een,true,{dagen_terug(3)}
medewerker2@voorbeeld.nl,Medewerker twee,true,{dagen_terug(40)}
oud-account@voorbeeld.nl,Oud account,false,{dagen_terug(400)}
"""

# ── 4 Zicht ─────────────────────────────────────────────────────────────────
BESTANDEN["siem-flow.csv"] = f"""timestamp,src_ip,dst_ip,src_vlan,dst_vlan
{uren_terug(2)},10.20.42.11,10.20.44.5,vlan42,vlan44
{uren_terug(6)},10.20.44.5,10.20.46.9,vlan44,vlan46
{uren_terug(30)},10.20.42.12,8.8.8.8,vlan42,wan
"""

BESTANDEN["sysmon-config.xml"] = """<?xml version="1.0" encoding="utf-8"?>
<Sysmon schemaversion="4.90">
  <!-- sysmonconfig-export.xml door SwiftOnSecurity, aangepast voor Gemeente Voorbeeld -->
  <EventFiltering>
    <RuleGroup name="proces aanmaken" groupRelation="or">
      <ProcessCreate onmatch="exclude"><Image condition="is">C:\\Windows\\System32\\svchost.exe</Image></ProcessCreate>
    </RuleGroup>
    <RuleGroup name="netwerkverbinding" groupRelation="or">
      <NetworkConnect onmatch="include"><DestinationPort condition="is">4444</DestinationPort></NetworkConnect>
    </RuleGroup>
    <RuleGroup name="bestand aangemaakt" groupRelation="or">
      <FileCreate onmatch="include"><TargetFilename condition="end with">.ps1</TargetFilename></FileCreate>
    </RuleGroup>
    <RuleGroup name="registerwijziging" groupRelation="or">
      <RegistryEvent onmatch="include"><TargetObject condition="contains">CurrentVersion\\Run</TargetObject></RegistryEvent>
    </RuleGroup>
    <RuleGroup name="stuurprogramma geladen" groupRelation="or">
      <DriverLoad onmatch="exclude"><Signature condition="contains">Microsoft</Signature></DriverLoad>
    </RuleGroup>
    <RuleGroup name="proces beeindigd" groupRelation="or">
      <ProcessTerminate onmatch="include"><Image condition="end with">powershell.exe</Image></ProcessTerminate>
    </RuleGroup>
  </EventFiltering>
</Sysmon>
"""

BESTANDEN["entra-risky.csv"] = f"""user,risk_level,risk_state,datum,ip
medewerker3@voorbeeld.nl,low,remediated,{dagen_terug(30)},203.0.113.7
"""

BESTANDEN["fw-flow.csv"] = f"""timestamp,src_ip,dst_ip,fqdn
{uren_terug(1)},10.20.42.11,93.184.216.34,www.voorbeeld.nl
{uren_terug(2)},10.20.42.12,93.184.216.35,api.voorbeeld.nl
{uren_terug(3)},10.20.44.5,93.184.216.36,updates.voorbeeld.nl
"""

BESTANDEN["siem-regels.json"] = "[\n" + ",\n".join(
    '  {"id": "R%02d", "name": "Gemeenteregel %d", "tags": ["gemeente", "burgerzaken"]}' % (n, n)
    for n in range(1, 11)) + ',\n  {"id": "R99", "name": "Generieke regel", "tags": ["algemeen"]}\n]\n'

BESTANDEN["siem-gedrag.json"] = """[
  {"id": "B01", "name": "Ongebruikelijke aanmeldtijd", "type": "behavior"},
  {"id": "B02", "name": "Massale bestandstoegang", "type": "behavior"},
  {"id": "B03", "name": "Nieuwe beheerdersrol", "type": "behavior"},
  {"id": "S01", "name": "Bekende hash", "type": "signature"}
]
"""

# ── 5 Kwetsbaarheden ────────────────────────────────────────────────────────
BESTANDEN["nessus-scan.nessus"] = f"""<?xml version="1.0" encoding="utf-8"?>
<NessusClientData_v2>
  <Report name="Extern {dagen_terug(4)}">
    <ReportHost name="93.184.216.34">
      <HostProperties><tag name="HOST_START">{dagen_terug(4)}T02:00:00Z</tag></HostProperties>
      <ReportItem port="443" severity="2" pluginName="TLS-configuratie"/>
      <ReportItem port="80" severity="1" pluginName="Informatieve melding"/>
    </ReportHost>
  </Report>
</NessusClientData_v2>
"""

BESTANDEN["edge-apparaten.csv"] = f"""device,type,last_patched_at
vpn-concentrator,VPN,{uren_terug(20)}
edge-firewall,Firewall,{uren_terug(40)}
reverse-proxy,Proxy,{uren_terug(60)}
"""

BESTANDEN["eol-systemen.csv"] = """system,eol_date,migration_date,eigenaar
oud-fileserver,2027-01-31,2026-11-15,Team ICT
legacy-database,2027-06-30,2027-03-01,Team Gegevens
"""

_nmap_ts = calendar.timegm((PEILDATUM - datetime.timedelta(days=4)).timetuple())
BESTANDEN["nmap-extern.xml"] = f"""<?xml version="1.0" encoding="utf-8"?>
<nmaprun scanner="nmap" start="{_nmap_ts}" startstr="externe scan">
  <host>
    <address addr="93.184.216.34" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="443"><state state="open"/></port>
      <port protocol="tcp" portid="80"><state state="closed"/></port>
    </ports>
  </host>
</nmaprun>
"""

# ── 6 Back-up ───────────────────────────────────────────────────────────────
BESTANDEN["backup-rapport.csv"] = f"""job_name,last_success,immutable,errors,repository
Kroonjuwelen dagelijks,{uren_terug(6)},true,0,immutable-repo
Bestandsservers dagelijks,{uren_terug(10)},true,0,immutable-repo
"""

BESTANDEN["backup-ad.csv"] = """backup_system,prod_ad_trust,eigen_ad,mfa
Backup-cluster,false,true,true
Offsite-kopie,false,true,true
"""

# ── 7 Werkplek ──────────────────────────────────────────────────────────────
BESTANDEN["wdac-policy.xml"] = """<?xml version="1.0" encoding="utf-8"?>
<SiPolicy xmlns="urn:schemas-microsoft-com:sipolicy">
  <Rules>
    <Rule><Option>Enabled:Unsigned System Integrity Policy</Option></Rule>
    <Rule><Option>Required:Enforce Store Applications</Option></Rule>
  </Rules>
  <FileRules>
    <Allow ID="ID_ALLOW_A_1" FriendlyName="Windows" FileName="*"/>
  </FileRules>
</SiPolicy>
"""

BESTANDEN["intune-asr.csv"] = """device_name,os,asr_office_macros_blocked
WKS-001,Windows 11,true
WKS-002,Windows 11,true
WKS-003,Windows 11,true
"""

BESTANDEN["lokale-admins.csv"] = """device,user_count_in_admins,members
WKS-001,0,Administrators;adm-infra
WKS-002,0,Administrators;adm-infra
WKS-003,0,Administrators;adm-infra
"""

BESTANDEN["intune-usb.csv"] = """device,usb_blocked_default,policy
WKS-001,true,Werkplekbeperking
WKS-002,true,Werkplekbeperking
WKS-003,true,Werkplekbeperking
"""

# ── 8 Volwassenheid ─────────────────────────────────────────────────────────
BESTANDEN["entra-beheerders.csv"] = """upn,role,auth_methods
beheer1@voorbeeld.nl,Global Administrator,fido2;microsoftAuthenticator
beheer2@voorbeeld.nl,Security Administrator,fido2
beheer3@voorbeeld.nl,Intune Administrator,windowsHelloForBusiness
"""

BESTANDEN["fw-categorieen.csv"] = """category,action,logged,policy
ai-tools,allow,true,Uitgaand verkeer
sociale-media,allow,true,Uitgaand verkeer
gokken,block,true,Uitgaand verkeer
"""

# ── C-items: geplakte rapporttekst ──────────────────────────────────────────
BESTANDEN["restore-test.txt"] = f"""Verslag hersteltest kroonjuwelen

Datum: {dagen_terug(60)}

Op bovenstaande datum is een restore uitgevoerd van de database achter Paspoortuitgifte, vanaf de
immutable kopie. De afgesproken RTO van 4 uur is gehaald: de omgeving was na 3 uur en 10 minuten
beschikbaar. De RPO van 1 uur is gehaald; het laatste herstelpunt was 40 minuten oud.

Aandachtspunt: de restore van de bijlagenopslag duurde langer dan verwacht en is apart belegd.
"""

BESTANDEN["tabletop.txt"] = f"""Verslag tabletop-oefening ransomware

Datum: {dagen_terug(45)}

Scenario: versleuteling van de bestandsservers op vrijdagavond, met uitval van het zaaksysteem op
maandagochtend. Deelnemers: directie, ICT, communicatie en de CISO.

Respons: de crisisorganisatie is binnen 45 minuten opgestart. De besluitvorming over uitwijk verliep
traag omdat de mandaten niet op papier stonden.

Verbeterpunten: mandaten vastleggen, de belboom actualiseren, en de lessons learned na twee weken
opnieuw langslopen.
"""

BESTANDEN["kpi-rapport.txt"] = f"""Maandrapportage informatiebeveiliging

Datum: {dagen_terug(12)}

Patchstatus: 98 procent van de werkplekken is binnen de termijn bijgewerkt; twee servers wachten op een
onderhoudsvenster.

MFA: 100 procent van de beheerders gebruikt een phishingbestendige methode.

Incidenten: drie meldingen, waarvan een phishingpoging die door de gebruiker is gemeld. Geen incident
met impact op de dienstverlening.
"""

BESTANDEN["bio2-gap.txt"] = f"""Gap-analyse BIO 2.0

Datum: {dagen_terug(120)}

Deze analyse legt de maatregelen van de gemeente naast BIO 2 en benoemt per thema de gap. De grootste
afwijking zit op logging en monitoring: de bewaartermijn is korter dan de norm vraagt.

Aanbeveling: de retentie verhogen naar 90 dagen en de use-cases per kwartaal herijken. Remediatie is
belegd bij Team ICT.
"""

BESTANDEN["pentest.txt"] = f"""Rapportage externe penetratietest

Datum: {dagen_terug(150)}

Scope: de extern benaderbare webomgeving en het VPN-koppelvlak. Getest volgens OWASP en NCSC-richtlijn.

Bevinding 1: verouderde TLS-configuratie op de reverse proxy. CVSS 5.3 (medium). Hersteld en
geverifieerd.
Bevinding 2: informatielek in een foutmelding. CVSS 3.1 (low). Hersteld.

Er zijn geen bevindingen met severity high of critical aangetroffen.
"""


def schrijf_dump() -> None:
    """De Linux-dump: kopie van de testdata van iamscan, plus een tar zonder compressie."""
    doel = HIER / "iamscan-dump"
    bron = REPO.parent / "iamscan" / "testdata" / "hosts"
    if not bron.is_dir():
        print("  iamscan/testdata/hosts niet gevonden; dump overgeslagen")
        return
    if doel.exists():
        shutil.rmtree(doel)
    shutil.copytree(bron, doel / "hosts")

    # De tar draagt alleen web01, zoals collect.sh hem per host maakt.
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for pad in sorted((doel / "hosts" / "web01").rglob("*")):
            if not pad.is_file():
                continue
            naam = "web01/" + str(pad.relative_to(doel / "hosts" / "web01")).replace("\\", "/")
            info = tarfile.TarInfo(naam)
            inhoud = pad.read_bytes()
            info.size = len(inhoud)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(inhoud))
    (HIER / "web01-iamscan.tar").write_bytes(buffer.getvalue())


def main() -> int:
    for naam, inhoud in BESTANDEN.items():
        # Regeleindes altijd LF: dit script staat op Windows in de repo, en met CRLF zou de
        # sha256 van dezelfde fixture in Python en in de browser verschillen.
        schoon = inhoud.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))
        (HIER / naam).write_bytes(schoon.encode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
