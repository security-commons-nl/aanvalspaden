# Wijzigingen aan de bron

`versie` in `paden.json` is jaar-maand. Elke inhoudelijke wijziging aan paden, chokepoints, vragen of regels
krijgt hier een regel, zodat een uitslag van later nog te plaatsen is tegen de bron van toen.

## 2026-08

- Eerste versie: 5 clusters, 18 bladeren (AP01 t/m AP18, AP17 als impact), 76 chokepoints, 1 randvoorwaarde.
  Gehaald uit de gecompileerde zelfcheck, model 1.0.
- Vragen dragen een `vraag_id`; dezelfde vraag bij meer paden wordt een keer gesteld.
- De scoreregels staan in de bron (`regels`, plus `regels` per blad) in plaats van in de app.
  Bewezen gelijk aan de app op een doorloop met 44 antwoorden.
- `onderdelen`: de zeven onderdelen en de vraagvolgorde, zodat de app zijn schermen uit de bron haalt.
- `check/`: de zelfcheck gebouwd vanaf deze bron, als één offline HTML-bestand.
- `mappingen/`: de normverankering. 44 barrieres verankerd in BIO 2.0 (en daarmee ISO 27001:2022) en in
  het Wpg-toetsingskader voor boa-organisaties, met per regel een sterkte en een reden. Een pagina met
  drie ingangen: vanuit het aanvalspad, vanuit de maatregel, en de witte vlekken. `paden.json` zelf is
  hiervoor niet gewijzigd.
- `mappingen/`: NIST CSF 2.0 en de AVG erbij, samen 333 regels over vier kaders. De volgorde van de
  kaders is redactioneel vastgelegd (`tools/mappingen.py`, VOLGORDE) in plaats van alfabetisch, want
  die volgorde bepaalt welk kader de pagina opent. De bedieningsbalk plakt bovenaan en wordt compact
  zodra de kop uit beeld is.
- `mappingen/handelingsperspectief.json`: per barriere waar de handleiding staat, en waar nog niet.
  14 van de 44 barrieres hebben er een; de overige 30 staan als openstaande schrijfopdracht met wat
  het artikel zou moeten dekken, gegroepeerd tot 11 clusters. Vierde weergave op de pagina, met per
  gat een knop naar een vooringevulde issue. `bouw.py` doet nu ook `node --check` op het script.
