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
