# aanvalspaden

Een instrument in drie diepten: zelfcheck, risicoanalyse en meting, met een gedeelde bron voor de aanvalspaden.

Status: prototype. De bron en de zelfcheck werken en zijn getest; de risicoanalyse in de app volgt.

> **Status: prototype.** De gedeelde bron (`paden.json`) en de zelfcheck (diepte 0) staan er en worden
> bewaakt door tests; de zelfcheck is [live](https://security-commons-nl.github.io/aanvalspaden/). De
> risicoanalyse in de app (diepte 1) volgt; de meting (diepte 2) woont nog in de posture-tool. Zie
> [BESLUITEN.md](BESLUITEN.md).

Eén instrument in drie diepten voor de CISO of ISO van een publieke organisatie. Wie na diepte 0 stopt,
heeft iets bruikbaars.

| Diepte | Wat | Invoer | Tijd | Uitkomst |
|---|---|---|---|---|
| 0. Zelfcheck | Achttien aanvalspaden, korte vragen | Eigen antwoorden | Een uur, alleen | Welke paden staan open, drie acties voor morgen |
| 1. Risicoanalyse | Kroonjuwelen tegen de open paden | Antwoorden plus bewijs | Een dag, met de lijn | Risicolijst met maatregel, eigenaar, termijn |
| 2. Meting | Dezelfde paden, uit echte data | Exports en connectors | Doorlopend, techniek | Bewijs per cel |

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

**Daarna, doorlopend.** De meting haalt dezelfde chokepoints uit echte data (Entra, firewall, CSV) en
levert het bewijs per cel. Zie onder.

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
| `tools/` | Schema, helpers, de referentie-implementatie van de regels, en het script waarmee de bron uit de zelfcheck is gehaald |
| `tests/` | Validatie van de bron en van de repo-structuur |

De zelfcheck haalt niets van buiten en stuurt niets weg, en dat is niet alleen beloofd: het
Content-Security-Policy is `default-src 'none'` met een hash op het script en de stylesheet, nagerekend
door een test. Details in [`check/LEESMIJ.md`](check/LEESMIJ.md).

Diepte 2 (de meting) woont voorlopig in
[security-posture-tool](https://github.com/security-commons-nl/security-posture-tool). Daar draagt elk
checklist-item een `pad` en een `chokepoint` uit deze bron, zodat een meting daar het bewijs is voor een cel
hier. De repo houdt een kopie van `paden.json` met een hash die bewaakt dat hij niet achterloopt.

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
