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
| `nist-csf.json` | NIST CSF 2.0 | `bronnen/nist-csf.json`, gegenereerd uit de officiele CSF 2.0 Reference Tool-export |
| `wpg.json` | Wpg-toetsingskader voor boa-organisaties | `bronnen/wpg.json`, uit de NOREA-handreiking versie 2024 1.0 |
| `avg.json` | AVG | `bronnen/avg.json`, een redactionele selectie van 32 artikelen |

De **volgorde** staat in `tools/mappingen.py` (`VOLGORDE`) en is redactioneel: BIO 2.0 opent, want dat is
het kader waar de doelgroep op wordt bevraagd, daarna NIST CSF omdat dat het dichtst bij de aanvalspaden
staat, en dan de twee kaders die maar deels over beveiliging gaan. Een kader dat er niet in staat, laat de
tests falen; kies dus een plek in plaats van hem achteraan te laten belanden.

**Waarom de dekking per kader zo verschilt.** Hoe dichter een kader bij techniek en dreiging staat, hoe
meer een dreigingsgerichte zelfcheck ervan aantoont. BIO 2.0 komt op 49 procent, NIST CSF op 39, het
Wpg-kader op 22 en de AVG op 19. Dat is geen kwaliteitsverschil tussen de mappings maar een eigenschap van
de kaders zelf, en het is precies wat de witte vlekken zichtbaar maken.

**BIO 2.0 en ISO 27001 zijn een mapping, geen twee.** BIO 2.0 volgt de nummering van ISO 27002:2022
(bijlage A van ISO 27001). Maatregel `8.5` hier is dus zowel de BIO2-maatregel als de ISO-maatregel; de
overheidsmaatregelen die eronder vallen (`8.05.01` en verder) staan erbij. Dat scheelt een heel
mappingbestand.

**NIST CSF 2.0 blijft Engels.** Het framework staat in het publieke domein, dus de uitkomstformuleringen
mogen er letterlijk in; ze blijven Engels omdat het kader zo heet en iedereen er zo naar verwijst
(statuut A10, Engelse vaktermen blijven Engels). De export bevat ook de ingetrokken subcategorieen uit
CSF 1.1; die worden overgeslagen, zodat er precies 106 geldende subcategorieen overblijven.

**De AVG is een redactionele selectie.** De AVG kent artikelen, geen maatregelen. De 32 artikelen hier
zijn de toetspunten die in een AVG-toets aan bod komen; artikelen die alleen de toezichthouder of de
lidstaat binden staan er niet in. Vrijwel alle regels landen op art. 32, art. 5 lid 1 onder f, art. 25 en
art. 33, en dat is precies de taakverdeling die dit kader zichtbaar maakt.

**Waarom ook de Wpg.** Om te laten zien dat een dreigingsgerichte zelfcheck maar een deel van een
normenkader raakt, en dat dat klopt. Het Wpg-kader gaat over rechtmatige verwerking: doelbinding,
bewaartermijnen, verstrekking, rechten van betrokkenen. Geen aanvalspad zegt daar iets over. Wat de
zelfcheck wel raakt is beveiliging: maatregel 6 (art. 4a Wpg) en de technische maatregelen uit bijlage 4
van de handreiking, die volgens die bijlage naast de BIO gelden.

## Het handelingsperspectief: hoe pak ik het aan

De normverankering zegt wat je aantoont. Het handelingsperspectief zegt hoe je het doet: per barriere
een of meer handleidingen in de kennisbank, met de rol erbij. `fundering` is waar je begint,
`alternatief` is een van de routes waartussen je kiest, `verdieping` gaat verder dan de fundering. Bij
monitoring staan er vijf: zelf een SIEM, co-managed, uitbesteed, MDR of regionaal. Die keuze is het
advies, dus de pagina toont ze naast elkaar in plaats van er een te kiezen.

**De kennisbank is de bron, deze map heeft een kopie.** In de frontmatter van een kennisbank-item staat
`barrieres:` en `rol:`; `kennisbank/tools/build.py` exporteert dat, en
`tools/haal_handelingsperspectief.py` haalt het hierheen met een sha256 eronder. Zo staat een
handleiding op een plek. Werk `handelingsperspectief.json` dus nooit met de hand bij: dan klopt de
sha256 niet meer en valt CI om, en dat is precies de bedoeling.

Wat er **niet** staat is even belangrijk. Een barriere zonder handleiding staat in `gevraagd.json`, met
erbij wat het artikel zou moeten dekken. Dat bestand is wel handwerk, want wat een nog ongeschreven
handleiding zou moeten dekken weet de kennisbank niet. Het is tegelijk de redactieagenda en de
uitnodiging aan wie het wel weet: op de pagina krijgt zo'n gat een knop die een vooringevulde issue
opent, met de barrieres en het gevraagde bewijs er al in.

Stand op 30-08-2026: **35 van de 44 barrieres** hebben een handleiding, samen 50 koppelingen. De
overige 9 zijn gegroepeerd tot **8 schrijfopdrachten**, gesorteerd op gewicht.

**De mapping loopt per barriere, de backlog groepeert.** Een artikel over werkplekhardening bedient
`patch`, `localadmin` en `unmanaged` tegelijk. Per barriere mappen houdt het precies en machinaal
toetsbaar; groeperen tot een `cluster` maakt er een haalbare schrijfopdracht van.

**De volgorde komt uit de data.** Het gewicht is het aantal aanvalspaden waarop een barriere staat: wie
daar verbetert, sluit meer routes tegelijk. Een randvoorwaarde hangt aan geen enkel pad maar weegt over
alle paden mee, en krijgt daarom het aantal paden als gewicht; tellen op bladeren zou hem op nul zetten
en naar de bodem van de backlog laten zakken. Zodra er echte zelfcheck-uitslagen zijn, is het betere
signaal hoe vaak een barriere als actie uit `score.acties()` komt.

Twee tests bewaken dit, op verschillende plekken omdat ze verschillende dingen nodig hebben:
`tests/test_handelingsperspectief.py` toetst vorm, volledigheid en of de kopie nog gelijk is aan de
kennisbank, en `mappingen/tests/test_kennisbank_verwijzingen.py` toetst of het item bestaat en de
barriere daar zelf nog in de frontmatter staat. Die tweede heeft de kennisbank-repo ernaast nodig; CI
checkt hem uit naar `_kennisbank`.

## Auteursrecht

Per kader is dit anders geregeld, en dat is bewust:

| Kader | Wat mag | Wat er in de bron staat |
|---|---|---|
| BIO 2.0 / ISO 27001 | ISO 27002-teksten zijn auteursrechtelijk beschermd | Alleen nummer, titel en de BIO2-sub-ids. Een test blokkeert als er een veld met normtekst insluipt |
| NIST CSF 2.0 | Publiek domein | De uitkomstformuleringen van NIST zelf, letterlijk en in het Engels |
| Wpg | NOREA-handreiking: gebruik en verspreiding met bronvermelding | Eigen samenvattingen, met de bron erbij |
| AVG | Wetgeving, vrij | Eigen samenvattingen per artikel |

Kortom: alleen waar het kader zelf vrij is, staat de originele tekst erin. Overal elders staat een eigen
formulering en een verwijzing naar de bron.

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

De NIST-bron opnieuw genereren (alleen nodig bij een nieuwe CSF-versie):

```bash
curl -o nist-csf.xlsx "https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=all"
python mappingen/bronnen/genereer_nist.py nist-csf.xlsx
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
