# mappingen/ - van aanvalspad naar norm

De vierde schakel van de keten. De zelfcheck vraagt naar barrieres tegen aanvalspaden, niet naar normen.
Hier staat het verband: welk bewijs uit een barriere zegt iets over welke maatregel, en over welke
maatregelen het niets zegt.

**Live:** https://security-commons-nl.github.io/aanvalspaden/normen/

## De belofte, en waarom die zo krap is

Er is precies een relatie, en die heeft een richting:

> **een barriere levert bewijs voor een maatregel**

Nooit "dekt af", nooit "voldoet aan". Dat onderscheid is de reden dat dit ding mag bestaan. Wie de
zelfcheck heeft gedaan, heeft antwoorden. Wie het gevraagde bewijs erbij legt, heeft materiaal voor een
gesprek met een auditor of een risicohouder. Het oordeel of je aan een norm voldoet, blijft van de
auditor. Een test (`test_geen_taal_die_compliance_belooft`) bewaakt dat er geen zin insluipt die iets
anders suggereert.

Elke regel draagt een **sterkte**:

| Sterkte | Wat het zegt |
|---|---|
| `volledig` | Wie dit bewijs op tafel legt, heeft het toetsbare deel van de maatregel aangetoond |
| `gedeeltelijk` | Het bewijs toont een deel aan; de maatregel vraagt meer |
| `raakvlak` | Het raakt elkaar, maar dit bewijs toont de maatregel niet aan |

Een raakvlak telt **niet** als dekking. Een maatregel waar alleen raakvlakken op staan, blijft een witte
vlek, met de raakvlakken erbij zodat een lezer ziet waarom het in de buurt komt en toch niet telt. Zou
een raakvlak wel meetellen, dan gaf de pagina precies de valse zekerheid die dit instrument wil vermijden.

## De korrel: de barriere, niet het chokepoint

De achttien paden hebben samen 76 chokepoints, maar die delen **44 unieke barrieres** (het `vraag_id` in
`paden.json`). "Dwing phishingbestendige authenticatie af" staat bij AP01, AP02, AP08 en AP17 met dezelfde
claim en hetzelfde bewijs. De mapping hangt daarom aan de barriere; een chokepoint erft hem. Anders zou je
dezelfde vraag bij vier paden verschillend kunnen verankeren zonder dat iemand het merkt. Een test bewaakt
dat chokepoints met hetzelfde `vraag_id` ook echt dezelfde claim en hetzelfde bewijs houden.

## Stilte is nooit een vergissing

Elke barriere staat of in `regels`, of in `ongekoppeld` met de reden waarom dit kader er niets over zegt.
Een test blokkeert als een barriere in geen van beide staat. Zo is het verschil zichtbaar tussen "hier is
over nagedacht en het past niet" en "hier is niemand aan toegekomen".

## De kaders

| Bestand | Kader | Herkomst |
|---|---|---|
| `bio2.json` | BIO 2.0, en daarmee ISO 27001:2022 | `bronnen/bio2.json`, gegenereerd uit de gedeelde dataset in `cisochat` |
| `wpg.json` | Wpg-toetsingskader voor boa-organisaties | `bronnen/wpg.json`, uit de NOREA-handreiking versie 2024 1.0 |

**BIO 2.0 en ISO 27001 zijn een mapping, geen twee.** BIO 2.0 volgt de nummering van ISO 27002:2022
(bijlage A van ISO 27001). Maatregel `8.5` hier is dus zowel de BIO2-maatregel als de ISO-maatregel; de
overheidsmaatregelen die eronder vallen (`8.05.01` en verder) staan erbij. Dat scheelt een heel
mappingbestand.

**Waarom ook de Wpg.** Om te laten zien dat een dreigingsgerichte zelfcheck maar een deel van een
normenkader raakt, en dat dat klopt. Het Wpg-kader gaat over rechtmatige verwerking: doelbinding,
bewaartermijnen, verstrekking, rechten van betrokkenen. Geen aanvalspad zegt daar iets over. Wat de
zelfcheck wel raakt is beveiliging: maatregel 6 (art. 4a Wpg) en de technische maatregelen uit bijlage 4
van de handreiking, die volgens die bijlage naast de BIO gelden.

## Auteursrecht

De bronbestanden dragen **nummers, titels en eigen samenvattingen**, geen normteksten. De tekst van
ISO 27002-maatregelen is auteursrechtelijk beschermd; die hebben we hier niet nodig en staat er dus niet
in. Een test controleert dat er geen veld met normtekst insluipt. Voor de Wpg geldt dat de NOREA-handreiking
mag worden gebruikt met bronvermelding; ook daar staan eigen samenvattingen.

## Bouwen

```bash
python mappingen/bouw.py            # schrijft mappingen/dist/index.html
python mappingen/bouw.py site/normen  # of naar een andere map
```

Zelfde patroon als `check/`: een zelfstandig HTML-bestand, alle data meegebakken, geen enkele externe
verwijzing, en een Content-Security-Policy van `default-src 'none'` met een sha256 op het script en de
stylesheet. Wat de pagina toont is vooraf uitgerekend in Python; de browser tekent alleen.

De BIO2-bron opnieuw genereren (alleen nodig als de dataset in `cisochat` wijzigt):

```bash
python mappingen/bronnen/genereer_bio2.py
```

## Testen

```bash
python -m pytest tests/test_mappingen.py -v   # de mapping: vorm, volledigheid, taal
python -m pytest mappingen/tests/ -v          # de pagina: bouw en browser
```

## Wat dit niet is

Geen auditinstrument en geen vervanging van een normenkader. Het zegt waar bewijs uit een
dreigingsgerichte check iets aantoont, en waar niet. De witte vlekken zijn geen gebrek van de zelfcheck
maar de grens ervan, en dat is precies wat de pagina wil laten zien.

## Bijdragen

De mapping is een uitspraak over andermans normenkader, dus hij is per definitie voor discussie vatbaar.
Elke regel draagt een reden in een zin, juist zodat je hem kunt tegenspreken zonder JSON te lezen. Vind je
een regel te ruim, te krap of gewoon fout: open een issue met de barriere, de maatregel en waarom, of een
pull request op het mappingbestand. Een issue is een volwaardige bijdrage.
