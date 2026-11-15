import pytest

import wertung
from wertung import SAUSPIEL, SIE, SOLO, TOUT, WENZ, ZUSAMMENGEWORFEN

TARIFE = {"sauspiel": 10, "solo": 20, "schneider": 10, "laufende": 10, "tout": 2, "sie": 4}
SPIELER = ["A", "B", "C", "D"]


@pytest.mark.parametrize("spielart, stufe, laufende, wert", [
    (SAUSPIEL, "Spiel", 0, 10),
    (SAUSPIEL, "Schneider", 0, 20),
    (SAUSPIEL, "Schwarz", 3, 60),
    (SOLO, "Spiel", 0, 20),
    (SOLO, "Schwarz", 8, 120),
    (WENZ, "Schneider", 2, 50),
    (SOLO, TOUT, 0, 40),
    (WENZ, TOUT, 3, 100),
    (SOLO, SIE, 8, 400),
])
def test_spielwert(spielart, stufe, laufende, wert):
    assert wertung.spielwert(TARIFE, spielart, stufe, laufende) == wert


@pytest.mark.parametrize("spielart, laufende", [(SAUSPIEL, 2), (SOLO, 9), (WENZ, 5), (WENZ, 1)])
def test_ungueltige_laufende(spielart, laufende):
    with pytest.raises(ValueError):
        wertung.spielwert(TARIFE, spielart, "Spiel", laufende)


@pytest.mark.parametrize("spielart, stufe, laufende", [
    (SAUSPIEL, TOUT, 0), (WENZ, SIE, 4), (SOLO, SIE, 0), (SOLO, SIE, 3)])
def test_ungueltige_stufe(spielart, stufe, laufende):
    with pytest.raises(ValueError):
        wertung.spielwert(TARIFE, spielart, stufe, laufende)


def test_sie_gewonnen():
    assert wertung.punkte_aenderungen(TARIFE, SPIELER, ["C"], SOLO, SIE, 8) == \
        {"A": -400, "B": -400, "C": 1200, "D": -400}


def test_sie_kann_man_nicht_verlieren():
    with pytest.raises(ValueError):
        wertung.punkte_aenderungen(TARIFE, SPIELER, ["A", "B", "D"], SOLO, SIE, 8)


def test_tout_verloren():
    assert wertung.punkte_aenderungen(TARIFE, SPIELER, ["A", "B", "D"], WENZ, TOUT, 2) == \
        {"A": 80, "B": 80, "C": -240, "D": 80}


def test_gewonnenes_solo_mit_allen_laufenden_ist_sie():
    with pytest.raises(ValueError):
        wertung.punkte_aenderungen(TARIFE, SPIELER, ["C"], SOLO, "Schwarz", 8)
    # Verloren: dann hatten die Gegenspieler alle Laufenden
    assert wertung.punkte_aenderungen(TARIFE, SPIELER, ["A", "B", "D"], SOLO, "Spiel", 8)["C"] == -300


def test_tout_faktor_einstellbar():
    assert wertung.spielwert({**TARIFE, "tout": 3}, SOLO, TOUT, 0) == 60


def test_sauspiel():
    assert wertung.punkte_aenderungen(TARIFE, SPIELER, ["A", "C"], SAUSPIEL, "Schneider") == \
        {"A": 20, "B": -20, "C": 20, "D": -20}


def test_solo_gewonnen():
    assert wertung.punkte_aenderungen(TARIFE, SPIELER, ["B"], SOLO, "Spiel", 3) == \
        {"A": -50, "B": 150, "C": -50, "D": -50}


def test_wenz_verloren():
    aenderung = wertung.punkte_aenderungen(TARIFE, SPIELER, ["A", "B", "D"], WENZ)
    assert aenderung == {"A": 20, "B": 20, "C": -60, "D": 20}
    assert sum(aenderung.values()) == 0


def test_zusammengeworfen():
    assert wertung.punkte_aenderungen(TARIFE, SPIELER, [], ZUSAMMENGEWORFEN) == dict.fromkeys(SPIELER, 0)


@pytest.mark.parametrize("gewinner", [[], ["A", "B", "C", "D"]])
def test_ungueltige_gewinner(gewinner):
    with pytest.raises(ValueError):
        wertung.punkte_aenderungen(TARIFE, SPIELER, gewinner, SOLO)


def test_sauspiel_braucht_zwei_gewinner():
    with pytest.raises(ValueError):
        wertung.punkte_aenderungen(TARIFE, SPIELER, ["A"], SAUSPIEL)


def test_geber_rotiert():
    assert [wertung.geber(SPIELER, n) for n in range(1, 7)] == ["A", "B", "C", "D", "A", "B"]


def test_statistik():
    statistik = wertung.leere_statistik()
    spiele = [
        {"spielart": SAUSPIEL, "spieler": "", "herzsolo": "", "punkte": {"A": 10}},
        {"spielart": SOLO, "spieler": "A", "herzsolo": "A", "punkte": {"A": 60}},
        {"spielart": SOLO, "spieler": "B", "herzsolo": "B", "punkte": {"A": -20}},
        {"spielart": WENZ, "spieler": "A", "herzsolo": "", "punkte": {"A": -60}},
        {"spielart": WENZ, "spieler": "C", "herzsolo": "", "punkte": {"A": 20}},
        {"spielart": ZUSAMMENGEWORFEN, "spieler": "", "herzsolo": "", "punkte": {"A": 0}},
    ]
    for spiel in spiele:
        wertung.statistik_hinzufuegen(statistik, "A", spiel)
    assert statistik == {
        "sauspiel_gewonnen": 1, "sauspiel_verloren": 0,
        "solo_eigen_gewonnen": 1, "solo_eigen_verloren": 0,
        "solo_fremd_gewonnen": 0, "solo_fremd_verloren": 1,
        "wenz_eigen_gewonnen": 0, "wenz_eigen_verloren": 1,
        "wenz_fremd_gewonnen": 1, "wenz_fremd_verloren": 0,
        "herzsoli": 1,
    }


def test_raenge_mit_gleichstand():
    eintraege = [
        {"name": "A", "gesamt": 200, "herzsoli": 0},
        {"name": "B", "gesamt": 210, "herzsoli": 0},
        {"name": "C", "gesamt": 200, "herzsoli": 1},
        {"name": "D", "gesamt": 200, "herzsoli": 0},
        {"name": "E", "gesamt": 190, "herzsoli": 3},
    ]
    assert [(e["name"], e["rang"]) for e in wertung.raenge(eintraege)] == \
        [("B", 1), ("C", 2), ("A", 3), ("D", 3), ("E", 5)]
