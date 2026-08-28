# Bijdragen

Organisatiebrede regels: [CONTRIBUTING.md](https://github.com/security-commons-nl/.github/blob/main/CONTRIBUTING.md)
en het [redactiestatuut](https://github.com/security-commons-nl/.github/blob/main/REDACTIESTATUUT.md).

## Wat helpt

- **Een vraag die in jouw omgeving anders uitpakt.** Meld welke vraag, wat je antwoordde en waarom de
  uitkomst niet klopt. Dat is de beste bijdrage die er is.
- **Een ontbrekend aanvalspad of chokepoint.** Met een publieke bron erbij (NCSC, IBD, een openbaar
  incidentrapport).
- **Een scherpere formulering.** De vraagmethodiek is: wat claim je (`claim`), wat betekent dat
  (`toelichting`), wat telt niet mee (`telt_niet`), waar controleer je op (`verificatie`), en wat is de
  maatregel (`actie`).

## Regels voor wie code of data wijzigt

- **`paden.json` is de enige bron.** Vragen, paden en chokepoints staan daar, nooit in de code van `check/`
  of in de meting. Wie een vraag wil wijzigen, wijzigt de bron.
- **Bewijs is de scheidslijn.** In diepte 0 is "ja" een antwoord; in diepte 1 is een cel pas groen met een
  bewijslink. Code die dat door elkaar haalt, halen we eruit.
- **Nederlands** in code-commentaar, documentatie en commitboodschappen. Geen em-dashes.
- **Geen persoonsnamen, organisatienamen of e-mailadressen** in code, data, tests of documentatie
  (statuut A1 tot en met A3). Fictieve voorbeelden: Gemeente Duinstad, `duinstad.nl`.
- **Eén onderwerp per commit**, met de map als prefix (`paden:`, `check:`, `tools:`). Stage alleen de paden
  die je zelf hebt geraakt; nooit `git add -A`.
- **Tests groen** voordat je pusht:

```bash
python -m pytest tests/ -v
cd check && npx vitest run     # zodra check/ bestaat
```
