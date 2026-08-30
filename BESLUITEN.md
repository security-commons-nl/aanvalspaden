# Besluiten

Append-only. Datum, besluit, één zin onderbouwing.

- **2026-08-28 · De keten heeft drie diepten met één bron.** Zelfcheck (antwoorden), risicoanalyse
  (kroonjuwelen en bewijs), meting (data), die alle drie `paden.json` lezen. Naast elkaar zetten zou
  betekenen dat dezelfde vragen op drie plekken uit elkaar lopen.
- **2026-08-28 · Achttien bladeren onder vijf clusters.** De zelfcheck werkt fijnmazig (AP01 t/m AP18), de
  matrix van de risicoanalyse werkt met vijf kolommen; tien kroonjuwelen maal achttien paden is niet in te
  vullen, maal vijf wel.
- **2026-08-28 · AP17 (ransomware) is type `impact`, geen pad.** Ransomware is het gevolg van een route, niet
  de voordeur; hij blijft wel in de zelfcheck staan, maar wordt geen kolom in de matrix.
- **2026-08-28 · De vraagmethodiek van de zelfcheck is de norm**, ook voor de bewijsvragen in de
  kennisbank-methode: claim, toelichting, wat niet telt, verificatie, actie.
- **2026-08-28 · Diepte 2 (meting) blijft voorlopig in `security-posture-tool`.** Eerst laat die tool zijn
  bevindingen op `paden.json` landen; pas als dat werkt, verhuist hij hierheen als `meting/`.
- **2026-08-28 · `paden.json` is eenmalig uit de gecompileerde zelfcheck gehaald** met
  `tools/uit_zelfcheck.py`, omdat de broncode nog niet beschikbaar was. Vanaf nu is `paden.json` de bron en
  is dat script alleen documentatie van de herkomst.
- **2026-08-28 · Teksten uit de zelfcheck zijn generiek gemaakt.** De bron sprak over "gemeentelijke
  gegevens" en "gemeentelijke processen"; dat is "van de organisatie" geworden, omdat de commons voor alle
  publieke organisaties publiceert (statuut A3).
- **2026-08-30 · De normverankering woont in deze repo als `mappingen/`, niet in een eigen repo.** Elke
  regel begint met een barriere-id uit `paden.json`; iets dat alleen betekenis heeft naast die bron, hoort
  ernaast te staan in plaats van in een tweede repo met een eigen schema en een eigen release-ritme.
- **2026-08-30 · De mapping hangt aan de barriere (`vraag_id`), niet aan het chokepoint.** De 76
  chokepoints delen 44 unieke barrieres met dezelfde claim en hetzelfde bewijs; per chokepoint mappen zou
  betekenen dat dezelfde vraag bij vier paden verschillend verankerd kan raken zonder dat het opvalt.
- **2026-08-30 · Er is precies een relatie: `levert-bewijs-voor`.** Geen "dekt af" en geen "voldoet aan".
  Een tweede relatie is het begin van een afvinklijst, en het oordeel over compliance is aan de auditor.
  Een test blokkeert op taal die compliance belooft.
- **2026-08-30 · Een raakvlak telt niet als dekking.** Een maatregel waar alleen raakvlakken op staan
  blijft een witte vlek, met die raakvlakken erbij. Anders geeft de pagina precies de valse zekerheid die
  dit instrument wil vermijden.
- **2026-08-30 · Elke barriere staat in `regels` of in `ongekoppeld`, met reden.** Stilte mag geen
  vergissing kunnen zijn: zo is het verschil zichtbaar tussen "hier is over nagedacht en het past niet" en
  "hier is niemand aan toegekomen".
- **2026-08-30 · BIO 2.0 en ISO 27001 zijn een mapping, niet twee.** BIO 2.0 volgt de nummering van
  ISO 27002:2022, dus maatregel `8.5` is beide; de overheidsmaatregelen eronder staan erbij.
- **2026-08-30 · Het Wpg-toetsingskader is meegenomen om de grens te laten zien.** Van de 36 maatregelen
  raakt de zelfcheck er acht. Dat is geen tekort maar het punt: een dreigingsgerichte check gaat niet over
  bewaartermijnen, verstrekking of de rechten van betrokkenen.
- **2026-08-30 · De bronbestanden dragen geen normteksten.** Alleen nummers, titels en eigen
  samenvattingen; de tekst van ISO 27002-maatregelen is auteursrechtelijk beschermd en hier niet nodig.
  Een test controleert dat er geen veld met normtekst insluipt.
- **2026-08-30 · De koppeling met de zelfcheck volgt in een tweede ronde.** Eerst de mapping laten
  reviewen zonder dat de zelfcheck ondertussen verandert; verschuift de mapping na review, dan hoeft
  `check/` maar een keer aangepast te worden.
- **2026-08-30 · Vier kaders, in een redactionele volgorde.** NIST CSF 2.0 en de AVG zijn toegevoegd naast
  BIO 2.0 en het Wpg-kader. De volgorde staat in `tools/mappingen.py` (`VOLGORDE`) en is niet alfabetisch:
  BIO 2.0 opent omdat dat het kader is waar de doelgroep op wordt bevraagd. Een kader dat niet in die
  volgorde staat, laat de tests falen.
- **2026-08-30 · NIST CSF blijft Engels, de AVG is een redactionele selectie.** CSF staat in het publieke
  domein, dus de uitkomstformuleringen staan er letterlijk in; ze blijven Engels omdat het kader zo heet.
  De AVG kent geen maatregelen maar artikelen, dus daar is gekozen voor de 32 artikelen die in een
  AVG-toets als toetspunt gelden.
- **2026-08-30 · De bedieningsbalk plakt bovenaan en wordt compact.** Met vier kaders en 106 maatregelen
  in het grootste kader is scrollen zonder filter onwerkbaar. De balk wordt compact zodra de kop uit beeld
  is, gemeten met een sentinel in plaats van op scrollpositie, want die klopt niet meer zodra een filter
  de paginahoogte verandert. Kop, balk en lijst zijn nu drie delen; alleen de lijst hertekent bij filteren.
- **2026-08-30 · Het handelingsperspectief hangt aan dezelfde barriere als de normverankering.** De
  zelfcheck zegt wat je moet doen, de kennisbank zegt hoe. Dat verband wordt vastgelegd per barriere,
  met een verwijzing naar item en paragraaf, en niet als losse links in lopende tekst.
- **2026-08-30 · Een ontbrekende handleiding is geen leeg vlak maar een uitnodiging.** Elke barriere
  zonder handleiding draagt een zin over wat het artikel zou moeten dekken, en op de pagina een knop
  naar een vooringevulde issue. Een kennisbank die alleen toont wat er ligt is een etalage; wat er
  ontbreekt is wat een commons nodig heeft.
- **2026-08-30 · De mapping loopt per barriere, de backlog groepeert tot schrijfopdrachten.** Per
  barriere is precies en toetsbaar; een artikel bedient er vaak drie. Zo blijft de lijst exact en de
  agenda haalbaar: 30 gaten worden 11 opdrachten.
- **2026-08-30 · De volgorde van de backlog komt uit de data, niet uit een mening.** Gewicht is het
  aantal aanvalspaden waarop een barriere staat. Een randvoorwaarde weegt over alle paden, anders zakt
  hij naar de bodem terwijl hij juist het breedst geldt.
- **2026-08-30 · `bouw.py` doet `node --check` op het script voor het de pagina in gaat.** Een
  syntaxfout maakte de hele app leeg zonder foutmelding; de browsertests vingen dat pas na dertig
  seconden wachten op een selector die nooit kwam. Nu valt de bouw meteen om, met de regel erbij.

## Open

- **Review van de mapping.** De 333 regels in `mappingen/` zijn een eerste versie zonder review van
  vakgenoten. Tot die review is gedaan, is elke regel een voorstel dat je met een issue kunt tegenspreken.
- **Broncode van de zelfcheck.** Nodig voor `check/` (diepte 0 en 1). Verwacht in
  `_wachtkamer/check-bron`. Zolang die er niet is, staan taak 3 en 5 tot en met 7 van het bouwplan stil.
- **Naam.** Deze repo heet `aanvalspaden` bij gebrek aan een gezamenlijk gekozen naam. Kiezen de eigenaren
  iets anders, dan is dat een hernoeming van de repo en van de titels; `paden.json` blijft ongewijzigd.
- **Maintainer-rol** voor de inbrenger van de zelfcheck op deze repo (handeling in GitHub, door een
  org-owner).

## 28-08-2026 · De bron dekt alle vragen van de zelfcheck

Een doorloop van de gecompileerde zelfcheck met echte antwoorden (alle 44 vragen, gemengd patroon) legde
twee gaten bloot in de omzetting naar `paden.json`:

1. Achttien velden hielden een niet-gedecodeerde escape over uit de JavaScript-bundel, waardoor woorden als
   "één" en "beïnvloeden" verminkt in de bron stonden. Opgelost in `tools/uit_zelfcheck.py`; een test
   bewaakt nu dat er geen escape meer in de bron staat.
2. Er waren 43 vragen gevonden waar de app er 44 stelt. De ontbrekende vraag (24/7 opvolging van kritieke
   meldingen) hoort bij geen enkel pad: hij weegt over de hele beoordeling mee. Daarom heeft de bron nu een
   `randvoorwaarden`-lijst naast de bladeren, met `werking` als uitleg waarom hij apart staat. `alle_vragen()`
   geeft precies 44.

**Waarom dit telt:** de bron is alleen bruikbaar als hij de app volledig dekt. Een vraag die stil wegvalt,
valt ook weg uit de risicoanalyse en de meting.

## 28-08-2026 · Diepte 2 landt op dezelfde chokepoints

De 37 checklist-items van `security-posture-tool` dragen nu een `pad` en een `chokepoint` uit `paden.json`
(tabel in `paden_map.py`). Drie items blijven bewust ongekoppeld, met reden vastgelegd: verantwoording aan
het bestuur, normconformiteit en AI-egressbeleid zijn geen barriere in een aanvalspad.

**Waarom dit telt:** hiermee is de keten rond. Een meting daar is het bewijs voor een cel hier, in plaats
van een tweede lijst die zijn eigen leven leidt.

## 29-08-2026 · Zelf bouwen vanaf de bron; de regels wonen in paden.json

De broncode van de zelfcheck is er niet en komt misschien niet. Wachten hield vijf taken stil. Besluit:
`check/` wordt gebouwd vanaf `paden.json`; de gecompileerde zelfcheck van de inbrenger is de
referentie-implementatie waar de nieuwe app tegen wordt getoetst. Herkomst blijft vastgelegd in
`tools/uit_zelfcheck.py` en hier. De inbrenger is hierover ingelicht voordat de app wordt gepubliceerd.

Daarvoor moest eerst de laatste eigen waarheid uit de app: de scoreregels. Die staan nu als data in de bron
(antwoorden, statussen, bepaling, uitzonderingen AP05 en AP17, weging van de acties, en per blad de sets
vereist, beperkt, reactief en plafond). `tools/score.py` leest ze en geeft op een echte doorloop van 44
antwoorden exact dezelfde achttien statussen en drie acties als de app; die doorloop staat als fixture.

Twee dingen die alleen in de regels zichtbaar werden: drie vragen zijn omgekeerd geformuleerd (ja = de
barriere ontbreekt) en de status van AP17 is de slechtste van dertien toegangspaden en de herstelbaarheid.

**Nog open, oordeel van de inbrenger nodig:** 57 van de 76 chokepoints zijn alleen preventief en maar 2
zijn detecterend; AP18 heeft geen enkele D of R. Dat is een inhoudelijke keuze, geen datafout.

## 29-08-2026 · De zelfcheck staat er, gebouwd vanaf de bron

De inbrenger gaf groen licht (en heeft zelf geen losse broncode; de gecompileerde HTML is wat er is).
`check/` is daarom nieuw gebouwd vanaf `paden.json`, als één zelfstandig HTML-bestand zonder bundler,
dependencies of externe verwijzingen. Live op https://security-commons-nl.github.io/aanvalspaden/.

**Waarom geen framework:** de app moet offline werken, controleerbaar niets versturen en over vijf jaar nog
te bouwen zijn. Een bouwscript van vijftig regels dat de bron in één scripttag zet, haalt dat; een
dependency-boom niet. Het Content-Security-Policy is `default-src 'none'` met een sha256 op script en
stylesheet, berekend bij het bouwen en nagerekend in een test. Daardoor is de offlinebelofte een
controleerbare eigenschap in plaats van een zin in de README.

**Bewijs dat app en bron niet uit elkaar lopen:** de browsertests draaien dezelfde antwoorden door de app,
door `tools/score.py` en langs de uitslag van de oorspronkelijke zelfcheck. Wijkt er één status af, dan is
de test rood. Een test verbiedt bovendien pad-ids en vraagteksten in `app.js`.

**Twee bugs die alleen een echte browser liet zien:** het CSP blokkeerde de inline `style` op de
voortgangsbalk (nu een `<progress>`), en een statusvlag in de legenda droeg hetzelfde `data-status` als een
pad. Beide gevonden doordat de tests elke consolefout laten falen.

**Nog open:** de D/R-verhouding blijft zoals ze is; de inbrenger bevestigde dat dat voor nu bewust is.
Diepte 1 (kroonjuwelen, bewijs per cel, risicolijst) komt hierbovenop.
