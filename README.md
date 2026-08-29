# Aanvalspaden: van zelfcheck tot risicolijst tot meting

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

De zelfcheck staat live: **[https://security-commons-nl.github.io/aanvalspaden/](https://security-commons-nl.github.io/aanvalspaden/)**. Het is één bestand; opslaan met Ctrl+S geeft je de
offline versie. De pagina haalt niets van buiten en stuurt niets weg, en dat is niet alleen beloofd:
`default-src 'none'` met een hash op het script en de stylesheet, nagerekend door een test.

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

## Bijdragen

Zie [CONTRIBUTING.md](CONTRIBUTING.md). Een issue of discussion is een volwaardige bijdrage; "maak maar een
pull request" is nooit het antwoord.
