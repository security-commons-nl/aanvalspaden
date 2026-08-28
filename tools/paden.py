"""Toegang tot paden.json, de enige bron voor de aanvalspaden.

Wie een pad, chokepoint of vraag nodig heeft, haalt hem hier op. Nooit een kopie in code.
"""
from __future__ import annotations

import json
import pathlib

PAD = pathlib.Path(__file__).resolve().parent.parent / "paden.json"


def laad() -> dict:
    """De hele bron als dict."""
    return json.loads(PAD.read_text(encoding="utf-8"))


def bladeren() -> list[dict]:
    """Alle achttien bladeren, paden en impact door elkaar."""
    return laad()["bladeren"]


def paden() -> list[dict]:
    """Alleen de bladeren van het type pad; die vormen de kolommen van de matrix."""
    return [b for b in bladeren() if b["type"] == "pad"]


def blad(ap_id: str) -> dict | None:
    """Eén blad op id, of None."""
    return next((b for b in bladeren() if b["id"] == ap_id), None)


def cluster_van(ap_id: str) -> dict | None:
    """Het cluster waar dit blad in zit, of None (impact zit in geen cluster)."""
    return next((c for c in laad()["clusters"] if ap_id in c["bladeren"]), None)


def chokepoints() -> list[dict]:
    """Alle chokepoints, met hun blad-id erbij onder de sleutel blad."""
    return [dict(cp, blad=b["id"]) for b in bladeren() for cp in b["chokepoints"]]


def chokepoint(cp_id: str) -> dict | None:
    """Eén chokepoint op id, of None."""
    return next((cp for cp in chokepoints() if cp["id"] == cp_id), None)
