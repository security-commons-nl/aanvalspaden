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

## Open

- **Broncode van de zelfcheck.** Nodig voor `check/` (diepte 0 en 1). Verwacht in
  `_wachtkamer/check-bron`. Zolang die er niet is, staan taak 3 en 5 tot en met 7 van het bouwplan stil.
- **Naam.** Deze repo heet `aanvalspaden` bij gebrek aan een gezamenlijk gekozen naam. Kiezen de eigenaren
  iets anders, dan is dat een hernoeming van de repo en van de titels; `paden.json` blijft ongewijzigd.
- **Maintainer-rol** voor de inbrenger van de zelfcheck op deze repo (handeling in GitHub, door een
  org-owner).

## 28-08-2026 — De bron dekt alle vragen van de zelfcheck

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

## 28-08-2026 — Diepte 2 landt op dezelfde chokepoints

De 37 checklist-items van `security-posture-tool` dragen nu een `pad` en een `chokepoint` uit `paden.json`
(tabel in `paden_map.py`). Drie items blijven bewust ongekoppeld, met reden vastgelegd: verantwoording aan
het bestuur, normconformiteit en AI-egressbeleid zijn geen barriere in een aanvalspad.

**Waarom dit telt:** hiermee is de keten rond. Een meting daar is het bewijs voor een cel hier, in plaats
van een tweede lijst die zijn eigen leven leidt.
