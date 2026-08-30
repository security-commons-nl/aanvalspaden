# Bouwplan: van aanvalspad naar norm (de crosswalk)

**Doel:** de vraag beantwoorden die elke CISO krijgt nadat hij de zelfcheck heeft gedaan: *en wat betekent
dit nu voor de BIO?* En de omgekeerde vraag erbij, die minstens zo belangrijk is: *waar houdt deze
zelfcheck op en begint de rest van het normenkader?*

**Aanleiding:** een reactie van een vakgenoot bij de IBD onder de aankondiging van de zelfcheck. Kort
samengevat: positioneer dit niet als alternatief naast de BIO, maar als de bewijslaag eronder, en koppel
een bevinding terug naar een maatregel en een risicohouder. Terecht punt. De omgekeerde beweging hoort er
alleen bij: als wij de koppeling leggen, moet ook zichtbaar zijn waar het normenkader iets vraagt waar
geen enkel aanvalspad over gaat. Dat is de witte vlekken-kaart.

**Architectuur:** een nieuwe map `mappingen/` in de bestaande repo `aanvalspaden`, als vierde schakel van
de keten (zelfcheck → risicoanalyse → meting → **normverankering**). Geen eigen repo: elke regel begint
met een barriere-id uit `paden.json`, en iets dat alleen betekenis heeft naast die bron hoort ernaast te
staan. Per kader een mappingbestand met regels, een bronbestand met de maatregelen, en één gegenereerde
offline HTML-pagina met drie ingangen.

**Tech stack:** Python 3.12 + pytest + jsonschema (mapping en validatie), vanilla JS (de pagina, geen
bundler, geen dependencies), GitHub Actions, JSON Schema voor de mappingen. Zelfde patroon als `check/`.

**Status:** gebouwd en getest op 30-08-2026. 105 tests groen. De mapping zelf wacht op review door
vakgenoten; tot die tijd is elke regel een goed onderbouwd voorstel, niet meer.

---

## 0. Spec (het besluit uit de spar van 30-08-2026)

1. **De spil is het chokepoint, de richting is pad → norm.** De crosswalk beantwoordt eerst de vraag
   "ik heb de zelfcheck gedaan, welke maatregelen heb ik hiermee aantoonbaar gemaakt". De omgekeerde
   ingang (vanuit de maatregel) rolt uit dezelfde data en kost niets extra.
2. **Drie kaders in ronde 1:** BIO 2.0, ISO 27001:2022 en het Wpg-toetsingskader voor boa's. De eerste
   twee zijn één mapping, want BIO 2.0 volgt de ISO 27002-nummering. Het Wpg-kader is er bewust bij om
   te laten zien dat niet alleen security telt. NIST CSF en SOC2 zijn ronde 2; het datamodel moet ze
   aankunnen, de inhoud komt later.
3. **De mapping woont in `aanvalspaden/mappingen/`,** niet in een eigen repo. Een aparte repo zou twee
   schema's opleveren die elkaars id's moeten kennen en een release-dans bij elke wijziging in de paden.
   Een gedeelde `kaders`-repo voor de normbronnen is een vervolgbesluit, geen onderdeel hiervan.
4. **De korrel is de barriere, niet het chokepoint.** De 76 chokepoints delen 44 unieke barrieres
   (`vraag_id`). Je schrijft op barriere-niveau; de pagina rolt op naar chokepoint, pad en cluster.
5. **Er is precies één relatie, met een richting: `levert-bewijs-voor`.** Nooit "dekt af", nooit "voldoet
   aan". Elke regel draagt een sterkte (`volledig`, `gedeeltelijk`, `raakvlak`) en een reden in één zin,
   zodat een reviewer hem kan tegenspreken zonder JSON te lezen.
6. **Een raakvlak telt niet als dekking.** Een maatregel waar alleen raakvlakken op staan blijft een witte
   vlek, mét die raakvlakken erbij. Anders geeft de pagina precies de valse zekerheid die dit instrument
   wil vermijden. (Dit besluit kwam uit een falende test, niet uit het ontwerp: W20 bewaartermijnen telde
   eerst als geraakt op grond van één raakvlak vanuit back-ups.)
7. **Stilte is nooit een vergissing.** Elke barriere staat in `regels` of in `ongekoppeld` met reden. Een
   test blokkeert als een barriere in geen van beide staat.
8. **Volledig bouwen, daarna review.** Geen proefcluster en geen `voorstel`-status in de data: alle 44
   barrieres in alle kaders, en de review loopt via issues en pull requests zoals elke andere bijdrage.
9. **Geen normteksten in de repo.** De bronbestanden dragen nummers, titels en eigen samenvattingen. De
   tekst van ISO 27002-maatregelen is auteursrechtelijk beschermd en hier niet nodig; een test bewaakt
   dat er geen veld met normtekst insluipt.
10. **De koppeling met de zelfcheck is ronde 2.** Eerst de mapping laten reviewen zonder dat `check/`
    ondertussen verandert.

## Globale regels

- Werkmap: `<werkmap>/aanvalspaden\`.
- **Redactiestatuut** `.github/REDACTIESTATUUT.md`: Nederlands, geen persoonsnamen, geen em-dashes,
  Engelse vaktermen blijven Engels.
- **Commits:** Nederlands, één onderwerp, map als prefix (`mappingen: ...`). Stage alleen expliciete
  paden; nooit `git add -A`. Geen AI-attributie.
- **Tests eerst.** Elke taak: falende test, dan implementatie, dan groen, dan commit.

---

## Taak 1: De bronnen

- [x] `mappingen/bronnen/genereer_bio2.py` leest `cisochat/data/bio2.json` en groepeert de 148
      overheidsmaatregelen naar 89 ISO-maatregelen (`5.01.01` hoort bij `5.1`). Overgenomen: nummer,
      titel, thema, de sub-ids. Niet overgenomen: de ISO-tekst.
- [x] `mappingen/bronnen/bio2.json` met `herkomst` en de commit-hash van de bron, zodat de kopie te
      herleiden is.
- [x] `mappingen/bronnen/wpg.json` met de 31 beheersingsmaatregelen uit de NOREA-handreiking
      (versie 2024 1.0, geldig vanaf 03-09-2024) plus de vijf technische maatregelen uit bijlage 4, elk
      met nummer, titel, Wpg-artikel, thema en een eigen samenvatting.
- [x] Test: de BIO2-bron draagt alleen toegestane velden; het Wpg-kader heeft 31 + 5 maatregelen.

**Vondst tijdens het bouwen:** de titel van BIO2-maatregel 5.02 was in de gedeelde dataset afgekapt tot
"informatiebeveiligin". Gerepareerd in `cisochat` (de bron), niet in de kopie.

## Taak 2: Het schema en de mapping

- [x] `mappingen/mapping.schema.json`: `kader`, `versie`, `toelichting`, `regels`, `ongekoppeld`. Een
      regel heeft `barriere`, `norm`, `relatie` (const), `sterkte` (enum), `reden` (25 tot 400 tekens).
- [x] `mappingen/bio2.json`: 118 regels over 44 barrieres. 44 van de 89 maatregelen krijgen bewijs.
- [x] `mappingen/wpg.json`: 62 regels over 41 barrieres, 4 barrieres expliciet ongekoppeld. 8 van de 36
      maatregelen krijgen bewijs.
- [x] `tools/mappingen.py`: de helper waarmee alles wordt opgezocht, inclusief `witte_vlekken()` en
      `dekking()`.

## Taak 3: De tests

- [x] `tests/test_mappingen.py`, 33 tests: schema, bestaande barrieres en maatregelen, geen dubbele
      paren, één relatie, geen taal die compliance belooft, redenen zonder em-dash, elke barriere gemapt
      of ongekoppeld, raakvlakken tellen niet als dekking, de Wpg-dekking blijft een minderheid.
- [x] Test die bewaakt dat chokepoints met hetzelfde `vraag_id` dezelfde claim en hetzelfde bewijs
      houden. Zonder die garantie is mappen op barriere-niveau niet houdbaar.

## Taak 4: De pagina

- [x] `mappingen/bouw.py`, zelfde patroon als `check/bouw.py`: één offline HTML-bestand, alle data
      meegebakken, CSP `default-src 'none'` met sha256 op script en stylesheet.
- [x] `mappingen/bron/{index.html,app.css,app.js}`: drie weergaven (vanuit het pad, vanuit de maatregel,
      witte vlekken), kaderkeuze, zoeken.
- [x] `mappingen/tests/test_crosswalk_bouw.py` (9 tests) en `test_crosswalk_app.py` (10 browsertests met
      Playwright).
- [x] `mappingen/tests/conftest.py` laadt `bouw.py` als `crosswalk_bouw`, omdat `check/` ook een
      `bouw.py` heeft en een gezamenlijke pytest-run anders de verkeerde module toetst.

## Taak 5: Inbedding

- [x] `mappingen/LEESMIJ.md`: de belofte, de korrel, de kaders, auteursrecht, bouwen en testen.
- [x] `README.md`: sectie "Van aanvalspad naar norm", de dieptetabel en de mappenlijst.
- [x] `CHANGELOG.md` en `BESLUITEN.md` (negen besluiten, plus de review als open punt).
- [x] `.github/workflows/ci.yml`: job `mappingen` die bouwt en test in een echte browser.
- [x] `.github/workflows/pages.yml`: publiceert naar `/normen/`, met de mappingbestanden als download.
- [x] Org-profiel: de projectomschrijving van `aanvalspaden` noemt de normverankering. Voorpagina,
      `llms.txt` en `sitemap.xml` volgen daaruit (statuut B9) en zijn opnieuw gegenereerd.
- [x] Kennisbank `security/risicoanalyse-aanvalspaden/`: de alinea "Geen audit" verwijst nu door voor de
      vertaling naar normen, en de samenhangtabel heeft een vijfde stap. README en leesversie allebei.
- [x] Commons `CLAUDE.md`: routing-trigger en projectbeschrijving.

## Taak 6 (ronde 2, na de review): de zelfcheck-koppeling

- [ ] Onderaan het resultaatscherm van de zelfcheck: "met deze antwoorden heb je bewijs voor ..." Raakt
      `check/bouw.py`, `check/bron/app.js` en de bestaande browsertests.
- [ ] Alleen barrieres waar de gebruiker daadwerkelijk bewijs claimt tellen mee. Een "ja" zonder bewijs is
      in diepte 0 een antwoord, geen bewijs; die scheidslijn mag niet vervagen.

## Vervolgbesluiten (niet in dit plan)

- **Een `kaders`-repo** voor de normbronnen, zodra een derde project ze leest. Nu leest `cisochat` de
  BIO2-dataset en `aanvalspaden` een afgeleide kopie; bij een derde lezer is het tijd. Dan is ook de
  plek om de licentievraag per kader één keer vast te leggen in plaats van per project.
- **NIST CSF 2.0 en SOC2** als vierde en vijfde kader. SOC2 is vooral interessant voor de
  leveranciersvraag ("mijn leverancier is SOC2 type II, wat dekt dat van mijn aanvalspaden"), en die
  vraag sluit aan op het gat dat het Wpg-kader zichtbaar maakt bij verwerkers.

## Definitie van klaar

- [x] `python -m pytest tests/ mappingen/tests/ check/tests/ -q` groen (105 tests).
- [x] `python mappingen/bouw.py` levert een pagina zonder externe verwijzingen, met kloppende CSP-hashes.
- [x] Statuutcontrole groen (`repo_compliance.py`), kennisbank-build groen.
- [x] Elke barriere in elk kader staat in `regels` of in `ongekoppeld`.
- [ ] Review door vakgenoten verwerkt. **Openstaand; dit is de volgende stap.**
