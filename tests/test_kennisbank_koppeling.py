"""AP09 is op twee plekken uitgewerkt. Als de bron wijzigt, moet de andere plek mee.

Het kennisbankitem "De killchain naast je controls leggen" bevat een killchain-tabel voor ClickFix met alle
MITRE-fasen. Dat is een andere snit dan AP09 hier, dat de barrieres toetst die de zelfcheck stelt, maar ze
gaan over dezelfde aanval. Die tabel wordt met de hand onderhouden en kan dus stil achterlopen.

Deze test legt vast hoe AP09 er nu uitziet. Wijzigt dat, dan faalt de test met de vraag of het
kennisbankitem ook bijgewerkt moet worden. Bevestigen doe je door de lijst hieronder bij te werken; dat is
een bewuste handeling en geen automatisme.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import paden as helper  # noqa: E402

# Vastgelegd op 29-08-2026, toen het kennisbankitem is gemaakt.
AP09_VASTGELEGD = [
    "Beperk software- en scriptuitvoering met application control en ASR",
    "Hard browsers en beperk extensies en gegevensdragers",
    "Verwijder lokale administratorrechten",
    "Borg EDR, tamper protection en snelle endpointisolatie",
]
KENNISBANKITEM = "kennisbank/security/killchain-naast-je-controls/"


def test_ap09_is_onveranderd_of_het_kennisbankitem_is_bijgewerkt():
    blad = helper.blad("AP09")
    titels = [cp["titel"] for cp in blad["chokepoints"]]
    assert titels == AP09_VASTGELEGD, (
        "AP09 is gewijzigd. De killchain-tabel in "
        f"{KENNISBANKITEM} gaat over dezelfde aanval en wordt met de hand onderhouden. "
        "Werk die tabel bij (of stel vast dat het niet nodig is) en pas daarna de lijst in deze test aan.\n"
        f"nu:        {titels}\nvastgelegd: {AP09_VASTGELEGD}"
    )


def test_ap09_gaat_nog_steeds_over_clickfix():
    blad = helper.blad("AP09")
    assert "ClickFix" in blad["titel"], blad["titel"]
