# Bouwplan: de aanvalspaden-keten (zelfcheck → risicoanalyse → meting)

> **Voor agentische uitvoerders:** gebruik `superpowers:subagent-driven-development` (aanbevolen) of
> `superpowers:executing-plans` en werk taak voor taak. Stappen hebben checkbox-syntax (`- [ ]`).
> Lees eerst §0 (de spec) en §Globale regels. Een taak is pas klaar als de test in die taak groen is
> en de commit gedaan is. Sla niets over, vul niets "later" in.

**Doel:** één instrument in drie diepten dat een CISO of ISO van "welke aanvalspaden staan open" (zelfcheck,
een uur, alleen) naar "welke risico's, welke maatregel, welke eigenaar" (risicoanalyse, een dag, met de lijn)
naar "bewijs uit echte data" (meting) brengt, met één gedeelde bron voor de aanvalspaden.

**Architectuur:** een nieuwe repo onder `security-commons-nl` met `paden.json` als enige bron van waarheid voor
de aanvalspaden, `check/` (de zelfcheck, React + Vite, broncode van de CISO van een collega-gemeente) die in
een tweede helft de risicoanalyse-stappen krijgt, `methode/` als leeswijzer die verwijst naar het
kennisbank-item, en later `meting/` (de huidige `security-posture-tool`) die zijn bevindingen op dezelfde
paden en chokepoints laat landen. Alles statisch, offline, EUPL-1.2.

**Tech stack:** React + Vite + TypeScript + vitest (check), Python 3.12 + pytest (paden-validatie, meting),
GitHub Actions (org-workflows `python-ci.yml`, `pages-docs.yml` uit `security-commons-nl/.github`), JSON
Schema voor `paden.json`.

**Spec:** §0 van dit document. Er is geen aparte spec; de spar van 28-08-2026 is hieronder samengevat.

---

## Stand van uitvoering (28-08-2026, einde van de dag)

| Taak | Stand |
|---|---|
| 0 Voorwaarden | **Besluit 29-08:** zelf bouwen vanaf `paden.json`; de gecompileerde zelfcheck is de referentie. Inbrenger wordt ingelicht voor publicatie |
| 1 Repo-skelet | Klaar, gepusht, CI groen |
| 2 `paden.json` + schema | Klaar, 29-08 uitgebreid: scoreregels als data, `vraag_id` per chokepoint, `tools/score.py` als referentie, exact gelijk aan de app op een doorloop van 44 antwoorden; 30 tests groen |
| 3 t/m 7 (`check/`) | Vrij om te bouwen vanaf de bron (besluit 29-08); wacht op het ja van de inbrenger en op het D/R-oordeel |
| 8 Meting op `paden.json` | Klaar: 37 items gekoppeld of met reden ongekoppeld, 135 tests groen in de posture-tool |
| 9 Verwijzingen | Klaar: org-profiel, statuut (B1), commons-CLAUDE.md, llms.txt |
| 10 Posture-tool verhuizen | Nog niet: apart besluit, pas zinvol als `check/` draait |

De doorloop met Playwright zit in `_wachtkamer/check-bron/2026-08-28-testdoorloop-resultaat.png`; die
staat bewust buiten de repo, want het is de app van een ander tot hij zelf publiceert.

---

## 0. Spec (samenvatting van het besluit)

1. **Drie diepten, één keten.** 0 zelfcheck (antwoorden, 18 paden, drie acties) · 1 risicoanalyse
   (kroonjuwelen × open paden, bewijs, eigenaar) · 2 meting (bewijs uit data). Diepte 1 is een knop na
   diepte 0, geen verplicht volgend scherm. Wie stopt na 0, heeft iets bruikbaars.
2. **Eén `paden.json`.** Vijf clusters (de paden uit de kennisbank-methode) met daaronder de achttien
   bladeren uit de zelfcheck (AP01 t/m AP18). DDoS (AP15, AP16) wordt overgenomen als blad onder cluster 3.
   AP17 (ransomware) is geen pad maar de impact/herstelbaarheid-as; hij blijft in de zelfcheck, maar krijgt in
   `paden.json` het type `impact`, niet `pad`.
3. **Vraagmethodiek van de zelfcheck is de norm**, ook voor de bewijsvragen in de kennisbank: per vraag een
   claim, een toelichting, wat níet telt, en de actie.
4. **Bewijs blijft de scheidslijn.** In diepte 0 is "ja" een antwoord. In diepte 1 is een cel pas groen met een
   bewijslink. De code mag die twee nooit door elkaar laten lopen.
5. **Naam:** één naam voor de keten. Standaard `aanvalspaden` (repo `security-commons-nl/aanvalspaden`,
   titel "Aanvalspaden: van zelfcheck tot risicolijst"). Als de eigenaren een andere naam kiezen, vervang
   je overal het woord `aanvalspaden` door die naam; verder verandert er niets aan dit plan.
6. **Eigenaarschap:** de CISO van de collega-gemeente is maintainer van de repo (GitHub-rol). In de inhoud
   geen namen (statuut A1). Broncode onder EUPL-1.2.
7. **Posture-tool:** blijft voorlopig in zijn eigen repo, maar laat bevindingen landen op `paden.json`
   (Taak 8). Verhuizing als `meting/` via `git subtree` is Taak 9 en gebeurt pas als Taak 8 werkt.
8. **Kennisbank-item `risicoanalyse-aanvalspaden`** blijft de leesbare methode en het papieren sjabloon; het
   verwijst naar het instrument, en het instrument naar de methode.

## Globale regels (gelden voor elke taak)

- Werkmap: de map waarin alle repo's van security-commons-nl naast elkaar staan.
- **Redactiestatuut** `<werkmap>/.github\REDACTIESTATUUT.md`: Nederlands; geen persoonsnamen,
  organisatienamen als herkomst, e-mailadressen of links naar sociale media in code, data, tests of docs; geen
  `auteur:`-velden; geen em-dashes (schrijf komma of dubbele punt); Engelse vaktermen blijven Engels.
- **Commits:** Nederlands, één onderwerp, map als prefix (`check: ...`, `paden: ...`). Stage alleen
  expliciete paden; **nooit `git add -A`**. Geen `Co-Authored-By`, geen sessie-links. Kopieer eerst de
  commit-msg-hook: `cp <werkmap>/kennisbank/.git/hooks/commit-msg <repo>/.git/hooks/commit-msg`.
- **Fictieve data in tests en voorbeelden:** organisatie "Gemeente Duinstad", domein `duinstad.nl`, namen
  alleen als rol ("de CISO"). Nooit echte gemeenten.
- **Tests eerst.** Elke taak: falende test, dan implementatie, dan groen, dan commit. Python: `python -m pytest
  tests/ -v`. TypeScript: `npx vitest run`.
- **Node 24, Python 3.12+** zijn aanwezig. `pandoc` voor HTML uit markdown.
- Bij een rode "in gebruik/EBUSY"-fout: 2 seconden wachten, één keer opnieuw.
- Als een stap een keuze vraagt die niet in dit plan staat: kies de eenvoudigste optie, schrijf de keuze in
  `BESLUITEN.md` in de repo-root (datum, keuze, één zin waarom), en ga door.

---

## Taak 0: Voorwaarden controleren (poort, geen code)

**Bestanden:** geen. Dit is een controle vóór Taak 1.

- [ ] **Stap 1: Bron van de zelfcheck aanwezig?** Controleer dat er een map is met de broncode van de
  zelfcheck (een Vite-project: `package.json` met `vite` erin, `src/` met `.tsx`- of `.jsx`-bestanden, en de
  vragen ergens als data of in componenten). Verwachte plek: `<werkmap>/_wachtkamer\check-bron\`.
  Ontbreekt hij: **stop** en meld "Taak 0: broncode zelfcheck ontbreekt in `_wachtkamer\check-bron`". Alleen
  de gecompileerde `Gemeentelijke-weerbaarheidscheck-offline.html` is niet genoeg.
- [ ] **Stap 2: Naam vastgesteld?** Zoek `<werkmap>/_wachtkamer\NAAM.txt`. Staat er één woord in,
  dan is dat de naam. Ontbreekt het bestand: gebruik `aanvalspaden` en maak het bestand aan met die inhoud.
- [ ] **Stap 3: Licentie en maintainer.** Controleer in de bronmap op een `LICENSE`. Is hij niet EUPL-1.2 of
  ontbreekt hij: kopieer `<werkmap>/kennisbank\LICENSE` erbij in Taak 1 en noteer in
  `BESLUITEN.md`: "licentie EUPL-1.2 toegepast op de bron van de zelfcheck; bevestigd door de eigenaren op
  [datum uit NAAM.txt-map of 'nog te bevestigen']". De GitHub-maintainer-rol is een handeling in de
  browser door de org-owner; noteer in `BESLUITEN.md` als "open: maintainer-rol toekennen".

---

## Taak 1: Repo-skelet

**Bestanden:**
- Create: `aanvalspaden/README.md`, `aanvalspaden/LICENSE`, `aanvalspaden/CONTRIBUTING.md`,
  `aanvalspaden/BESLUITEN.md`, `aanvalspaden/.gitignore`, `aanvalspaden/.github/workflows/ci.yml`
- Create: `aanvalspaden/tests/test_skelet.py`

**Interfaces:**
- Produces: mapstructuur `paden.json` (root), `check/`, `methode/`, `tests/`, `tools/`.

- [ ] **Stap 1: Repo aanmaken op GitHub en lokaal**

```bash
cd <werkmap>
gh repo create security-commons-nl/aanvalspaden --public --description "Aanvalspaden: van zelfcheck tot risicolijst tot meting. Eén bron voor de aanvalspaden van de publieke sector." --clone
cd aanvalspaden
cp ../kennisbank/.git/hooks/commit-msg .git/hooks/commit-msg
cp ../kennisbank/LICENSE LICENSE
mkdir -p check methode tests tools .github/workflows
```

- [ ] **Stap 2: Schrijf de falende skelet-test** in `tests/test_skelet.py`:

```python
"""De repo heeft de vaste structuur; deze test beschermt die."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_vaste_mappen_en_bestanden_bestaan():
    for pad in ("README.md", "LICENSE", "CONTRIBUTING.md", "BESLUITEN.md", ".gitignore",
                "check", "methode", "tools", ".github/workflows/ci.yml"):
        assert (ROOT / pad).exists(), f"ontbreekt: {pad}"


def test_licentie_is_eupl():
    assert "EUROPEAN UNION PUBLIC LICENCE" in (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_geen_em_dash_in_docs():
    for pad in ("README.md", "CONTRIBUTING.md", "BESLUITEN.md"):
        assert "\u2014" not in (ROOT / pad).read_text(encoding="utf-8"), f"em-dash in {pad}"
```

- [ ] **Stap 3: Run, verwacht FAIL**

```bash
python -m pytest tests/test_skelet.py -v
```
Verwacht: FAIL op `README.md` ontbreekt.

- [ ] **Stap 4: Schrijf de bestanden**

`README.md`:

```markdown
# Aanvalspaden: van zelfcheck tot risicolijst tot meting

> **Status: prototype** (redactiestatuut B8). Werkt en is te draaien, zonder belofte over volledigheid.

Eén instrument in drie diepten voor de CISO of ISO van een publieke organisatie:

| Diepte | Wat | Invoer | Tijd | Uitkomst |
|---|---|---|---|---|
| 0. Zelfcheck | Achttien aanvalspaden, korte vragen | Eigen antwoorden | Een uur, alleen | Welke paden staan open, drie acties voor morgen |
| 1. Risicoanalyse | Kroonjuwelen tegen de open paden | Antwoorden plus bewijs | Een dag, met de lijn | Risicolijst met maatregel, eigenaar, termijn |
| 2. Meting | Dezelfde paden, uit echte data | Exports, connectors | Techniek, doorlopend | Bewijs per cel, automatisch (volgt) |

Diepte 0 en 1 zitten in één offline HTML-bestand (`check/`). Diepte 2 is de
[security-posture-tool](https://github.com/security-commons-nl/security-posture-tool), die zijn bevindingen op
dezelfde paden laat landen; verhuizing naar deze repo volgt.

## De bron: `paden.json`

Alle drie de diepten lezen dezelfde `paden.json`: vijf clusters, achttien bladeren, per blad de chokepoints
en de vragen (claim, toelichting, wat niet telt, actie). Wijzig een pad hier, en check, methode en meting
volgen. Schema: `tools/paden.schema.json`; validatie: `python -m pytest tests/`.

## De methode (leesbaar)

De vier stappen met de lijn, en het papieren sjabloon, staan in de kennisbank:
[Risicoanalyse langs aanvalspaden](https://security-commons-nl.github.io/kennisbank/security/risicoanalyse-aanvalspaden/).
`methode/` in deze repo bevat alleen de leeswijzer en de koppeling.

## Zelf draaien

```bash
cd check && npm ci && npm run build      # levert check/dist/index.html, offline bruikbaar
python -m pytest tests/ -v               # valideert paden.json en de structuur
```

## Herkomst

De zelfcheck is ontwikkeld door de CISO-organisatie van een Nederlandse gemeente en met toestemming
ingebracht; de methode komt uit de kennisbank van security-commons-nl. Licentie: EUPL-1.2.

## Bijdragen

Zie [CONTRIBUTING.md](CONTRIBUTING.md). Een issue of discussion is een volwaardige bijdrage.
```

`CONTRIBUTING.md`:

```markdown
# Bijdragen

Organisatiebrede regels: [CONTRIBUTING.md](https://github.com/security-commons-nl/.github/blob/main/CONTRIBUTING.md)
en het [redactiestatuut](https://github.com/security-commons-nl/.github/blob/main/REDACTIESTATUUT.md).

## Wat helpt

- **Een vraag die anders uitpakt in jouw omgeving.** Meld welke vraag, wat je antwoordde en waarom de
  uitkomst niet klopt.
- **Een ontbrekend aanvalspad of chokepoint.** Met een publieke bron erbij (NCSC, IBD, incidentrapport).
- **Een bewijsvraag die scherper kan.** De vraagmethodiek is: claim, toelichting, wat niet telt, actie.

## Voor wie een pull request doet

- `paden.json` is de enige bron; wijzig nooit vragen in de code van `check/` als ze in `paden.json` horen.
- Nederlands in code-commentaar, documentatie en commits; één onderwerp per commit, map als prefix.
- Geen persoonsnamen, organisatienamen of e-mailadressen (statuut A1 tot en met A3). Fictieve data:
  Gemeente Duinstad.
- Tests groen: `python -m pytest tests/ -v` en `cd check && npx vitest run`.
```

`BESLUITEN.md`:

```markdown
# Besluiten

Append-only. Datum, keuze, één zin waarom.

- 2026-08-28: keten in drie diepten (zelfcheck, risicoanalyse, meting) met één `paden.json` als bron;
  de zelfcheck is de instap, de methode uit de kennisbank het vervolg, de posture-tool de meting.
- 2026-08-28: naam `aanvalspaden` tenzij de eigenaren anders kiezen (zie `_wachtkamer/NAAM.txt`).
```

`.gitignore`:

```
node_modules/
dist/
__pycache__/
*.pyc
.venv/
.env
.DS_Store
```

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Structuur en paden.json via de herbruikbare org-workflow.
  paden:
    uses: security-commons-nl/.github/.github/workflows/python-ci.yml@main
    with:
      python-version: "3.12"
      test-command: "python -m pytest tests/ -v"
      install-extras: "pytest jsonschema"

  # De zelfcheck: eigen tests en een build die een offline HTML oplevert.
  check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: check
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: check/package-lock.json
      - run: npm ci
      - run: npx vitest run
      - run: npm run build
      - name: Build levert één offline bestand
        run: test -s dist/index.html
```

- [ ] **Stap 5: Run, verwacht PASS**

```bash
python -m pytest tests/test_skelet.py -v
```
Verwacht: 3 passed.

- [ ] **Stap 6: Commit**

```bash
git add README.md LICENSE CONTRIBUTING.md BESLUITEN.md .gitignore .github/workflows/ci.yml tests/test_skelet.py
git commit -m "repo: skelet van de aanvalspaden-keten"
git push -u origin main
```

De `check`-job in CI faalt nu nog (er is geen `check/package.json`); dat is verwacht tot Taak 3.

---

## Taak 2: `paden.json` met schema en validatie

**Bestanden:**
- Create: `aanvalspaden/paden.json`, `aanvalspaden/tools/paden.schema.json`, `aanvalspaden/tools/paden.py`
- Create: `aanvalspaden/tests/test_paden.py`

**Interfaces:**
- Produces: `paden.json` met de structuur hieronder; `tools/paden.py` met
  `laad() -> dict`, `bladeren() -> list[dict]`, `cluster_van(ap_id: str) -> dict`.
  Latere taken (4, 5, 8) lezen `paden.json` via deze structuur; verander de veldnamen niet.

**Structuur van `paden.json`** (dit is de norm; alle veldnamen exact zo):

```json
{
  "versie": "2026-08",
  "toelichting": "Eén bron voor de aanvalspaden van de publieke sector. Vijf clusters, achttien bladeren. Wijzig hier, niet in de code.",
  "clusters": [
    {
      "id": "C1",
      "titel": "Gecompromitteerd account",
      "kern": "Phishing, adversary-in-the-middle, hergebruikte wachtwoorden, MFA-moeheid: de aanvaller logt in als de gebruiker.",
      "bladeren": ["AP01", "AP02", "AP03", "AP04", "AP06", "AP07"]
    }
  ],
  "bladeren": [
    {
      "id": "AP01",
      "titel": "Phishing → accountovername",
      "type": "pad",
      "scenario": "Een aanvaller onderschept een login via een nagemaakte tussenpagina (AiTM).",
      "chokepoints": [
        {
          "id": "AP01-1",
          "titel": "Phishing-resistente authenticatie afgedwongen",
          "vraag": {
            "claim": "Wordt inloggen met passkeys of een gelijkwaardig sterke methode afgedwongen?",
            "toelichting": "Beschikbaar stellen is niet genoeg. Zwakkere methoden mogen de eis niet kunnen omzeilen.",
            "telt_niet": "Dat niemand de zwakke methode gebruikt. Ze moet uit staan, ook voor uitzonderingen en herstelroutes.",
            "actie": "Dwing authentication strength met FIDO2/passkeys of Windows Hello for Business af; controleer alle apps, gebruikers en uitzonderingen."
          },
          "drp": ["P"],
          "bewijs": "Export van het Conditional Access-beleid met authentication strength, plus de lijst uitzonderingen."
        }
      ],
      "bronnen": ["NCSC: factsheet phishing-resistente MFA"]
    }
  ]
}
```

Regels voor de inhoud:
- Vijf clusters met exact deze id's en titels: `C1 Gecompromitteerd account` (AP01, AP02, AP03, AP04, AP06,
  AP07) · `C2 Werkplek via de gebruiker` (AP08, AP09, AP10, AP11) · `C3 Kwetsbare internetgerichte dienst`
  (AP12, AP13, AP14, AP15, AP16) · `C4 Leverancier en keten` (AP18) · `C5 Misbruik van beheerrechten` (AP05).
- AP17 (`Ransomware → gemeentelijke uitval`) krijgt `"type": "impact"` en staat in geen enkel cluster; hij
  blijft wel in `bladeren` zodat de zelfcheck hem kan tonen.
- De achttien titels komen letterlijk uit de zelfcheck (de labels met een pijl, zoals `Phishing →
  accountovername`). Vervang in titels het woord "gemeentelijke" door "publieke" (AP17: `Ransomware →
  uitval van dienstverlening`; AP18: `Leveranciersincident → impact op de dienstverlening`).
- Per blad minimaal twee chokepoints; elke chokepoint heeft één vraag in de vier velden (claim, toelichting,
  telt_niet, actie), een `drp`-lijst met een of meer van `"D"`, `"R"`, `"P"`, en een `bewijs`-zin: welk
  artefact groen maakt in diepte 1. De vragen neem je over uit de zelfcheck (bron: `check/src`, na Taak 3)
  en uit `<werkmap>/kennisbank\security\risicoanalyse-aanvalspaden\aanvalspaden.md`
  (chokepoints en bewijsvragen per pad). Waar beide een vraag hebben over hetzelfde chokepoint, wint de
  formulering van de zelfcheck.
- Geen organisatienamen, geen productnamen als eis (Entra, Defender mogen als *voorbeeld* in `actie`, nooit in
  `claim`).

- [ ] **Stap 1: Schrijf het schema** `tools/paden.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "paden.json",
  "type": "object",
  "required": ["versie", "toelichting", "clusters", "bladeren"],
  "additionalProperties": false,
  "properties": {
    "versie": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}$"},
    "toelichting": {"type": "string", "minLength": 20},
    "clusters": {
      "type": "array", "minItems": 5, "maxItems": 5,
      "items": {
        "type": "object", "required": ["id", "titel", "kern", "bladeren"], "additionalProperties": false,
        "properties": {
          "id": {"type": "string", "pattern": "^C[1-5]$"},
          "titel": {"type": "string", "minLength": 5},
          "kern": {"type": "string", "minLength": 20},
          "bladeren": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^AP[0-9]{2}$"}}
        }
      }
    },
    "bladeren": {
      "type": "array", "minItems": 18, "maxItems": 18,
      "items": {
        "type": "object",
        "required": ["id", "titel", "type", "scenario", "chokepoints", "bronnen"],
        "additionalProperties": false,
        "properties": {
          "id": {"type": "string", "pattern": "^AP[0-9]{2}$"},
          "titel": {"type": "string", "pattern": "→"},
          "type": {"enum": ["pad", "impact"]},
          "scenario": {"type": "string", "minLength": 20},
          "chokepoints": {
            "type": "array", "minItems": 2,
            "items": {
              "type": "object",
              "required": ["id", "titel", "vraag", "drp", "bewijs"],
              "additionalProperties": false,
              "properties": {
                "id": {"type": "string", "pattern": "^AP[0-9]{2}-[0-9]+$"},
                "titel": {"type": "string", "minLength": 5},
                "vraag": {
                  "type": "object",
                  "required": ["claim", "toelichting", "telt_niet", "actie"],
                  "additionalProperties": false,
                  "properties": {
                    "claim": {"type": "string", "pattern": "\\?$"},
                    "toelichting": {"type": "string", "minLength": 10},
                    "telt_niet": {"type": "string", "minLength": 10},
                    "actie": {"type": "string", "minLength": 10}
                  }
                },
                "drp": {"type": "array", "minItems": 1, "items": {"enum": ["D", "R", "P"]}, "uniqueItems": true},
                "bewijs": {"type": "string", "minLength": 10}
              }
            }
          },
          "bronnen": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

- [ ] **Stap 2: Schrijf de falende tests** `tests/test_paden.py`:

```python
"""paden.json is de enige bron; deze tests bewaken vorm en inhoud."""
import json
import pathlib
import re

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PADEN = ROOT / "paden.json"
SCHEMA = ROOT / "tools" / "paden.schema.json"

VERBODEN = re.compile(r"alkmaar|leiden|leiderdorp|oegstgeest|zoeterwoude|@[a-z0-9.-]+\.nl|linkedin", re.I)


@pytest.fixture(scope="module")
def data():
    return json.loads(PADEN.read_text(encoding="utf-8"))


def test_valideert_tegen_schema(data):
    jsonschema.validate(data, json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_elk_blad_hoort_bij_precies_een_cluster_behalve_impact(data):
    in_cluster = {b for c in data["clusters"] for b in c["bladeren"]}
    for blad in data["bladeren"]:
        if blad["type"] == "impact":
            assert blad["id"] not in in_cluster, f"{blad['id']} is impact en hoort in geen cluster"
        else:
            assert blad["id"] in in_cluster, f"{blad['id']} hoort in geen enkel cluster"
    alle = [b for c in data["clusters"] for b in c["bladeren"]]
    assert len(alle) == len(set(alle)), "een blad staat in twee clusters"


def test_ids_zijn_uniek_en_chokepoint_ids_matchen_blad(data):
    ids = [b["id"] for b in data["bladeren"]]
    assert len(ids) == len(set(ids))
    for blad in data["bladeren"]:
        for cp in blad["chokepoints"]:
            assert cp["id"].startswith(blad["id"] + "-"), cp["id"]


def test_ap17_is_impact_en_ap15_ap16_zijn_pad(data):
    per_id = {b["id"]: b for b in data["bladeren"]}
    assert per_id["AP17"]["type"] == "impact"
    assert per_id["AP15"]["type"] == "pad" and per_id["AP16"]["type"] == "pad"


def test_geen_organisatienamen_of_adressen(data):
    tekst = json.dumps(data, ensure_ascii=False)
    assert not VERBODEN.search(tekst), VERBODEN.search(tekst).group(0)


def test_geen_em_dash(data):
    assert "\u2014" not in json.dumps(data, ensure_ascii=False)


def test_helpers():
    from tools import paden
    d = paden.laad()
    assert len(paden.bladeren()) == 18
    assert paden.cluster_van("AP01")["id"] == "C1"
    assert paden.cluster_van("AP17") is None
```

- [ ] **Stap 3: Run, verwacht FAIL**

```bash
pip install jsonschema pytest
python -m pytest tests/test_paden.py -v
```
Verwacht: FAIL, `paden.json` bestaat niet.

- [ ] **Stap 4: Schrijf `tools/__init__.py` (leeg) en `tools/paden.py`:**

```python
"""Toegang tot paden.json, de enige bron voor de aanvalspaden."""
from __future__ import annotations

import json
import pathlib

PAD = pathlib.Path(__file__).resolve().parent.parent / "paden.json"


def laad() -> dict:
    return json.loads(PAD.read_text(encoding="utf-8"))


def bladeren() -> list[dict]:
    return laad()["bladeren"]


def cluster_van(ap_id: str) -> dict | None:
    for cluster in laad()["clusters"]:
        if ap_id in cluster["bladeren"]:
            return cluster
    return None
```

- [ ] **Stap 5: Schrijf `paden.json`** volgens de structuur en regels hierboven: 5 clusters, 18 bladeren,
  per blad minimaal 2 chokepoints met volledige vragen. Haal de vragen uit `check/src` (als Taak 3 al is
  gedaan) of anders uit de gecompileerde HTML: open
  `<werkmap>/_wachtkamer\check-bron\...` of, als alleen de HTML er is, extraheer de
  strings met dit script en gebruik ze als bron:

```bash
python - <<'EOF'
import re, sys
t = open(r"<werkmap>/_wachtkamer/Gemeentelijke-weerbaarheidscheck-offline.html", encoding="utf-8").read()
s = max(re.findall(r"<script[^>]*>(.*?)</script>", t, re.S), key=len)
for x in re.findall(r'"((?:[^"\\\n]|\\.){25,700})"', s):
    if re.search(r"\b(de|het|een|van|je|niet|wordt)\b", x) and "function" not in x and "=>" not in x:
        print("-", x.replace("\\n", " "))
EOF
```

  Per vraag uit de zelfcheck: de vraagzin wordt `claim`, de regel eronder `toelichting`, de "telt niet"-zin
  (herkenbaar aan "is niet genoeg", "telt niet", "alleen ... is onvoldoende") wordt `telt_niet`, en de
  imperatiefzin ("Dwing ... af", "Blokkeer ...") wordt `actie`. Ontbreekt een van de vier, formuleer hem
  zelf in dezelfde stijl, maximaal twee zinnen.

- [ ] **Stap 6: Run, verwacht PASS**

```bash
python -m pytest tests/test_paden.py -v
```
Verwacht: 7 passed. Faalt het schema op een pattern: lees de melding, repareer `paden.json`, niet het schema.

- [ ] **Stap 7: Commit**

```bash
git add paden.json tools/__init__.py tools/paden.py tools/paden.schema.json tests/test_paden.py
git commit -m "paden: één bron met vijf clusters, achttien bladeren, chokepoints en vragen"
git push
```

---

## Taak 3: De zelfcheck inbrengen als `check/` en op `paden.json` zetten

**Bestanden:**
- Create: `aanvalspaden/check/` (de Vite-bron, integraal), `aanvalspaden/check/src/data/paden.json` (kopie),
  `aanvalspaden/check/src/lib/paden.ts`, `aanvalspaden/check/src/lib/paden.test.ts`,
  `aanvalspaden/tests/test_check_sync.py`
- Modify: de plek in `check/src` waar de vragen nu hardcoded staan (zoek op `AP01`).

**Interfaces:**
- Consumes: `paden.json` (Taak 2).
- Produces: TypeScript-types `Blad`, `Chokepoint`, `Vraag`, `Cluster` en functies
  `laadPaden(): Paden`, `bladeren(): Blad[]`, `clusterVan(apId: string): Cluster | null` in
  `check/src/lib/paden.ts`. Taak 5 bouwt hierop.

- [ ] **Stap 1: Bron kopiëren**

```bash
cd <werkmap>/aanvalspaden
cp -r ../_wachtkamer/check-bron/. check/
rm -rf check/node_modules check/dist
cd check && npm ci && npx vitest run || true && npm run build && test -s dist/index.html && echo "build ok"
```
Verwacht: build ok. Faalt `npm run build`: los alleen ontbrekende dependencies op (`npm install <pakket>`),
verander geen code, en noteer het in `BESLUITEN.md`.

- [ ] **Stap 2: Vind de hardcoded vragen**

```bash
grep -rn "AP01" check/src | head
```
Noteer het bestand (bijvoorbeeld `check/src/data/vragen.ts`). Dat bestand gaat weg; alle vragen komen uit
`paden.json`.

- [ ] **Stap 3: Schrijf de falende test** `check/src/lib/paden.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { bladeren, clusterVan, laadPaden } from "./paden";

describe("paden.json in de check", () => {
  it("heeft achttien bladeren en vijf clusters", () => {
    const p = laadPaden();
    expect(p.bladeren).toHaveLength(18);
    expect(p.clusters).toHaveLength(5);
  });

  it("kent per blad minstens twee chokepoints met vier vraagvelden", () => {
    for (const blad of bladeren()) {
      expect(blad.chokepoints.length).toBeGreaterThanOrEqual(2);
      for (const cp of blad.chokepoints) {
        expect(cp.vraag.claim.endsWith("?")).toBe(true);
        expect(cp.vraag.toelichting.length).toBeGreaterThan(10);
        expect(cp.vraag.telt_niet.length).toBeGreaterThan(10);
        expect(cp.vraag.actie.length).toBeGreaterThan(10);
      }
    }
  });

  it("zet AP01 in C1 en AP17 in geen cluster", () => {
    expect(clusterVan("AP01")?.id).toBe("C1");
    expect(clusterVan("AP17")).toBeNull();
  });
});
```

- [ ] **Stap 4: Run, verwacht FAIL** (`./paden` bestaat niet)

```bash
cd check && npx vitest run src/lib/paden.test.ts
```

- [ ] **Stap 5: Schrijf `check/src/lib/paden.ts`** en kopieer `paden.json`:

```bash
mkdir -p check/src/data && cp paden.json check/src/data/paden.json
```

```ts
// Eén bron voor de aanvalspaden. De kopie in src/data wordt door tests/test_check_sync.py
// gelijk gehouden met ../../paden.json in de repo-root; wijzig nooit deze kopie direct.
import data from "../data/paden.json";

export type Vraag = { claim: string; toelichting: string; telt_niet: string; actie: string };
export type Chokepoint = { id: string; titel: string; vraag: Vraag; drp: ("D" | "R" | "P")[]; bewijs: string };
export type Blad = {
  id: string;
  titel: string;
  type: "pad" | "impact";
  scenario: string;
  chokepoints: Chokepoint[];
  bronnen: string[];
};
export type Cluster = { id: string; titel: string; kern: string; bladeren: string[] };
export type Paden = { versie: string; toelichting: string; clusters: Cluster[]; bladeren: Blad[] };

export function laadPaden(): Paden {
  return data as Paden;
}

export function bladeren(): Blad[] {
  return laadPaden().bladeren;
}

export function clusterVan(apId: string): Cluster | null {
  return laadPaden().clusters.find((c) => c.bladeren.includes(apId)) ?? null;
}
```

Controleer dat `tsconfig.json` JSON-imports toestaat: `"resolveJsonModule": true` onder `compilerOptions`.
Ontbreekt dat: toevoegen.

- [ ] **Stap 6: Run, verwacht PASS**

```bash
npx vitest run src/lib/paden.test.ts
```

- [ ] **Stap 7: Vervang de hardcoded vragen door `paden.json`.** Open het bestand uit Stap 2. Voor elke
  plek waar de app een vraag, toelichting, actie of padtitel uit dat bestand leest, laat je hem lezen uit
  `bladeren()` en `chokepoints[].vraag`. Behoud de bestaande antwoordwaarden (ja / gedeeltelijk / nee /
  onbekend), de uitkomstlogica per pad en de drie-acties-logica; die veranderen niet. Verwijder daarna het
  oude vragenbestand. Draai de bestaande tests van de app; alles wat eerder groen was moet groen blijven:

```bash
npx vitest run && npm run build && test -s dist/index.html
```

  Als een bestaande test de oude vragenstructuur hardcodeert: pas de test aan zodat hij dezelfde
  waarde uit `paden.json` verwacht. Verwijder geen tests.

- [ ] **Stap 8: Sync-test in Python** `tests/test_check_sync.py`:

```python
"""De kopie van paden.json in check/src/data moet gelijk zijn aan de bron in de root."""
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_kopie_in_check_is_gelijk_aan_bron():
    assert _sha(ROOT / "paden.json") == _sha(ROOT / "check" / "src" / "data" / "paden.json"), (
        "check/src/data/paden.json loopt achter; draai: cp paden.json check/src/data/paden.json"
    )
```

```bash
cd .. && python -m pytest tests/ -v
```
Verwacht: alles groen.

- [ ] **Stap 9: Titel en naam in de app.** Zoek in `check/src` en `check/index.html` op "Gemeentelijke
  weerbaarheidscheck" en vervang door "Aanvalspaden: zelfcheck". Zoek op "gemeente" (kleine letter) in
  gebruikersteksten en vervang door "organisatie" waar het over de eigen organisatie gaat; laat het staan
  waar het over gemeenten als sector gaat. Build opnieuw.

- [ ] **Stap 10: Commit**

```bash
git add check paden.json tests/test_check_sync.py
git commit -m "check: zelfcheck ingebracht en op paden.json gezet; hardcoded vragen verwijderd"
git push
```
CI: beide jobs moeten nu groen zijn. Controleer: `gh run list -R security-commons-nl/aanvalspaden --limit 1`.

---

## Taak 4: Pages en de koppeling met de kennisbank

**Bestanden:**
- Create: `aanvalspaden/.github/workflows/pages.yml`, `aanvalspaden/methode/README.md`
- Modify: `<werkmap>/kennisbank\security\risicoanalyse-aanvalspaden\README.md`,
  `<werkmap>/kennisbank\security\risicoanalyse-aanvalspaden\aanvalspaden.md`

**Interfaces:**
- Consumes: `check/dist/index.html` (Taak 3).
- Produces: live URL `https://security-commons-nl.github.io/aanvalspaden/`.

- [ ] **Stap 1: Pages-workflow** `.github/workflows/pages.yml`:

```yaml
name: Build and deploy Pages

on:
  push:
    branches: [main]
    paths: ["check/**", "paden.json", ".github/workflows/pages.yml"]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: check
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: check/package-lock.json
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v5
        with:
          path: check/dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
```

Zet Pages aan op "GitHub Actions":

```bash
gh api -X POST repos/security-commons-nl/aanvalspaden/pages -f build_type=workflow 2>/dev/null || gh api -X PUT repos/security-commons-nl/aanvalspaden/pages -f build_type=workflow
```

- [ ] **Stap 2: `methode/README.md`** (de leeswijzer in de repo):

```markdown
# De methode: van open pad naar risicolijst

De zelfcheck (diepte 0) zegt welke aanvalspaden open staan. De methode (diepte 1) vertaalt dat met de lijn
naar risico's met een eigenaar. De volledige methode, met het papieren sjabloon en een ingevuld voorbeeld,
staat in de kennisbank:

**[Risicoanalyse langs aanvalspaden](https://security-commons-nl.github.io/kennisbank/security/risicoanalyse-aanvalspaden/)**

In het kort:

1. **Kroonjuwelen, maximaal tien.** Wat mag niet omvallen of lekken; eigenaar is de lijn.
2. **Aanvalspaden.** De vijf clusters uit `paden.json`; de achttien bladeren zijn het detail.
3. **Dekking met bewijs.** Per open pad en kroonjuweel: zien we het (D), kunnen we reageren (R), houden we het
   tegen (P). Groen alleen met een bewijslink.
4. **De rode cellen zijn de risicolijst.** Maatregel, eigenaar, termijn of bewuste acceptatie.

De zelfcheck neemt stap 2 en het grootste deel van stap 3 uit handen; in de app kun je na het resultaat
doorgaan met stap 1 en 4.
```

- [ ] **Stap 3: Kennisbank koppelen.** In `kennisbank/security/risicoanalyse-aanvalspaden/README.md`,
  direct na de regel `> **Lees de methode online:** ...`, voeg toe:

```markdown

> **Begin met de zelfcheck.** In een uur, alleen, weet je welke aanvalspaden open staan:
> [security-commons-nl.github.io/aanvalspaden](https://security-commons-nl.github.io/aanvalspaden/). Deze
> methode is de stap daarna, met de lijn erbij. Beide gebruiken dezelfde bron voor de aanvalspaden.
```

  In `aanvalspaden.md` van hetzelfde item: zet bovenaan (na de frontmatter en de titel) de zin:

```markdown
> De vijf paden hieronder zijn de clusters; de achttien onderliggende aanvalspaden met hun vragen staan in
> [`paden.json`](https://github.com/security-commons-nl/aanvalspaden/blob/main/paden.json), de gedeelde bron
> van zelfcheck, methode en meting. Bij verschil wint `paden.json`.
```

  Daarna: herschrijf per pad de bewijsvragen naar de vier velden (claim, toelichting, wat niet telt, actie),
  in dezelfde bewoording als `paden.json`. Draai de kennisbank-check en commit daar apart:

```bash
cd <werkmap>/kennisbank && python tools/build.py
git add security/risicoanalyse-aanvalspaden/README.md security/risicoanalyse-aanvalspaden/aanvalspaden.md security/index.html index.html
git commit -m "security: risicoanalyse gekoppeld aan de zelfcheck; bewijsvragen in het vier-velden-formaat"
git push
```

- [ ] **Stap 4: Commit in aanvalspaden en controleer live**

```bash
cd <werkmap>/aanvalspaden
git add .github/workflows/pages.yml methode/README.md
git commit -m "site: Pages-deploy van de zelfcheck; leeswijzer methode"
git push
```
Wacht op de run (`gh run watch -R security-commons-nl/aanvalspaden`), open dan
`https://security-commons-nl.github.io/aanvalspaden/` en controleer dat de zelfcheck laadt en dat de titel
"Aanvalspaden: zelfcheck" is. Een 404 direct na de eerste deploy is normaal; wacht twee minuten.

---

## Taak 5: Diepte 1 in de app, deel A: datamodel en logica (zonder UI)

**Bestanden:**
- Create: `check/src/lib/risico.ts`, `check/src/lib/risico.test.ts`

**Interfaces:**
- Consumes: `Blad`, `Chokepoint`, `clusterVan` uit `check/src/lib/paden.ts` (Taak 3); de uitkomst per pad
  uit de bestaande app. Zoek in `check/src` de functie die per blad de stand berekent (waarden als
  `sterk`, `beperkt`, `reactief`, `open`, `onbekend`; de exacte namen staan in de code, gebruik die).
- Produces: types `Kroonjuweel`, `Cel`, `Bewijs`, `Risico`; functies `openePaden(standen)`,
  `celStatus(cel)`, `risicolijst(kroonjuwelen, cellen)`.

- [ ] **Stap 1: Schrijf de falende tests** `check/src/lib/risico.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { celStatus, openePaden, risicolijst, type Cel, type Kroonjuweel } from "./risico";

const kj: Kroonjuweel[] = [
  { id: "K1", naam: "Uitkeringen betalen", eigenaar: "directeur Sociaal Domein", systemen: ["uitkeringsapplicatie"] },
  { id: "K2", naam: "Burgerzaken", eigenaar: "hoofd Publiekszaken", systemen: ["BRP-koppeling"] },
];

describe("openePaden", () => {
  it("geeft alleen bladeren van type pad met stand open of reactief", () => {
    const standen = { AP01: "open", AP02: "sterk", AP05: "reactief", AP17: "open" } as const;
    expect(openePaden(standen).map((b) => b.id)).toEqual(["AP01", "AP05"]);
  });
});

describe("celStatus", () => {
  const basis: Cel = { kroonjuweelId: "K1", bladId: "AP01", geraakt: true, bewijs: [] };
  it("is rood zonder bewijs, ook als de zelfcheck ja zei", () => {
    expect(celStatus(basis)).toBe("rood");
  });
  it("is groen alleen met bewijs op alle drp-letters van minstens één chokepoint", () => {
    const cel: Cel = { ...basis, bewijs: [{ chokepointId: "AP01-1", link: "bewijs/ca-export.json", letters: ["P"] }] };
    expect(celStatus(cel)).toBe("groen");
  });
  it("is grijs als het kroonjuweel niet geraakt wordt door dit pad", () => {
    expect(celStatus({ ...basis, geraakt: false })).toBe("grijs");
  });
});

describe("risicolijst", () => {
  it("maakt van elke rode cel één risico met maatregel uit de actie en eigenaar uit het kroonjuweel", () => {
    const cellen: Cel[] = [
      { kroonjuweelId: "K1", bladId: "AP01", geraakt: true, bewijs: [] },
      { kroonjuweelId: "K2", bladId: "AP01", geraakt: false, bewijs: [] },
    ];
    const lijst = risicolijst(kj, cellen);
    expect(lijst).toHaveLength(1);
    expect(lijst[0]).toMatchObject({ kroonjuweel: "Uitkeringen betalen", pad: "AP01", eigenaar: "directeur Sociaal Domein" });
    expect(lijst[0].maatregel.length).toBeGreaterThan(10);
    expect(lijst[0].status).toBe("open");
  });
});
```

- [ ] **Stap 2: Run, verwacht FAIL**

```bash
cd check && npx vitest run src/lib/risico.test.ts
```

- [ ] **Stap 3: Schrijf `check/src/lib/risico.ts`:**

```ts
// Diepte 1: van open paden naar een risicolijst. Pure functies, geen UI.
// Regel uit de spec: in de zelfcheck is "ja" een antwoord; hier is een cel pas groen met bewijs.
import { bladeren, type Blad } from "./paden";

export type Kroonjuweel = { id: string; naam: string; eigenaar: string; systemen: string[] };
export type Letter = "D" | "R" | "P";
export type Bewijs = { chokepointId: string; link: string; letters: Letter[] };
export type Cel = { kroonjuweelId: string; bladId: string; geraakt: boolean; bewijs: Bewijs[] };
export type CelStatus = "groen" | "rood" | "grijs";
export type Stand = "sterk" | "beperkt" | "reactief" | "open" | "onbekend";
export type Risico = {
  kroonjuweel: string;
  eigenaar: string;
  pad: string;
  padTitel: string;
  maatregel: string;
  status: "open" | "geaccepteerd";
  termijn: string;
};

export function openePaden(standen: Record<string, string>): Blad[] {
  return bladeren().filter(
    (b) => b.type === "pad" && (standen[b.id] === "open" || standen[b.id] === "reactief"),
  );
}

export function celStatus(cel: Cel): CelStatus {
  if (!cel.geraakt) return "grijs";
  const blad = bladeren().find((b) => b.id === cel.bladId);
  if (!blad) return "rood";
  // Groen: minstens één chokepoint waarvan alle drp-letters met een link zijn belegd.
  const gedekt = blad.chokepoints.some((cp) => {
    const bewijs = cel.bewijs.filter((b) => b.chokepointId === cp.id && b.link.trim().length > 0);
    const letters = new Set(bewijs.flatMap((b) => b.letters));
    return cp.drp.every((l) => letters.has(l));
  });
  return gedekt ? "groen" : "rood";
}

export function risicolijst(kroonjuwelen: Kroonjuweel[], cellen: Cel[]): Risico[] {
  const perId = new Map(kroonjuwelen.map((k) => [k.id, k]));
  return cellen
    .filter((c) => celStatus(c) === "rood")
    .map((c) => {
      const k = perId.get(c.kroonjuweelId);
      const blad = bladeren().find((b) => b.id === c.bladId);
      const eersteActie = blad?.chokepoints[0]?.vraag.actie ?? "";
      return {
        kroonjuweel: k?.naam ?? c.kroonjuweelId,
        eigenaar: k?.eigenaar ?? "",
        pad: c.bladId,
        padTitel: blad?.titel ?? c.bladId,
        maatregel: eersteActie,
        status: "open",
        termijn: "",
      };
    });
}
```

- [ ] **Stap 4: Run, verwacht PASS**

```bash
npx vitest run src/lib/risico.test.ts
```

- [ ] **Stap 5: Commit**

```bash
git add src/lib/risico.ts src/lib/risico.test.ts
git commit -m "check: datamodel en logica voor diepte 1 (kroonjuwelen, cellen, bewijs, risicolijst)"
git push
```

---

## Taak 6: Diepte 1 in de app, deel B: opslag en export

**Bestanden:**
- Create: `check/src/lib/opslag.ts`, `check/src/lib/opslag.test.ts`, `check/src/lib/export.ts`,
  `check/src/lib/export.test.ts`

**Interfaces:**
- Consumes: `Kroonjuweel`, `Cel`, `Risico`, `risicolijst` (Taak 5). De bestaande app slaat antwoorden op in
  `localStorage`; zoek de sleutel (`grep -rn "localStorage" src`) en gebruik hetzelfde patroon.
- Produces: `bewaarAnalyse(a: Analyse)`, `laadAnalyse(): Analyse | null`, `wisAnalyse()`,
  `exportJson(a: Analyse): string`, `exportHtml(a: Analyse): string`.

- [ ] **Stap 1: Falende tests** `check/src/lib/opslag.test.ts`:

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { bewaarAnalyse, laadAnalyse, wisAnalyse, type Analyse } from "./opslag";

const voorbeeld: Analyse = {
  versie: 1,
  kroonjuwelen: [{ id: "K1", naam: "Uitkeringen betalen", eigenaar: "directeur", systemen: [] }],
  cellen: [{ kroonjuweelId: "K1", bladId: "AP01", geraakt: true, bewijs: [] }],
  acceptaties: {},
};

describe("opslag van de analyse", () => {
  beforeEach(() => localStorage.clear());
  it("geeft null als er niets is", () => expect(laadAnalyse()).toBeNull());
  it("bewaart en laadt een analyse ongewijzigd", () => {
    bewaarAnalyse(voorbeeld);
    expect(laadAnalyse()).toEqual(voorbeeld);
  });
  it("wist alleen de analyse, niet de antwoorden van de zelfcheck", () => {
    localStorage.setItem("iets-anders", "x");
    bewaarAnalyse(voorbeeld);
    wisAnalyse();
    expect(laadAnalyse()).toBeNull();
    expect(localStorage.getItem("iets-anders")).toBe("x");
  });
});
```

`check/src/lib/export.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { exportHtml, exportJson } from "./export";
import type { Analyse } from "./opslag";

const a: Analyse = {
  versie: 1,
  kroonjuwelen: [{ id: "K1", naam: "Uitkeringen betalen", eigenaar: "directeur", systemen: ["uitkeringsapplicatie"] }],
  cellen: [{ kroonjuweelId: "K1", bladId: "AP01", geraakt: true, bewijs: [] }],
  acceptaties: {},
};

describe("export", () => {
  it("json bevat de risicolijst en de invoer", () => {
    const j = JSON.parse(exportJson(a));
    expect(j.risicolijst).toHaveLength(1);
    expect(j.kroonjuwelen).toHaveLength(1);
  });
  it("html is self-contained en bevat de risicolijst als tabel", () => {
    const h = exportHtml(a);
    expect(h.startsWith("<!doctype html>")).toBe(true);
    expect(h).not.toMatch(/<link[^>]+href="https?:/);
    expect(h).not.toMatch(/<script[^>]+src="https?:/);
    expect(h).toContain("<table");
    expect(h).toContain("Uitkeringen betalen");
    expect(h).toContain("AP01");
  });
});
```

- [ ] **Stap 2: Run, verwacht FAIL**

```bash
npx vitest run src/lib/opslag.test.ts src/lib/export.test.ts
```
Als `localStorage` niet bestaat in de testomgeving: zet in `vitest.config.ts` (of `vite.config.ts` onder
`test`) `environment: "jsdom"` en `npm install -D jsdom`.

- [ ] **Stap 3: Schrijf `check/src/lib/opslag.ts`:**

```ts
// Opslag van diepte 1, gescheiden van de antwoorden van de zelfcheck (eigen sleutel).
import type { Cel, Kroonjuweel } from "./risico";

export type Analyse = {
  versie: 1;
  kroonjuwelen: Kroonjuweel[];
  cellen: Cel[];
  acceptaties: Record<string, { reden: string; door: string; datum: string }>; // sleutel: `${kroonjuweelId}|${bladId}`
};

const SLEUTEL = "aanvalspaden.analyse.v1";

export function bewaarAnalyse(a: Analyse): void {
  try {
    localStorage.setItem(SLEUTEL, JSON.stringify(a));
  } catch {
    // Opslag kan geblokkeerd zijn (privévenster); de analyse blijft dan alleen in het geheugen.
  }
}

export function laadAnalyse(): Analyse | null {
  try {
    const raw = localStorage.getItem(SLEUTEL);
    return raw ? (JSON.parse(raw) as Analyse) : null;
  } catch {
    return null;
  }
}

export function wisAnalyse(): void {
  try {
    localStorage.removeItem(SLEUTEL);
  } catch {
    // niets te wissen
  }
}
```

`check/src/lib/export.ts`:

```ts
// Export van diepte 1: JSON (voor hergebruik) en self-contained HTML (voor de lijn, plakbaar in Word).
import type { Analyse } from "./opslag";
import { risicolijst, type Risico } from "./risico";

function e(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function exportJson(a: Analyse): string {
  const lijst: Risico[] = risicolijst(a.kroonjuwelen, a.cellen).map((r) => {
    const acc = a.acceptaties[`${a.kroonjuwelen.find((k) => k.naam === r.kroonjuweel)?.id}|${r.pad}`];
    return acc ? { ...r, status: "geaccepteerd" as const } : r;
  });
  return JSON.stringify({ versie: a.versie, kroonjuwelen: a.kroonjuwelen, cellen: a.cellen, acceptaties: a.acceptaties, risicolijst: lijst }, null, 2);
}

export function exportHtml(a: Analyse): string {
  const lijst = risicolijst(a.kroonjuwelen, a.cellen);
  const rijen = lijst
    .map(
      (r) =>
        `<tr><td>${e(r.kroonjuweel)}</td><td>${e(r.pad)}: ${e(r.padTitel)}</td><td>${e(r.maatregel)}</td><td>${e(r.eigenaar)}</td><td>${e(r.status)}</td><td>${e(r.termijn)}</td></tr>`,
    )
    .join("\n");
  const css =
    "body{font-family:Calibri,Arial,sans-serif;font-size:11pt;max-width:19cm;margin:2cm auto}table{border-collapse:collapse;width:100%;font-size:10pt}th,td{border:1px solid #c9d1dc;padding:.35em .5em;vertical-align:top;text-align:left}th{background:#f3f6fa}@media print{@page{size:A4 landscape;margin:1.5cm}}";
  return `<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>Risicolijst langs aanvalspaden</title><style>${css}</style></head>
<body><h1>Risicolijst langs aanvalspaden</h1>
<p>Uit de zelfcheck en de risicoanalyse; gebaseerd op eigen antwoorden en aangeleverd bewijs, niet onafhankelijk geverifieerd. Bevat gevoelige beveiligingsinformatie.</p>
<table><thead><tr><th>Kroonjuweel</th><th>Aanvalspad</th><th>Maatregel</th><th>Eigenaar</th><th>Status</th><th>Termijn</th></tr></thead>
<tbody>
${rijen}
</tbody></table></body></html>`;
}
```

- [ ] **Stap 4: Run, verwacht PASS; commit**

```bash
npx vitest run src/lib/opslag.test.ts src/lib/export.test.ts
git add src/lib/opslag.ts src/lib/opslag.test.ts src/lib/export.ts src/lib/export.test.ts package.json package-lock.json
git commit -m "check: opslag en export (JSON, self-contained HTML) voor diepte 1"
git push
```

---

## Taak 7: Diepte 1 in de app, deel C: de schermen

**Bestanden:**
- Create: `check/src/ui/Verdieping.tsx`, `check/src/ui/Kroonjuwelen.tsx`, `check/src/ui/Matrix.tsx`,
  `check/src/ui/Risicolijst.tsx`, `check/src/ui/Verdieping.test.tsx`
- Modify: het resultaatscherm van de zelfcheck (zoek op de tekst "Als je morgen maar drie dingen kunt doen").

**Interfaces:**
- Consumes: alles uit Taak 5 en 6; de `standen` per blad uit de bestaande resultaatlogica.
- Produces: één knop op het resultaatscherm, "Maak er een risicoanalyse van", die `Verdieping` opent.

Gebruik de componentstijl van de bestaande app (zelfde CSS-klassen, zelfde knoppen). Geen nieuwe UI-library.

- [ ] **Stap 1: Falende test** `check/src/ui/Verdieping.test.tsx` (React Testing Library; installeer
  `@testing-library/react` en `@testing-library/user-event` als ze ontbreken):

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { Verdieping } from "./Verdieping";

const standen = { AP01: "open", AP02: "sterk", AP05: "reactief" };

describe("Verdieping (diepte 1)", () => {
  beforeEach(() => localStorage.clear());

  it("start met het kroonjuwelenscherm en weigert een elfde kroonjuweel", async () => {
    render(<Verdieping standen={standen} />);
    expect(screen.getByRole("heading", { name: /kroonjuwelen/i })).toBeTruthy();
    const naam = screen.getByLabelText(/naam/i);
    for (let i = 1; i <= 10; i++) {
      await userEvent.clear(naam);
      await userEvent.type(naam, `Proces ${i}`);
      await userEvent.type(screen.getByLabelText(/eigenaar/i), "directeur");
      await userEvent.click(screen.getByRole("button", { name: /toevoegen/i }));
    }
    expect(screen.getByRole("button", { name: /toevoegen/i })).toHaveProperty("disabled", true);
    expect(screen.getByText(/tien is de grens/i)).toBeTruthy();
  });

  it("toont in de matrix alleen de open en reactieve paden", async () => {
    render(<Verdieping standen={standen} />);
    await userEvent.type(screen.getByLabelText(/naam/i), "Uitkeringen betalen");
    await userEvent.type(screen.getByLabelText(/eigenaar/i), "directeur");
    await userEvent.click(screen.getByRole("button", { name: /toevoegen/i }));
    await userEvent.click(screen.getByRole("button", { name: /naar de matrix/i }));
    expect(screen.getByText("AP01")).toBeTruthy();
    expect(screen.getByText("AP05")).toBeTruthy();
    expect(screen.queryByText("AP02")).toBeNull();
  });

  it("zet een cel op rood zodra hij geraakt is en op groen pas met bewijs", async () => {
    render(<Verdieping standen={standen} />);
    await userEvent.type(screen.getByLabelText(/naam/i), "Uitkeringen betalen");
    await userEvent.type(screen.getByLabelText(/eigenaar/i), "directeur");
    await userEvent.click(screen.getByRole("button", { name: /toevoegen/i }));
    await userEvent.click(screen.getByRole("button", { name: /naar de matrix/i }));
    const cel = screen.getByTestId("cel-K1-AP01");
    await userEvent.click(cel);
    expect(cel.getAttribute("data-status")).toBe("rood");
    await userEvent.click(screen.getByRole("button", { name: /bewijs/i }));
    await userEvent.type(screen.getByLabelText(/link of verwijzing/i), "bewijs/ca-export.json");
    await userEvent.click(screen.getByRole("checkbox", { name: /^P$/ }));
    await userEvent.click(screen.getByRole("button", { name: /opslaan/i }));
    expect(screen.getByTestId("cel-K1-AP01").getAttribute("data-status")).toBe("groen");
  });

  it("de risicolijst toont elke rode cel met eigenaar en maatregel", async () => {
    render(<Verdieping standen={standen} />);
    await userEvent.type(screen.getByLabelText(/naam/i), "Uitkeringen betalen");
    await userEvent.type(screen.getByLabelText(/eigenaar/i), "directeur");
    await userEvent.click(screen.getByRole("button", { name: /toevoegen/i }));
    await userEvent.click(screen.getByRole("button", { name: /naar de matrix/i }));
    await userEvent.click(screen.getByTestId("cel-K1-AP01"));
    await userEvent.click(screen.getByRole("button", { name: /naar de risicolijst/i }));
    const rij = screen.getByRole("row", { name: /uitkeringen betalen/i });
    expect(rij.textContent).toContain("directeur");
    expect(rij.textContent).toContain("AP01");
  });
});
```

- [ ] **Stap 2: Run, verwacht FAIL**

```bash
npx vitest run src/ui/Verdieping.test.tsx
```

- [ ] **Stap 3: Bouw de vier componenten.** Vereisten die de tests afdwingen (bouw precies dit, niets meer):

  - `Verdieping({ standen })`: houdt `Analyse` in state (start met `laadAnalyse() ?? leeg`), bewaart bij elke
    wijziging via `bewaarAnalyse`. Drie stappen met knoppen "Naar de matrix", "Naar de risicolijst", en terug.
  - `Kroonjuwelen`: kop `<h2>Kroonjuwelen</h2>`, formulier met labels "Naam", "Eigenaar", "Systemen
    (kommagescheiden)", knop "Toevoegen" (disabled bij 10, met de tekst "Tien is de grens: wie de top tien
    niet haalt, telt in deze ronde niet mee."), lijst met verwijderknop per kroonjuweel. Id's `K1`, `K2`, ...
    oplopend.
  - `Matrix`: kolommen = `openePaden(standen)`, rijen = kroonjuwelen. Elke cel een `<button>` met
    `data-testid="cel-{K}-{AP}"` en `data-status` uit `celStatus`. Klik = `geraakt` omschakelen. Bij een rode
    cel een knop "Bewijs" die een paneel opent met per chokepoint van dat blad: de `claim`, een veld "Link of
    verwijzing", checkboxes `D`, `R`, `P` (alleen die in `cp.drp`), en "Opslaan". Toon de `bewijs`-zin uit
    `paden.json` als hint bij het veld.
  - `Risicolijst`: `<table>` met per rij (`role="row"`) kroonjuweel, pad, maatregel (bewerkbaar tekstveld,
    voorvulling uit `risicolijst()`), eigenaar, status (radio: open / geaccepteerd; bij geaccepteerd een veld
    "reden" en "door"), termijn (datumveld). Knoppen "Download JSON" en "Download HTML" die `exportJson` /
    `exportHtml` als bestand aanbieden (`Blob` + `URL.createObjectURL`, bestandsnaam
    `risicolijst-aanvalspaden.json` / `.html`).
  - Op het resultaatscherm van de zelfcheck: onder de drie acties één knop "Maak er een risicoanalyse van",
    met de zin "Een dag, met de lijn erbij: welke kroonjuwelen liggen achter de open paden, en wie is
    eigenaar." Klik opent `Verdieping`. **Niet** automatisch doorsturen (spec, punt 1).

- [ ] **Stap 4: Run alles, verwacht PASS; build**

```bash
npx vitest run && npm run build && test -s dist/index.html
```

- [ ] **Stap 5: Handmatige controle in de browser.** Open `check/dist/index.html` lokaal (dubbelklik).
  Doorloop: zelfcheck invullen tot resultaat, knop, drie kroonjuwelen, twee cellen rood, één bewijs, lijst,
  beide downloads. Alles zonder internet. Noteer afwijkingen als issues, niet als "later".

- [ ] **Stap 6: Commit**

```bash
git add src/ui package.json package-lock.json
git add src/  # alleen als het resultaatscherm buiten src/ui is aangepast; anders het exacte bestand
git commit -m "check: diepte 1 in de app (kroonjuwelen, matrix met bewijs, risicolijst, export)"
git push
```

---

## Taak 8: Posture-tool laat bevindingen landen op `paden.json`

**Bestanden (repo `security-posture-tool`):**
- Create: `v0.1/paden.json` (kopie), `v0.1/paden_map.py`, `v0.1/tests/test_paden_map.py`
- Modify: het findings-model in `v0.1/evidence.py` of waar `Finding`/`finding` wordt gedefinieerd
  (`grep -rn "class Finding\|def finding" v0.1/*.py`), en `v0.1/README.md`.

**Interfaces:**
- Consumes: `paden.json` uit `aanvalspaden` (kopie, met sync-test zoals in Taak 3 stap 8, maar dan met een
  vastgelegde hash in `v0.1/paden.sha256` omdat het een andere repo is).
- Produces: elke bevinding krijgt twee optionele velden `pad` (bijv. `"AP01"`) en `chokepoint` (bijv.
  `"AP01-1"`); functie `koppel(finding_id: str) -> tuple[str, str] | None` in `paden_map.py` op basis van een
  tabel `KOPPELING: dict[str, tuple[str, str]]` in datzelfde bestand.

- [ ] **Stap 1: Kopie en hash**

```bash
cd <werkmap>/security-posture-tool
cp ../aanvalspaden/paden.json v0.1/paden.json
sha256sum v0.1/paden.json | awk '{print $1}' > v0.1/paden.sha256
```

- [ ] **Stap 2: Falende tests** `v0.1/tests/test_paden_map.py`:

```python
"""Bevindingen van de meting landen op dezelfde paden en chokepoints als zelfcheck en methode."""
import hashlib
import json
import pathlib

import paden_map

V01 = pathlib.Path(__file__).resolve().parent.parent


def test_kopie_paden_json_matcht_hash():
    h = hashlib.sha256((V01 / "paden.json").read_bytes()).hexdigest()
    assert h == (V01 / "paden.sha256").read_text().strip(), "paden.json loopt achter op aanvalspaden/paden.json"


def test_elke_koppeling_wijst_naar_bestaand_chokepoint():
    data = json.loads((V01 / "paden.json").read_text(encoding="utf-8"))
    cps = {cp["id"] for b in data["bladeren"] for cp in b["chokepoints"]}
    bladeren = {b["id"] for b in data["bladeren"]}
    for finding_id, (pad, cp) in paden_map.KOPPELING.items():
        assert pad in bladeren, f"{finding_id}: onbekend pad {pad}"
        assert cp in cps and cp.startswith(pad + "-"), f"{finding_id}: onbekend chokepoint {cp}"


def test_koppel_geeft_none_voor_onbekende_bevinding():
    assert paden_map.koppel("bestaat-niet") is None


def test_minstens_de_mfa_en_laps_bevindingen_zijn_gekoppeld():
    assert paden_map.koppel("mfa_ontbreekt") is not None
    assert paden_map.koppel("laps_ontbreekt") is not None
```

  De namen `mfa_ontbreekt` en `laps_ontbreekt` zijn voorbeelden; vervang ze door de echte finding-id's uit
  de code (`grep -rn "finding_id\|FINDING" v0.1/*.py v0.1/connectors/*.py | head -30`) en gebruik er
  minstens twee die over MFA en over lokale admin-wachtwoorden gaan.

- [ ] **Stap 3: Run, verwacht FAIL; schrijf `v0.1/paden_map.py`:**

```python
"""Koppeling van bevindingen (finding-id) naar aanvalspad en chokepoint uit paden.json.

Dit is de brug tussen de meting (diepte 2) en de zelfcheck en methode (diepte 0 en 1): een bevinding hier
is het bewijs voor een cel daar. Onbekende bevindingen blijven ongekoppeld; dat is geen fout, wel een
uitnodiging om de tabel aan te vullen.
"""
from __future__ import annotations

KOPPELING: dict[str, tuple[str, str]] = {
    # finding-id: (pad, chokepoint). Vul aan per connector; houd de id's exact gelijk aan de code.
    "mfa_ontbreekt": ("AP01", "AP01-1"),
    "laps_ontbreekt": ("AP05", "AP05-1"),
}


def koppel(finding_id: str) -> tuple[str, str] | None:
    return KOPPELING.get(finding_id)
```

  Vul `KOPPELING` aan voor elke finding-id die de code kent en die logisch bij een chokepoint hoort; laat
  weg wat nergens past. Voeg in het findings-model de velden `pad: str | None = None` en
  `chokepoint: str | None = None` toe en vul ze bij het aanmaken van een finding via `koppel()`.

- [ ] **Stap 4: Run alle tests, verwacht PASS**

```bash
cd v0.1 && python -m pytest tests/ -v
```
Verwacht: de bestaande 127 plus de 4 nieuwe groen.

- [ ] **Stap 5: README-alinea** in `v0.1/README.md`, onder de eerste kop:

```markdown
## Relatie met de aanvalspaden-keten

Deze meting is diepte 2 van [aanvalspaden](https://github.com/security-commons-nl/aanvalspaden): dezelfde
achttien paden en chokepoints als de zelfcheck en de methode. Elke bevinding krijgt een `pad` en een
`chokepoint` (zie `paden_map.py`), zodat een bevinding hier het bewijs is voor een cel daar. `paden.json` is
een kopie van de bron in de aanvalspaden-repo; `paden.sha256` bewaakt dat hij niet achterloopt.
```

- [ ] **Stap 6: Commit**

```bash
git add v0.1/paden.json v0.1/paden.sha256 v0.1/paden_map.py v0.1/tests/test_paden_map.py v0.1/README.md
git add v0.1/evidence.py   # of het bestand waar het findings-model staat
git commit -m "meting: bevindingen landen op de aanvalspaden en chokepoints uit paden.json"
git push
```

---

## Taak 9: Org-profiel, statuut en verwijzingen

**Bestanden:**
- Modify: `<werkmap>/.github\profile\README.md` (projectentabel),
  `<werkmap>/.github\REDACTIESTATUUT.md` (tabel bij B1),
  `<werkmap>/CLAUDE.md` (projecten + routing),
  `<werkmap>/security-commons-nl.github.io\llms.txt` (via de build).

- [ ] **Stap 1: Profiel.** Voeg in de projectentabel, direct onder de rij van `security-posture-tool`, deze rij
  toe (één regel):

```markdown
| [aanvalspaden](https://github.com/security-commons-nl/aanvalspaden) | prototype | Eén instrument in drie diepten: zelfcheck (een uur, welke aanvalspaden staan open), risicoanalyse (met de lijn, kroonjuwelen en bewijs, risicolijst met eigenaar) en meting; één bron voor de aanvalspaden van de publieke sector | [Live tool](https://security-commons-nl.github.io/aanvalspaden/) | CISO's en ISO's bij publieke organisaties |
```

  Pas de rij van `security-posture-tool` aan: voeg aan "Wat is het?" toe: ", diepte 2 (meting) van de
  aanvalspaden-keten".

- [ ] **Stap 2: Statuut B1-tabel.** Voeg een regel toe: `| aanvalspaden | \`check/\`, \`methode/\`, \`meting/\`
  (volgt); \`paden.json\` op de root is de bron |`.

- [ ] **Stap 3: Commons-CLAUDE.md.** Onder `## Projecten` een blok:

```markdown
### aanvalspaden (prototype)
De keten zelfcheck → risicoanalyse → meting. `paden.json` op de root is de enige bron voor de achttien
aanvalspaden; `check/` is de offline app (React + Vite), `methode/` verwijst naar de kennisbank,
`meting/` volgt (security-posture-tool). Bouwplan: `2026-08-28-bouwplan-aanvalspaden-keten.md`.
```

  En in de routing-sneltabel de rij `| dreigingsbeeld, aanvalspad, CTI-rapport | ... |` vervangen door:
  `| aanvalspad, chokepoint, zelfcheck, risicolijst, kroonjuwelen | \`aanvalspaden\` (bron: \`paden.json\`); leesbare methode in \`kennisbank/security/risicoanalyse-aanvalspaden\` |`.

- [ ] **Stap 4: Commits en site**

```bash
cd <werkmap>/.github && git add profile/README.md REDACTIESTATUUT.md && git commit -m "profiel: aanvalspaden-keten toegevoegd; posture-tool als diepte 2" && git push
cd ../security-commons-nl.github.io && cp ../.github/profile/README.md org-profile/profile/README.md && node site/build.mjs && git add llms.txt sitemap.xml && git commit -m "site: aanvalspaden in llms.txt en sitemap" && git push
```

  `CLAUDE.md` is geen repo; opslaan is genoeg.

---

## Taak 10 (pas na Taak 8, apart besluit): posture-tool verhuizen als `meting/`

Niet uitvoeren zonder een regel in `BESLUITEN.md` van de aanvalspaden-repo met datum en "ja" van de
eigenaren. Als dat er is:

- [ ] **Stap 1: Subtree met historie**

```bash
cd <werkmap>/aanvalspaden
git subtree add --prefix=meting https://github.com/security-commons-nl/security-posture-tool.git main
```

- [ ] **Stap 2: Kopie-`paden.json` in `meting/v0.1/` verwijderen** en `paden_map.py` laten lezen uit
  `../../paden.json` (pad relatief aan `meting/v0.1/`); de hash-test uit Taak 8 vervalt en wordt vervangen
  door de sync-test-vorm uit Taak 3 stap 8.
- [ ] **Stap 3: CI-job `meting`** toevoegen in `.github/workflows/ci.yml` met `working-directory: meting/v0.1`
  en `test-command: "python -m pytest tests/ -v"`.
- [ ] **Stap 4:** README van `security-posture-tool` vervangen door een doorverwijzing, repo archiveren
  (`gh api -X PATCH repos/security-commons-nl/security-posture-tool -F archived=true`), profielrij verwijderen
  en onder "Gearchiveerd" zetten, `llms.txt` opnieuw bouwen.
- [ ] **Stap 5:** Commit per stap, één onderwerp per commit, expliciete paden.

---

## Definitie van klaar (per taak en voor het geheel)

- Elke taak eindigt met groene tests (Python én vitest waar van toepassing) en een commit met expliciete paden.
- Na Taak 4: de zelfcheck draait live op `security-commons-nl.github.io/aanvalspaden/` met vragen uit
  `paden.json`, en de kennisbank verwijst ernaar.
- Na Taak 7: een gebruiker kan offline van resultaat naar risicolijst met export, zonder internet.
- Na Taak 8: een bevinding van de posture-tool heeft een `pad` en `chokepoint` die in `paden.json` bestaan.
- Na Taak 9: het org-profiel toont de keten als één project met label prototype, en `llms.txt` volgt.
- Overal: geen persoonsnamen, geen organisatienamen als herkomst, geen em-dashes; `python -m pytest` en
  `npx vitest run` groen; geen `git add -A`.

## Zelfcontrole op dit plan

- Spec-dekking: punt 1 (Taak 5, 6, 7 en de knop, niet automatisch), 2 (Taak 2), 3 (Taak 2 stap 5, Taak 4
  stap 3), 4 (Taak 5 `celStatus`), 5 (Taak 0 stap 2, Taak 3 stap 9), 6 (Taak 0 stap 3, Taak 1 README), 7
  (Taak 8, Taak 10), 8 (Taak 4). Geen gaten.
- Naamconsistentie: `laadPaden`, `bladeren`, `clusterVan` (TS) en `laad`, `bladeren`, `cluster_van` (Python)
  worden overal zo gebruikt; `celStatus`, `openePaden`, `risicolijst`, `bewaarAnalyse`, `laadAnalyse`,
  `wisAnalyse`, `exportJson`, `exportHtml` idem; `KOPPELING` en `koppel` in Taak 8.
- Onbekenden zijn expliciet gemaakt als poorten (Taak 0) of als zoekinstructie met `grep` (Taak 3 stap 2,
  Taak 5 interfaces, Taak 8 stap 2); nergens "later".
