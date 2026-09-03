# meting/ - bewijs per barriere (diepte 2)

De zelfcheck vraagt wat je denkt dat er staat. De meting kijkt in de export. Je laadt een CSV, een XML,
een firewallconfiguratie of een uitgepakte hostdump, en de pagina zegt per item: voldoet, voldoet niet,
te oud, niet te lezen, of nog geen bewijs. Daarna laat hij zien welke chokepoints uit `paden.json`
daarmee bewijs hebben en welke niet.

Eén zelfstandig HTML-bestand, net als de zelfcheck en de crosswalk. Geen server, geen account, geen
telemetrie, geen enkele externe verwijzing. De bestanden die je laadt verlaten je browser niet.

**Live:** https://security-commons-nl.github.io/aanvalspaden/meting/

## Bouwen

```bash
python meting/bouw.py          # schrijft meting/dist/index.html (ongeveer 205 kB)
python meting/bouw.py site     # of naar een andere map
```

Het bouwscript zet `regels.json`, een uitsnede van `paden.json` en `bron/app.js` in één scripttag en
`bron/app.css` in één style-tag, en berekent daarna de sha256 van allebei voor het
Content-Security-Policy in `bron/index.html`:

```
default-src 'none'; script-src 'sha256-...'; style-src 'sha256-...'; img-src data:;
form-action 'none'; base-uri 'none'
```

Er staat bewust geen `connect-src` in. De meting praat met niemand, en een test controleert dat `fetch`,
`XMLHttpRequest`, `WebSocket` en `EventSource` nergens in de pagina voorkomen.

Uit `paden.json` gaan alleen `bladeren`, `randvoorwaarden`, `regels` en `versie` mee. De `onderdelen`
(de vragen met hun toelichting) horen bij de zelfcheck, niet hier; een test bewaakt dat ze niet
meeliften.

## De bestanden

| Bestand | Wat het is |
|---|---|
| `regels.json` | de 41 items, de 30 bronnen, de tien categorieen, de termijnen en de iamscan-constanten. Data, geen code |
| `overname.py` | het script dat `regels.json` ooit uit de posture-tool en iamscan trok, met `--check` om te vergelijken. Eenmalig, niet in de CI |
| `reken.py` | de referentie: de lezers, per bron een `toets_`-functie, de iamscan-analyse, de afleiding naar chokepoints, het dashboard |
| `bron/app.js` | dezelfde regels in de browser, functie voor functie als `reken.<naam>` |
| `bron/index.html`, `bron/app.css` | het sjabloon en de opmaak |
| `bouw.py` | zet het bovenstaande in één bestand en rekent de CSP-hashes |
| `tests/` | 154 tests, waarvan 20 in een echte browser |
| `collect.sh` | leest op een Linux-host de bestanden die item 10.1 tot en met 10.4 nodig hebben, en maakt er een tarball van |

## Waar de inhoud vandaan komt

`app.js` bevat geen enkel item, geen enkele drempel en geen enkele uitleg. Alles komt uit
`regels.json`, en de koppeling naar de paden uit `paden.json`:

| Uit de bron | Wat de app ermee doet |
|---|---|
| `items` | de 41 rijen op het itemscherm, met label, doel en categorie |
| `items[].regel` | welke toets draait en met welke drempel |
| `bronnen` | wat je moet aanleveren: formaat, verplichte kolommen, hoe je de export maakt |
| `tijd` | de termijnen: een nmap-scan ouder dan zeven dagen is te oud, niet fout |
| `iamscan` | de shell-escapes, de beheerdersgroepen en de UID-grens |
| `paden.json` bladeren | het padenscherm: per chokepoint het bewijs, of de witte vlek |

Twee tests bewaken dat: geen label en geen uitleg uit `regels.json` mag in `app.js` staan, en de
drempels moeten via `param(regels, '4.4')` gelezen worden.

## Vijf uitkomsten, en waarom er vijf zijn

| Uitkomst | Betekenis |
|---|---|
| voldoet | de regel is gehaald |
| voldoet niet | de regel is niet gehaald |
| te oud | de inhoud klopt, maar het artefact is ouder dan de termijn |
| niet te lezen | het bestand mist een verplichte kolom, is kapot, of is een ander formaat |
| nog geen bewijs | er is niets geladen |

"Te oud" en "niet te lezen" apart houden van "voldoet niet" is het hele punt. Een verlopen scan is geen
open barriere, en een kapotte export is geen bevinding. Wie die drie op één hoop gooit, meet zijn eigen
exportproces in plaats van zijn beveiliging.

## De tijd komt uit de peildatum, nooit uit de klok

Elke termijn rekent vanaf `organisatie.peildatum` in het dossier. Zet je de peildatum een maand vooruit,
dan kantelt een scan van vorige week naar "te oud". Zonder dat zou dezelfde meting morgen een andere
uitslag geven en zou een dossier van vorige maand niet meer na te rekenen zijn.

`new Date()` mag maar op één plek staan, namelijk om het datumveld een standaardwaarde te geven; een test
telt de regels waarin het voorkomt.

## Wat de meting niet doet

**De meting rekent geen padstatus uit.** Ze levert per chokepoint een afgeleid antwoord (ja, nee,
onbekend) en exporteert dat naar de zelfcheck. Daar, en in `tools/score.py`, staat de enige beoordeling.
Een derde kopie van die regels in `app.js` zou een derde waarheid zijn.

Ze haalt ook niets op bij een bron: geen Graph API, geen Intune, geen SIEM. Je exporteert zelf, en dat
is met opzet, want het houdt de pagina offline en de gegevens bij jou.

## Witte vlekken

Van de 76 chokepoints in `paden.json` heeft 22 een meetregel. De overige 54 staan expliciet op het
padenscherm als witte vlek, met wat ervoor nodig zou zijn. Dat is geen tekortkoming die je wegpoetst
maar het eerlijke beeld: een groen dashboard over 22 van de 76 barrieres is geen dekking.

## Naar de zelfcheck

De knop *Antwoorden voor de zelfcheck* schrijft `zelfcheck-antwoorden-uit-meting-<datum>.json` met per
vraag het afgeleide antwoord en de items waar het vandaan komt. In de zelfcheck laadt de knop
*Antwoorden uit meting laden* dat bestand. Die vult alleen vragen die leeg of onbekend zijn: een
antwoord dat een mens zelf gaf blijft staan, en bij elke gevulde vraag komt een notitie met de datum en
de items. De check blijft van de mens; de meting levert bewijs aan.

## Tests

```bash
python -m pytest meting/tests -v
```

| Bestand | Wat het bewaakt |
|---|---|
| `test_regels.py` (13) | `regels.json` klopt met `paden.json`, elke bron wordt gebruikt, elk item heeft een chokepoint of een reden om het niet te hebben, de labels lopen woordelijk gelijk met de bron waar ze uit komen |
| `test_reken.py` (107) | elke `toets_`-functie op zijn fixture, de vijf uitkomsten, de termijnen vanaf de peildatum, de iamscan-analyse, en de export door `tools/score.py` |
| `test_bouw.py` (14) | één script en één stylesheet, de CSP-hashes kloppen, geen netwerk, geen kopie van de regels in `app.js`, de bouw is herhaalbaar |
| `test_app.py` (20) | de pagina in Chromium: bestanden kiezen, een tar uitpakken, een map laden, een document plakken, het dashboard, de uitdraai, en de vergelijking met `reken.py` |

De browsertests slaan zichzelf over als Playwright of Chromium ontbreekt; installeren doe je met
`pip install playwright && python -m playwright install chromium`. Elke fout in de browserconsole laat de
test falen.

`test_regels.py` bevat tests die zichzelf overslaan als `security-posture-tool` en `iamscan` niet naast
deze repo staan. De overname was eenmalig, dus de CI checkt die repo's niet uit; die repo's zijn
gearchiveerd.

## AI-hulp

Levert je beheersysteem andere kolomnamen dan een contract vraagt, dan zet de AI-hulp die om:
[/meting/ai/](https://security-commons-nl.github.io/aanvalspaden/meting/ai/), met je eigen sleutel bij
je eigen leverancier. Wat eruit komt is een voorstel; de meting toetst het pas na *Overnemen*, met
dezelfde regels als een gewoon bestand, en noteert dan dat de invoer met AI is omgezet. De tool zelf
praat met niemand: `default-src 'none'` en geen `fetch` in `app.js`. Zie `ai/LEESMIJ.md`.

## Een bron of een item toevoegen

1. Een regel bij in `regels.json`: een record in `bronnen` (formaat, verplichte kolommen, uitleg, hoe je
   de export maakt) en een record in `items` (label, doel, soort, regeltype, en het chokepoint uit
   `paden.json` waar het bewijs voor levert).
2. `toets_<bron>` in `reken.py`, en dezelfde functie in `bron/app.js` als `reken.toets_<bron>`. Beide
   retourneren `{verdicts, samenvatting, voorbeeld, artefact_datum, fouten}`.
3. Een fixture in `tests/fixtures/` via `maak_fixtures.py`, met een datum in `2026-08-…` zodat hij tegen
   peildatum `2026-09-03` het bedoelde verdict geeft.
4. Een test in `test_reken.py` en, als de bron een nieuw formaat is, één in `test_app.py`.

`test_elke_bron_wordt_gebruikt` en `test_elk_chokepoint_bestaat` vangen het als je stap 1 half doet.

## Valkuilen

- **Nooit de klok in een regel.** Alles vanaf de peildatum, anders is een dossier niet na te rekenen.
- **Geen `round()` voor percentages.** Python rondt 12,5 naar 12 en JavaScript naar 13. Gebruik
  `rond_half_omhoog`.
- **Geen `Number(waarde)` op een keuzelijst.** `Number('')` is 0 en wint elke minimumvergelijking. Lees
  een leeg veld als `null`; een test verbiedt `Number(` in `app.js`.
- **Datums met milliseconden.** `toISOString()` geeft `.000Z`; leest de datumlezer dat niet, dan valt
  stil elke termijn weg en is alles "voldoet". `test_datumlezer_spiegelt_python` bewaakt het.
- **Eén bestand, meer items.** De kroonjuwelenlijst, de firewallconfig en de SIEM-flow dekken elk
  meerdere items. De bestandskeuze hoort bij de bron, niet bij het item.
- **CSV-koppen** eerst naar kleine letters en gestript, BOM eraf. Een export uit Excel heeft vaak `;` als
  scheidingsteken; de lezer valt daarop terug.
- **Kapotte XML** geeft in de browser geen fout maar een document met `<parsererror>`. Daarop toetsen,
  anders wordt kapotte XML "voldoet" met nul bevindingen.
- **Gzip is niet byte-reproduceerbaar** over platforms. De fixture is een `.tar`; de test gzipt hem zelf.
- **Persoonsgegevens in exports.** Een export uit Entra of AD bevat namen en UPN's. Het dossier bewaart
  daarom hoogstens tien voorbeeldregels per item en nooit de ruwe export. Kijk het dossier na voor je het
  deelt; de voorbeeldregels staan er als gewone tekst in.

## Herkomst

De items en de toetsregels komen uit `security-posture-tool` en `iamscan`, overgenomen op de tag
`v0-applicatie`. Wat daarvan bewust afwijkt staat in [VERANTWOORDING.md](VERANTWOORDING.md).
