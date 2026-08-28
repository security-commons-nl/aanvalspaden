# Aanvalspaden: van zelfcheck tot risicolijst tot meting

> **Status: in aanbouw.** De gedeelde bron (`paden.json`) staat er en wordt bewaakt door tests. De app
> (diepte 0 en 1) wacht op de broncode van de zelfcheck; zie [BESLUITEN.md](BESLUITEN.md).

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
```

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
```

## Mappen

| Map | Wat erin staat |
|---|---|
| `paden.json` | De bron, hierboven beschreven |
| `check/` | Diepte 0 en 1: de offline app (React, Vite). Wacht op de broncode |
| `methode/` | Leeswijzer bij diepte 1; de volledige methode staat in de kennisbank |
| `tools/` | Schema, helpers, en het script waarmee de bron uit de zelfcheck is gehaald |
| `tests/` | Validatie van de bron en van de repo-structuur |

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
