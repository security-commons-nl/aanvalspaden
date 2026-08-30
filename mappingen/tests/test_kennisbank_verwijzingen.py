"""De verwijzingen naar de kennisbank: bestaat het item, en bestaat de paragraaf?

Een dode verwijzing is erger dan geen verwijzing, want hij belooft iets dat er niet is. Deze test
staat hier en niet in tests/, omdat hij een tweede repo nodig heeft: lokaal staat de kennisbank
ernaast, in CI wordt hij door de mappingen-job uitgecheckt naar `_kennisbank`.

Naast tests/test_kennisbank_koppeling.py, niet in plaats daarvan: die bewaakt of de inhoud van AP09
niet uit elkaar loopt met de killchain-tabel in het kennisbank-item. Dat is inhoudelijke drift; dit
gaat over verwijzingen die bestaan. Twee verschillende risico's.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

HIER = pathlib.Path(__file__).resolve().parent
MAP = HIER.parent
REPO = MAP.parent
sys.path.insert(0, str(REPO))

from tools import mappingen as helper  # noqa: E402

DATA = helper.handelingsperspectief()

# Lokaal staat de kennisbank naast deze repo; in CI wordt hij binnen de workspace uitgecheckt, want
# een checkout buiten $GITHUB_WORKSPACE wordt geweigerd.
KANDIDATEN = (REPO.parent / "kennisbank", REPO / "_kennisbank")
KENNISBANK = next((k for k in KANDIDATEN if k.is_dir()), None)

pytestmark = pytest.mark.skipif(
    KENNISBANK is None,
    reason=f"kennisbank niet gevonden op {[str(k) for k in KANDIDATEN]}",
)


@pytest.mark.parametrize("hl", DATA["handleidingen"], ids=[h["barriere"] for h in DATA["handleidingen"]])
def test_het_item_bestaat(hl):
    readme = KENNISBANK / hl["item"] / "README.md"
    assert readme.is_file(), (
        f"{hl['barriere']}: kennisbank-item {hl['item']} bestaat niet. Is het hernoemd of verplaatst, "
        "werk dan de verwijzing bij."
    )


@pytest.mark.parametrize("hl", DATA["handleidingen"], ids=[h["barriere"] for h in DATA["handleidingen"]])
def test_de_paragraaf_bestaat(hl):
    tekst = (KENNISBANK / hl["item"] / "README.md").read_text(encoding="utf-8")
    koppen = re.findall(r"^##\s+(.+?)\s*$", tekst, re.M)
    assert hl["paragraaf"] in koppen, (
        f"{hl['barriere']}: paragraaf {hl['paragraaf']!r} staat niet in {hl['item']}. "
        f"Is de kop hernoemd, werk dan de verwijzing bij. Gevonden koppen: {koppen}"
    )


def test_verwezen_items_hebben_een_leesversie():
    """De verwijzing gaat naar de site, dus daar moet een pagina staan (statuut B3)."""
    for hl in DATA["handleidingen"]:
        pagina = KENNISBANK / hl["item"] / "index.html"
        assert pagina.is_file(), (
            f"{hl['barriere']}: {hl['item']} heeft geen index.html, dus de link naar de site loopt dood"
        )
