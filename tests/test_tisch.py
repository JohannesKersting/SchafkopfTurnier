import pytest

import wertung
from seiten import tisch

SIE, SPIEL = wertung.SIE, wertung.STUFEN[0]


@pytest.mark.parametrize("vorher, geaendert, wert, nachher", [
    ((SPIEL, 3), "stufe", SIE, (SIE, 8)),
    ((SPIEL, 3), "laufende", 8, (SIE, 8)),
    ((SIE, 8), "stufe", "Tout", ("Tout", 0)),
    ((SIE, 8), "laufende", 5, (SPIEL, 5)),
    ((SPIEL, 3), "laufende", 4, (SPIEL, 4)),
])
def test_sie_gekoppelt(vorher, geaendert, wert, nachher):
    ui = {"spielart": wertung.SOLO, "auswahl": ["A"], "stufe": vorher[0], "laufende": vorher[1], "herzsolo": True}
    ui[geaendert] = wert
    tisch.sie_gekoppelt(ui, geaendert)
    assert (ui["stufe"], ui["laufende"]) == nachher
    assert ui["herzsolo"] == (nachher[0] != SIE)


def test_verlorenes_solo_nicht_gekoppelt():
    ui = {"spielart": wertung.SOLO, "auswahl": ["A", "B", "C"], "stufe": SPIEL, "laufende": 8}
    tisch.sie_gekoppelt(ui, "laufende")
    assert ui["stufe"] == SPIEL
