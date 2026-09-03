# Verantwoording van de meting

Waar de 41 items en hun regels vandaan komen, wat er bewust van afwijkt, en wat deze meting wel en niet
beweert. Wie de uitkomst wil kunnen tegenspreken, heeft dit nodig.

## Herkomst

De items en de toetsregels komen uit twee applicaties die hier zijn opgegaan:

| Bron | Wat ervan is overgenomen |
|---|---|
| `security-posture-tool`, tag `v0-applicatie` | de 37 items uit `v0.1/checklist.py`, hun labels en doelen, de koppeling naar de aanvalspaden uit `v0.1/paden_map.py`, en de toetsregels uit `v0.1/connectors/*.py` |
| `iamscan`, tag `v0-applicatie` | de analyse van een Linux-hostdump uit `analysis.py` en `parsers.py`: de vier items 10.1 tot en met 10.4 |

`overname.py` heeft die overname gedaan en kan hem nalezen (`python meting/overname.py --check`). Beide
repo's zijn daarna gearchiveerd. Het waren applicaties, en het statuut van deze
commons zegt dat we
instrumenten publiceren, geen applicaties: een instrument is één bestand dat je opent, niet een
installatie die je moet draaien en onderhouden.

De koppeling naar de barrieres komt uit `paden.json` in deze repo, niet uit een kopie. Dat scheelt de
kopieerslag die de posture-tool wel had.

## Vijf bewuste afwijkingen

**1. De Entra-items krijgen een CSV-contract in plaats van een API-koppeling.** De posture-tool haalde
`fetch_privileged_accounts`, `fetch_mfa_registrations`, `fetch_last_signin`, `fetch_risky_signins` en
`fetch_auth_methods` op via Microsoft Graph. Dat vraagt een app-registratie, toestemming en een geheim,
en het maakt van een instrument een installatie. Hier staan de kleinste kolomsets die diezelfde query's
opleverden als contract in `regels.json`, met per bron de uitleg uit welk portaalscherm of met welk
PowerShell-commando je de export maakt. Dat is documentatie, geen code die kan verlopen.

**2. De vijf documentitems worden geplakte tekst in plaats van PDF.** De posture-tool trok tekst uit een
PDF met `pypdf`. In de browser plak je de tekst of kies je een `.txt` of `.md`. De trefwoordensets en de
termijnen zijn letterlijk `SHALLOW_RULES` uit de bron op de tag. Dat is geen detail: een review op
03-09-2026 ving dat een eerdere versie van het bouwplan trefwoorden had verzonnen die er niet stonden.

Een trefwoordentoets is geen beoordeling. Het verdict heet "voldoet", maar wat het betekent is
"aanwezig en actueel". Wat er in het document staat, beoordeelt een mens.

**3. De vier iamscan-items zijn nieuw.** Ze koppelen aan twee chokepoints:

- AP05-1, privileged access gescheiden van dagelijks gebruik. Een tweede account met UID 0 en een
  `sudo ALL` zonder wachtwoord zijn precies het tegendeel daarvan.
- AP11-3, lateral movement. Root-login over SSH, wachtwoordauthenticatie en een sleutel die bij meerdere
  accounts staat zijn de routes.

De bevindingenlijst per host is het bewijs; die staat op het hostscherm.

**4. De kill-chain-fasen gaan mee als label, zonder regel of telling.** De Lockheed-mapping in de
posture-tool was een voorzet met "DRAFT" erboven. Een label mag dat zijn, een rekenregel niet.

**5. WDAC met een namespace wordt wel gelezen.** `wdac_policy_xml.py` telde de regels in een policy
met `root.iter("Allow")`. Een echte WDAC-export staat in de namespace
`urn:schemas-microsoft-com:sipolicy`, en dan vindt die zoekopdracht niets: de teller blijft op nul staan
en elke echte policy kreeg "voldoet niet". Meting kijkt naar de tagnaam zonder namespace, en telt
dezelfde regelsoorten als de applicatie (`Allow`, `Deny`, `FileRule`, `FileAttrib`, `Signer`,
`FilePathRule`, `FilePublisherRule`, `FileHashRule`). De rest van de regel is ongewijzigd: staat de
policy in audit-modus en dwingt AppLocker niets af, dan is het "voldoet niet".

Twee kleinere dingen in dezelfde regel: XML die geen `SiPolicy` of `AppLockerPolicy` is heet hier "niet
te lezen" in plaats van "voldoet niet" (een willekeurig bestand is geen bewijs van een ontbrekende
maatregel), en de vergelijkingstest in `meting/tests/test_reken.py` legt dit verschil vast, zodat het
zichtbaar blijft.

## Wat de meting niet uitrekent

De meting bepaalt geen status per aanvalspad. Ze leidt per chokepoint een antwoord af (ja, nee,
onbekend) en exporteert dat naar de zelfcheck. De beoordelingsregels staan in `tools/score.py` en in de
zelfcheck, en nergens anders. Een derde kopie van die regels zou een derde waarheid opleveren, en dan is
de vraag welke van de drie klopt.

## Wat de uitkomst waard is

Van de 76 chokepoints in `paden.json` heeft 22 een meetregel. De andere 54 staan als witte vlek op het
padenscherm, met wat ervoor nodig zou zijn. Alles groen betekent dus: de 22 barrieres waarvoor een
export bestaat zijn in orde op het moment van de peildatum. Het betekent niet dat de paden dicht zijn.

Drie dingen die de meting per definitie niet ziet:

1. **Of de export klopt.** Ze leest wat je aanlevert. Een onvolledige CSV geeft een net verdict over een
   onvolledig beeld.
2. **Of de instelling ook werkt.** Een firewallregel in de configuratie is geen bewijs dat het verkeer
   erlangs gaat zoals bedoeld.
3. **Wat er tussen twee metingen gebeurt.** De peildatum staat in het dossier, en de termijnen rekenen
   daarvandaan, juist zodat dat zichtbaar blijft.

## Persoonsgegevens

Exports uit Entra, Active Directory en een hostdump bevatten namen, UPN's en accountnamen. De pagina
verwerkt alles in je eigen browser en stuurt niets weg. Het dossier dat je opslaat bewaart per item
hoogstens tien voorbeeldregels en nooit de ruwe export, maar die tien regels kunnen persoonsgegevens
bevatten. Kijk een dossier na voor je het deelt.

De voorbeelddata in `tests/fixtures/` is verzonnen. Namen als alice, bob, carol en deploy verwijzen niet
naar personen.

## Licentie en aansprakelijkheid

EUPL-1.2, net als de rest van deze repo. Deze meting is een hulpmiddel, geen audit en geen technische
verificatie. De uitkomst komt uit de bestanden die je zelf aanlevert.
