# check/ (diepte 0 en 1)

Hier komt de app: de zelfcheck (diepte 0) en de risicoanalyse erbovenop (diepte 1), samen één offline
HTML-bestand.

**Wacht op:** de broncode van de zelfcheck (Vite-project). Zolang die er niet is, blijft deze map leeg en
slaat de CI de app-job over.

Zodra de bron er is:

1. De bron hierheen kopiëren, `node_modules/` en `dist/` weglaten.
2. De hardcoded vragen vervangen door `paden.json` uit de repo-root (via `src/lib/paden.ts`, met een kopie
   in `src/data/` die door een sync-test gelijk wordt gehouden).
3. Diepte 1 erbovenop: kroonjuwelen, de matrix met bewijs, de risicolijst met export.

De volledige stappen staan in het bouwplan: `2026-08-28-bouwplan-aanvalspaden-keten.md` (taak 3 en 5 tot en
met 7).
