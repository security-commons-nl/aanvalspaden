#!/usr/bin/env python3
"""Haalt kern.js op uit procescheck: de gedeelde kern van de AI-hulp.

`kern.js` doet alles wat deterministisch is: schema-controle, chunking, samenvoegen, csv en xlsx lezen,
de citaatcontrole en het vergelijken en toepassen van een voorstel. Twee implementaties van die
citaatcontrole is er een te veel, want dan verschilt de hallucinatiecheck per tool. Daarom staat de
bron in procescheck (`ai/bron/kern.js`) en draagt deze repo een byte-identieke kopie.

Aanroep:
    python meting/ai/haal_kern.py            haalt de kern op en schrijft ai/bron/kern.js
    python meting/ai/haal_kern.py --check    faalt als de kopie afwijkt van de bron (CI)

De bron is de buurmap `../procescheck` als die er staat, anders de raw-URL van main. Alleen
standaardbibliotheek.
"""
from __future__ import annotations

import difflib
import pathlib
import sys
import urllib.request

HIER = pathlib.Path(__file__).resolve().parent
DOEL = HIER / "bron" / "kern.js"
BUURMAP = HIER.parent.parent.parent / "procescheck" / "ai" / "bron" / "kern.js"
RAW = ("https://raw.githubusercontent.com/security-commons-nl/procescheck/main/"
       "ai/bron/kern.js")


def haal_bron() -> tuple[str, str]:
    """(inhoud, herkomst). Regeleindes altijd LF, anders wijkt de kopie op Windows af."""
    if BUURMAP.is_file():
        return BUURMAP.read_text(encoding="utf-8").replace("\r\n", "\n"), str(BUURMAP)
    try:
        with urllib.request.urlopen(RAW, timeout=30) as antwoord:
            return antwoord.read().decode("utf-8").replace("\r\n", "\n"), RAW
    except OSError as fout:
        sys.exit(f"kan kern.js niet ophalen: {fout}\n"
                 f"Zet procescheck als buurmap neer, of zorg voor netwerk.")


def main(argv: list[str]) -> int:
    controleren = "--check" in argv
    bron, herkomst = haal_bron()

    if not DOEL.exists():
        if controleren:
            print(f"{DOEL} ontbreekt; draai zonder --check", file=sys.stderr)
            return 1
        DOEL.parent.mkdir(parents=True, exist_ok=True)
        DOEL.write_bytes(bron.encode("utf-8"))
        print(f"{DOEL}: nieuw, uit {herkomst}")
        return 0

    huidig = DOEL.read_text(encoding="utf-8").replace("\r\n", "\n")
    if huidig == bron:
        print(f"kern.js is gelijk aan {herkomst}")
        return 0
    if controleren:
        verschil = difflib.unified_diff(huidig.splitlines(), bron.splitlines(),
                                        fromfile="meting/ai/bron/kern.js", tofile=herkomst,
                                        lineterm="")
        print("\n".join(list(verschil)[:60]), file=sys.stderr)
        print("\nkern.js loopt uit de pas met procescheck. Draai `python meting/ai/haal_kern.py`.",
              file=sys.stderr)
        return 1
    DOEL.write_bytes(bron.encode("utf-8"))
    print(f"{DOEL}: bijgewerkt uit {herkomst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
