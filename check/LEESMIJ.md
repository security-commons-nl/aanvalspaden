# check/ - de zelfcheck (diepte 0)

Eén zelfstandig HTML-bestand: alle vragen, alle regels en alle opmaak zitten erin. Geen server, geen
account, geen telemetrie, geen enkele externe verwijzing. Wie hem offline wil draaien, slaat de pagina op.

**Live:** https://security-commons-nl.github.io/aanvalspaden/

## Bouwen

```bash
python check/bouw.py          # schrijft check/dist/index.html
python check/bouw.py site     # of naar een andere map
```

Het bouwscript zet `paden.json` en `bron/app.js` in één scripttag en `bron/app.css` in één style-tag, en
berekent daarna de sha256 van allebei voor het Content-Security-Policy in `bron/index.html`. Het
resultaat is dus:

```
default-src 'none'; script-src 'sha256-...'; style-src 'sha256-...'; img-src data:;
form-action 'none'; base-uri 'none'
```

Alles wat de pagina zou kunnen ophalen of versturen staat daarmee uit, en niet alleen in een belofte. Een
test rekent de hashes na op de inhoud, dus de regel kan niet stilletjes verlopen. Bijeffect: `fetch` en
inline `style`-attributen werken niet meer; dat laatste is de reden dat de voortgangsbalk een
`<progress>` is.

## Waar de inhoud vandaan komt

De app bevat geen eigen lijst met vragen, paden of drempels. Alles komt uit `paden.json`:

| Uit de bron | Wat de app ermee doet |
|---|---|
| `onderdelen` | de zeven schermen en de volgorde van de vragen |
| `chokepoints[].vraag` | claim, toelichting en wat niet meetelt |
| `vraag_id` | dezelfde vraag bij meer paden wordt één keer gesteld |
| `negatief` | ja is hier het ongunstige antwoord; de app zegt dat erbij |
| `opties` | eigen antwoordmogelijkheden (alleen bij het beheermodel, AP05) |
| `alleen_als` | vervolgvraag die vervalt als de vorige nee is |
| `regels` + `regels` per blad | de status per pad en de drie acties |

Een test controleert dat: geen pad-id en geen vraagtekst mag in `app.js` staan.

## Tests

```bash
python -m pytest check/tests/ -v
```

- `test_bouw.py` (8): de bron zit er ongewijzigd in, er is precies één script en één stylesheet, de
  CSP-hashes kloppen met de inhoud, er is geen externe verwijzing, de bouw is herhaalbaar, en er staat
  een kruimelpad terug naar de hoofdpagina (statuut B10).
- `test_app.py` (14): de app in Chromium. Klikken, opslaan, herladen, wissen, de vervolgvraag die
  verdwijnt. Daarna de drie doorlopen (alles ja, alles nee, alles onbekend) en, belangrijker, de
  vergelijking: dezelfde antwoorden moeten in de browser dezelfde uitslag geven als `tools/score.py` én
  als de zelfcheck waar de bron uit komt (`tests/fixtures/doorloop-2026-08-28.json`).
  De browsertests slaan zichzelf over als Playwright of Chromium ontbreekt; installeren doe je met
  `pip install playwright && python -m playwright install chromium`.

Elke fout in de browserconsole laat de test falen. Zo kwamen de twee bugs boven die het CSP veroorzaakte.

## Wat er nog niet is

Diepte 1 (kroonjuwelen tegen de open paden, bewijs per cel, risicolijst met eigenaar) komt hierbovenop, als
knop na de uitslag en niet als volgend scherm. De methode staat al beschreven in de kennisbank; zie
`methode/README.md`.
