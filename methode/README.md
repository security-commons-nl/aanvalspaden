# De methode: van open pad naar risicolijst

De zelfcheck (diepte 0) zegt welke aanvalspaden open staan. De methode (diepte 1) vertaalt dat met de lijn
erbij naar risico's met een maatregel en een eigenaar. De volledige methode, met het papieren sjabloon en
een ingevuld voorbeeld, staat in de kennisbank:

**[Risicoanalyse langs aanvalspaden](https://security-commons-nl.github.io/kennisbank/security/risicoanalyse-aanvalspaden/)**

In het kort, vier stappen:

1. **Kroonjuwelen, maximaal tien.** Welke processen of gegevens doen bestuurlijk pijn als ze uitvallen of
   lekken? Dit is het enige stuk waar je de lijn voor nodig hebt. Tien is de grens: wie de top tien niet
   haalt, telt in deze ronde niet mee.
2. **De aanvalspaden.** De vijf clusters uit [`paden.json`](../paden.json); de achttien bladeren zijn het
   detail. Je hoeft ze niet zelf te bedenken, en een pad schrappen omdat het "bij ons niet speelt" is
   precies de aanname die je wilt toetsen.
3. **Dekking meten met bewijs.** Per open pad en kroonjuweel: zien we het (D), weten we wat we doen (R),
   houden we het tegen (P). Groen alleen met een bewijslink; elk chokepoint in de bron zegt welk artefact
   dat is.
4. **De rode cellen zijn de risicolijst.** Elk risico heeft meteen een maatregel (het chokepoint dichten),
   een eigenaar (die van het kroonjuweel) en een termijn, of een bewuste acceptatie door de risico-eigenaar.

De zelfcheck neemt stap 2 en het grootste deel van stap 3 uit handen: je weet al welke paden open staan en
welke chokepoints daaronder zitten. In de app ga je na het resultaat verder met stap 1 en 4.

## Waarom de dekking uit de zelfcheck niet meetelt als bewijs

In de zelfcheck antwoord je zelf. Dat is genoeg om te bepalen waar je moet kijken, en te weinig om te zeggen
dat iets gedekt is. Daarom begint elke cel in de matrix rood zodra je hem aankruist als geraakt, ook als de
zelfcheck bij dat pad "sterk beheerst" gaf. Een cel wordt groen als er een artefact onder ligt: een export,
een configuratie, een testverslag. Diepte 2 (de meting) levert precies die artefacten.
