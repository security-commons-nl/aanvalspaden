# De AI-hulp van de meting

Een aparte pagina (`/aanvalspaden/meting/ai/`) die met de API-sleutel van de gebruiker een export uit
een beheersysteem omzet naar het **kolomcontract** dat een meetregel verwacht. De meting zelf praat
nooit met een leverancier; alleen deze pagina, alleen op verzoek, alleen met de sleutel die de
gebruiker invult.

Het patroon komt uit [procescheck](https://github.com/security-commons-nl/procescheck/tree/main/ai) en
staat uitgewerkt in de bouwplannen `2026-09-03-ai-hulp.md` en `2026-09-03-ai-hulp-per-tool.md` in de
`.github`-repo. Wat dit voor een gebruiker betekent, staat op
[AI-hulp met je eigen sleutel](https://security-commons-nl.github.io/ai-hulp/).

| Bestand | Wat het doet |
|---|---|
| `opdrachten.json` | De opdracht: systeemprompt, toegestane invoer, vaste regels, leveranciers en grenzen. Data, geen code. |
| `haal_kern.py` | Haalt `kern.js` op uit procescheck en bewaakt met `--check` dat de kopie byte-identiek blijft. |
| `bron/kern.js` | De gedeelde kern: schemacontrole, chunking, samenvoegen, csv en xlsx lezen, citaatcontrole. Kent **geen** netwerk en gaat ook mee in de tool. |
| `bron/ai.js` | De zeven stappen van de pagina en de enige plek met `fetch`. |
| `bouw.py` | Zet opdrachten, contracten, kern en pagina in een bestand, met een CSP dat naar buiten mag: `connect-src https: http://localhost:*`. |
| `tests/fixtures/neem_op.py` | Neemt het voorbeeldantwoord een keer echt op. Daarna staat het in git en draaien de tests zonder sleutel. |

## Wat hier anders is dan bij procescheck

**Je kiest eerst een bron.** De meting kent dertig contracten; twintig daarvan zijn tabellen en die
staan in de keuzelijst. De pagina bouwt uit het gekozen contract de systeemprompt (welke kolommen) en
het JSON-schema (precies die kolommen, `additionalProperties: false`). Dertig schema's in
`opdrachten.json` zetten zou dezelfde tabel twee keer onderhouden; nu komt het uit `regels.json`.

**Alleen tabellen.** Een XML-config, een JSON-regelset, een geplakt rapport of een Linux-dump laat je
niet door een taalmodel herschrijven: dan toets je de tekst van het model in plaats van je eigen
export. Die formaten kies je in de tool als bestand, zoals altijd.

**Het samenvoegen gaat zonder sleutelveld.** `kern.voeg_stukken_samen` ontdubbelt op `code` of `id`;
een omgezette tabel heeft dat niet, want twee rijen mogen identiek zijn en de volgorde is de
identiteit. `ai.js` plakt de stukken daarom zelf achter elkaar.

**Het citaat wordt hier getoetst, niet in de tool.** De pagina heeft de invoer in het geheugen; de
tool krijgt alleen het voorstel, met de sha256 van de invoer en niet de invoer zelf. Daarom legt de
pagina per rij `bronregel_klopt` vast. De tool toont een rij die dat niet haalde, telt hem apart en
neemt hem **niet** mee in de toets.

## Hoe een omzetting loopt

1. Leverancier en sleutel (sessionStorage, weg bij het sluiten van de tab), verbinding testen.
2. Opdracht en bron kiezen; de pagina laat de kolommen van dat contract zien.
3. Invoer plakken of een `.csv`, `.md` of `.xlsx` kiezen; een xlsx wordt in de browser gelezen.
4. Toestemming per sessie: wat gaat waarheen, hoeveel aanroepen kost het.
5. Per stuk van hoogstens 24.000 tekens een aanroep, `temperature: 0`, eerst `json_schema`, bij een
   400 terugvallen op `json_object`, bij een 429 wachten (2, 4, 8 seconden).
6. Het voorstel opslaan: een JSON met de omgezette rijen, per rij het citaat en het oordeel daarover,
   plus de sha256 van de invoer. Nooit de invoer zelf, nooit de sleutel.
7. In de meting: *Voorstel laden*, kijken, en pas bij *Overnemen en toetsen* draait `reken.toets` op
   de omgezette tabel. De meting draagt daarna `herkomst_ai` en in de uitdraai staat "omgezet met AI".

## Een bron toevoegen

Niets. Voeg je in `meting/regels.json` een tabelcontract toe, dan staat het na `python meting/ai/bouw.py`
in de keuzelijst, met zijn kolommen in de prompt en het schema. Alleen als een contract géén tabel is,
hoort het er niet in; dat regelt `FORMAAT` in `bouw.py`.

## Tests

```
python -m pytest meting/ai/tests -v      25 tests
python meting/ai/haal_kern.py --check    kern.js is gelijk aan procescheck
```

De browsertests spelen de leverancier na met `page.route`; er gaat geen enkel verzoek naar buiten. De
laatste twee lopen de hele weg af: omzetten, opslaan, laden in de meting, toetsen, en controleren dat
een rij met een verzonnen citaat niet in de meting terechtkomt.

`meting/tests` en `meting/ai/tests` hebben elk een eigen `conftest.py` en kunnen niet in één
pytest-aanroep; CI draait ze als aparte stappen.
