# aanvalspaden

Een instrument in drie diepten: zelfcheck, risicoanalyse en meting, met een gedeelde bron voor de aanvalspaden.

Status: prototype. De bron, de zelfcheck en de meting werken en zijn getest; de risicoanalyse in de app volgt.

> **Status: prototype.** De gedeelde bron (`paden.json`), de zelfcheck (diepte 0) en de meting (diepte 2)
> staan er en worden bewaakt door tests. De zelfcheck is
> [live](https://security-commons-nl.github.io/aanvalspaden/), de meting
> [ook](https://security-commons-nl.github.io/aanvalspaden/meting/). De risicoanalyse in de app (diepte 1)
> volgt. Zie [BESLUITEN.md](BESLUITEN.md).

Eén instrument in drie diepten voor de CISO of ISO van een publieke organisatie. Wie na diepte 0 stopt,
heeft iets bruikbaars.

| Diepte | Wat | Invoer | Tijd | Uitkomst |
|---|---|---|---|---|
| 0. Zelfcheck | Achttien aanvalspaden, korte vragen | Eigen antwoorden | Een uur, alleen | Welke paden staan open, drie acties voor morgen |
| 1. Risicoanalyse | Kroonjuwelen tegen de open paden | Antwoorden plus bewijs | Een dag, met de lijn | Risicolijst met maatregel, eigenaar, termijn |
| 2. Meting | Dezelfde paden, uit echte data | Exports en hostdumps | Doorlopend, techniek | [Bewijs per barriere](https://security-commons-nl.github.io/aanvalspaden/meting/) |
| Handleiding | Hoe pak ik het aan? | Kennisbank, per barriere | Per maatregel | [De handleidingen](https://security-commons-nl.github.io/aanvalspaden/normen/), met de alternatieven ernaast |

Dwars op die drie staat de **normverankering**: welke maatregel uit BIO 2.0, ISO 27001, NIST CSF 2.0,
het Wpg-toetsingskader of de AVG wordt aantoonbaar met het bewijs dat de zelfcheck vraagt, en welke niet.
[Bekijk hem](https://security-commons-nl.github.io/aanvalspaden/normen/), of lees verder onder
[Van aanvalspad naar norm](#van-aanvalspad-naar-norm).

Twee regels houden het eerlijk:

1. **Bewijs is de scheidslijn.** In diepte 0 is "ja" een antwoord; in diepte 1 is een cel pas groen met een
   bewijslink. Die twee mogen nooit door elkaar lopen.
2. **Diepte 1 is een knop, geen volgend scherm.** Wie na het resultaat stopt, houdt een afgeronde zelfcheck.

## Voor wie

CISO's en ISO's bij publieke organisaties.

## Snel starten

Doe de zelfcheck op https://security-commons-nl.github.io/aanvalspaden/ (een uur, in je browser). Zelf bouwen: `python check/bouw.py`.

## Bijdragen

Zie de [CONTRIBUTING](https://github.com/security-commons-nl/.github/blob/main/CONTRIBUTING.md) van de organisatie: daar staat per project een formulier, ook zonder Git-ervaring.

Zie [CONTRIBUTING.md](CONTRIBUTING.md). Een issue of discussion is een volwaardige bijdrage; "maak maar een
pull request" is nooit het antwoord.

## Licentie

EUPL-1.2, zie [LICENSE](LICENSE).

## Zo gebruik je het
**Het uur, alleen.** Open de zelfcheck: **https://security-commons-nl.github.io/aanvalspaden/**. Liever
offline? Sla de pagina op met Ctrl+S; het is één bestand en het haalt niets van buiten. Zeven onderdelen,
44 vragen, en je hebt niets nodig behalve wat je zelf weet van je tenant, je werkplekken en je leveranciers.

Drie regels bij het invullen:

- **Ja betekent afgedwongen en gecontroleerd.** Een maatregel die beschikbaar is maar te omzeilen, is geen
  ja. Kies dan gedeeltelijk.
- **Onbekend is een bruikbaar antwoord.** De check rekent het niet goed en niet fout; hij zegt wat je eerst
  moet uitzoeken.
- **Drie vragen zijn omgekeerd geformuleerd** (bijvoorbeeld: kunnen medewerkers nog via een zwakkere methode
  inloggen?). De app zegt erbij dat ja daar het ongunstige antwoord is.

De uitslag is per aanvalspad een status (open, reactief beheerst, onbekend, beperkt risico, sterk beheerst)
en drie acties voor morgen. Geen score, geen percentage. "84% veilig" zegt niets; "phishing naar
accountovername staat open omdat de sms-fallback nog aan staat" wel. Je antwoorden blijven in de opslag van
je browser; wissen doe je met de knop onder de uitslag.

**De dag, met de lijn.** Neem de open paden mee naar de [methode](methode/README.md). Daar zet je ze af
tegen je kroonjuwelen, maximaal tien processen of gegevensverzamelingen die bestuurlijk pijn doen. Per open
pad en kroonjuweel drie vragen: zien we het, kunnen we reageren, houden we het tegen. Hier telt het
antwoord uit de zelfcheck niet meer; een cel wordt pas groen met een artefact eronder (een export, een
configuratie, een testverslag). De rode cellen zijn je risicolijst, elk met een maatregel, een eigenaar en
een termijn, of een bewuste acceptatie door de risico-eigenaar.

**Daarna, doorlopend.** De [meting](https://security-commons-nl.github.io/aanvalspaden/meting/) toetst
dezelfde chokepoints aan echte data. Je laadt een export (Entra, Active Directory, firewall, nmap, backup)
of een uitgepakte hostdump, en de pagina zegt per item of het voldoet, niet voldoet, te oud is of niet te
lezen. Ook offline, ook zonder installatie: de bestanden verlaten je browser niet. De uitkomst gaat als
antwoorden terug naar de zelfcheck, en vult daar alleen de vragen die nog open staan. Zie onder.

Levert je beheersysteem andere kolomnamen dan een meetregel vraagt, dan zet de
[AI-hulp](https://security-commons-nl.github.io/aanvalspaden/meting/ai/) die om, met je eigen sleutel bij
je eigen leverancier. Wat eruit komt is een voorstel; de meting toetst het pas als jij dat zegt, met
dezelfde regels als bij een gewoon bestand, en noteert dan dat de invoer met AI is omgezet. De tool zelf
praat met niemand. Wat dat inhoudt staat op
[AI-hulp met je eigen sleutel](https://security-commons-nl.github.io/ai-hulp/).

**Wat je er eerlijk bij zegt tegen de directie:** de check is dreigingsgedreven en geen audit tegen een
normenkader. Hij zegt waar een aanvaller ruimte heeft, niet of je compliant bent. Dat vult elkaar aan.

## De bron: `paden.json`
Alle drie de diepten lezen hetzelfde bestand. Vijf clusters voor het overzicht en de matrix, achttien
bladeren voor het detail, en per blad de chokepoints met hun vraag.

```
clusters   C1 Gecompromitteerd account   C2 Werkplek via de gebruiker
           C3 Kwetsbare internetgerichte dienst   C4 Leverancier en keten
           C5 Misbruik van beheerrechten

bladeren   AP01 t/m AP18. AP17 (ransomware) heeft type "impact": het is het gevolg,
           niet de voordeur, en dus geen kolom in de matrix.

per chokepoint   vraag: claim, toelichting, wat niet telt, verificatie, actie
                 drp:   D detecteren, R reageren, P preventief
                 bewijs: welk artefact deze cel groen maakt in diepte 1

randvoorwaarden  Vragen die over alle paden heen meewegen in plaats van bij een enkel pad,
                 zoals 24/7 opvolging van kritieke meldingen.

regels           Hoe de zelfcheck uit antwoorden een status bepaalt: de antwoordopties, de vijf
                 statussen, de bepaling in zes stappen, de uitzonderingen voor AP05 (beheermodel)
                 en AP17 (samenstelling), en de weging van de drie acties. Per blad staan de
                 regelsets: vereist, beperkt, reactief en een eventueel plafond.
```

Elk chokepoint draagt een `vraag_id`. Dezelfde vraag staat bij meer paden (phishingbestendige
authenticatie telt bij vier paden) en wordt maar een keer gesteld; het antwoord geldt overal. Drie vragen
zijn omgekeerd geformuleerd (`negatief: true`): daar betekent ja dat de barriere ontbreekt.

De regels zijn geen tweede waarheid naast de code. `tools/score.py` is een referentie-implementatie die ze
uit de bron leest, en `tests/fixtures/doorloop-2026-08-28.json` is een echte doorloop van de zelfcheck
met 44 antwoorden en de uitslag die de app daarop gaf. Een test bewaakt dat de referentie exact hetzelfde
zegt: achttien statussen, drie acties, in die volgorde.

Samen 44 unieke vragen: precies de vragen die de zelfcheck stelt. Een test bewaakt dat aantal, zodat
de bron niet stilletjes achterloopt op de app.

Wijzig een pad of een vraag hier, en alle drie de diepten volgen. Het schema staat in
[`tools/paden.schema.json`](tools/paden.schema.json); `python -m pytest tests/ -v` valideert de bron en
controleert onder meer dat elk pad in precies één cluster zit, dat elke claim een vraagzin is, dat elk
chokepoint zegt welk bewijs telt, en dat er geen organisatienamen in staan.

Lezen vanuit Python:

```python
from tools import paden

paden.paden()             # de zeventien paden: de kolommen van de matrix
paden.blad("AP01")        # één blad met zijn chokepoints
paden.cluster_van("AP01") # het cluster waar het blad in zit
paden.chokepoint("AP01-1")

from tools import score
uit = score.beoordeel(paden.laad(), {"pr": "yes", "fallback": "no", "soc": "yes"})
uit["AP01"]["status"]     # "strong": beide vereiste barrieres staan (fallback is omgekeerd: nee = goed)
score.acties(paden.laad(), antwoorden, uit)   # de drie zwaarste acties
```

## Mappen
| Map | Wat erin staat |
|---|---|
| `paden.json` | De bron, hierboven beschreven |
| `check/` | Diepte 0: de zelfcheck, een zelfstandig HTML-bestand uit de bron. [Live](https://security-commons-nl.github.io/aanvalspaden/) |
| `methode/` | Leeswijzer bij diepte 1; de volledige methode staat in de kennisbank |
| `meting/` | Diepte 2: bewijs per barriere uit exports en hostdumps, ook een zelfstandig HTML-bestand. [Live](https://security-commons-nl.github.io/aanvalspaden/meting/) |
| `meting/ai/` | Opt-in AI-hulp bij de meting: een export omzetten naar het kolomcontract van een meetregel, met je eigen sleutel. [Live](https://security-commons-nl.github.io/aanvalspaden/meting/ai/) |
| `mappingen/` | De normverankering: per barriere welke maatregel er aantoonbaar mee wordt, plus de witte vlekken. [Live](https://security-commons-nl.github.io/aanvalspaden/normen/) |
| `tools/` | Schema, helpers, de referentie-implementatie van de regels, en het script waarmee de bron uit de zelfcheck is gehaald |
| `tests/` | Validatie van de bron en van de repo-structuur |

De zelfcheck haalt niets van buiten en stuurt niets weg, en dat is niet alleen beloofd: het
Content-Security-Policy is `default-src 'none'` met een hash op het script en de stylesheet, nagerekend
door een test. Details in [`check/LEESMIJ.md`](check/LEESMIJ.md).

Diepte 2 (de meting) staat in [`meting/`](meting/LEESMIJ.md), in dezelfde vorm: één HTML-bestand met
`default-src 'none'` en zonder netwerk. De 41 items dragen elk een `pad` en een `chokepoint` uit deze bron,
zodat een meting het bewijs is voor een barriere hier. Ze leest `paden.json` rechtstreeks, dus er is geen
kopie die kan achterlopen. De items komen uit `security-posture-tool` en `iamscan`, die daarmee zijn
opgegaan in deze repo; de herkomst en de bewuste afwijkingen staan in
[`meting/VERANTWOORDING.md`](meting/VERANTWOORDING.md).

## Van aanvalspad naar norm
De zelfcheck vraagt naar barrieres, niet naar normen. Wie hem heeft gedaan, krijgt van zijn auditor of
zijn risicohouder toch de vraag wat dit betekent voor de BIO. De
**[normverankering](https://security-commons-nl.github.io/aanvalspaden/normen/)** beantwoordt die vraag
voor vier kaders, en de omgekeerde erbij.

Er is precies een relatie, en die heeft een richting: **een barriere levert bewijs voor een maatregel.**
Nooit "dekt af", nooit "voldoet aan". Wie de zelfcheck heeft gedaan heeft antwoorden; wie het gevraagde
bewijs erbij legt heeft materiaal voor een gesprek. Het oordeel blijft van de auditor. Elke regel draagt
een sterkte (`volledig`, `gedeeltelijk`, `raakvlak`) en een reden in een zin, zodat je hem kunt
tegenspreken zonder JSON te lezen. Een raakvlak telt niet als dekking.

| Kader | Wat erin zit | Wat de zelfcheck raakt |
|---|---|---|
| BIO 2.0 en ISO 27001:2022 | 89 maatregelen. BIO 2.0 volgt de ISO 27002-nummering, dus dit is een mapping en niet twee | 44 met bewijs, 45 witte vlekken |
| NIST CSF 2.0 | 106 subcategorieen in zes functies. Publiek domein, dus de uitkomsten staan er letterlijk | 41 met bewijs, 65 witte vlekken |
| Wpg-toetsingskader voor boa's | 31 beheersingsmaatregelen plus de vijf technische uit bijlage 4 van de NOREA-handreiking | 8 met bewijs, 28 witte vlekken |
| AVG | 32 artikelen die in een AVG-toets als toetspunt gelden, van de beginselen tot de doorgifte | 6 met bewijs, 26 witte vlekken |

Die dalende reeks is geen tekort maar het punt. Hoe dichter een kader bij techniek en dreiging staat,
hoe meer een zelfcheck ervan aantoont: NIST CSF is dreigingsgericht en komt op 39 procent, de AVG gaat
over grondslag, transparantie en de rechten van betrokkenen en komt op 19. Geen aanvalspad zegt iets
over bewaartermijnen of een verwerkingsregister, en dat hoort zo. **De witte vlekken zijn daarmee het
eigenlijke product:** ze laten per maatregelnummer zien waar een dreigingsgerichte zelfcheck ophoudt en
de rest van het normenkader begint.

De volgorde van de kaders is redactioneel, niet alfabetisch: BIO 2.0 opent, omdat dat het kader is
waar de doelgroep op wordt bevraagd. Een nieuw kader dat niet in die volgorde staat, laat de tests
falen.

Drie ingangen op dezelfde data: vanuit het aanvalspad, vanuit de maatregel, en de witte vlekken.
De mapping hangt aan de barriere (het `vraag_id`), niet aan het chokepoint: de 76 chokepoints delen
44 unieke barrieres, en dezelfde vraag hoort overal hetzelfde te verankeren. Details, de bronnen en de
afspraak over auteursrecht staan in [`mappingen/LEESMIJ.md`](mappingen/LEESMIJ.md).

**Status: eerste versie, nog niet gereviewd.** De regels zijn geschreven op basis van de bron en het
kader, en hebben nog geen review van vakgenoten gehad. Een regel die te ruim, te krap of gewoon fout is,
hoort een issue te worden.

## Hoe pak ik het aan
De zelfcheck zegt wat je moet doen, maar niet hoe. Voor een deel van de barrieres ligt er een
handleiding in de kennisbank; voor de meeste nog niet. Dat staat allebei op de pagina, onder
[Hoe pak ik het aan](https://security-commons-nl.github.io/aanvalspaden/normen/).

| | Aantal |
|---|---|
| Barrieres met een handleiding | 14 (4 volledig, 10 gedeeltelijk) |
| Barrieres zonder handleiding | 30 |
| Artikelen om te schrijven | 11 |

**Die 30 zijn geen tekort maar de redactieagenda.** Per ontbrekende handleiding staat er wat het
artikel zou moeten dekken, en een knop die een vooringevulde issue opent met de barrieres en het
gevraagde bewijs erin. Een kennisbank die alleen toont wat er ligt is een etalage; wat ontbreekt is
wat een commons nodig heeft.

De volgorde komt uit de data: het gewicht is het aantal aanvalspaden waarop een barriere staat, dus
wat de meeste routes tegelijk sluit, schrijf je eerst. Zodra er echte zelfcheck-uitslagen zijn, is het
betere signaal hoe vaak een barriere als actie bovenkomt.

## De methode, leesbaar
De vier stappen met de lijn erbij, het papieren sjabloon en een ingevuld voorbeeld staan in de kennisbank:
[Risicoanalyse langs aanvalspaden](https://security-commons-nl.github.io/kennisbank/security/risicoanalyse-aanvalspaden/).

## Zelf draaien
```bash
pip install pytest jsonschema
python -m pytest tests/ -v        # bron en structuur
```

Zodra `check/` er is: `cd check && npm ci && npm run build` levert één offline HTML-bestand.

## Herkomst
De zelfcheck is ontwikkeld door de CISO-organisatie van een Nederlandse gemeente en met toestemming
ingebracht; de methode komt uit de kennisbank van security-commons-nl. Licentie: EUPL-1.2.
