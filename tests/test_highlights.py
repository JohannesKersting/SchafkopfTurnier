import pytest

import einstellungen
import highlights
import turnier as t
import wertung

TARIFE = {"sauspiel": 10, "solo": 20, "schneider": 10, "laufende": 10, "tout": 2, "sie": 4}


def test_waehle():
    assert highlights.waehle({"A": 3, "B": 1}) == ["A"]
    assert highlights.waehle({"A": 3, "B": 3, "C": 3}) == ["A", "B", "C"]
    assert highlights.waehle({"A": 3, "B": 3, "C": 3, "D": 3}) is None
    assert highlights.waehle({"A": 0, "B": 0}) is None
    assert highlights.waehle({"A": 0, "B": 2}, groesste=False) == ["A"]
    assert highlights.waehle({}) is None


def test_laengste_serie():
    deltas = [10, 20, -10, 10, 10, 10, -5, -5]
    assert highlights.laengste_serie(deltas, gewonnen=True) == 3
    assert highlights.laengste_serie(deltas, gewonnen=False) == 2


def test_zahlungen_sauspiel_halbiert():
    assert highlights.zahlungen({"A": 10, "B": -10, "C": 10, "D": -10}) == {
        ("B", "A"): 5, ("B", "C"): 5, ("D", "A"): 5, ("D", "C"): 5}


@pytest.mark.parametrize("delta, erwartet", [
    ({"A": 60, "B": -20, "C": -20, "D": -20}, {("B", "A"): 20, ("C", "A"): 20, ("D", "A"): 20}),
    ({"A": -60, "B": 20, "C": 20, "D": 20}, {("A", "B"): 20, ("A", "C"): 20, ("A", "D"): 20}),
])
def test_zahlungen_solo(delta, erwartet):
    assert highlights.zahlungen(delta) == erwartet


@pytest.fixture
def turnier(tmp_path, monkeypatch):
    monkeypatch.setattr(einstellungen, "DATA_DIR", str(tmp_path))
    t.cache_leeren()
    t.Turnier(name="HL", runden=1, spiele_pro_runde=3, startpunkte=100, tische=["Ober"],
              spieler=list("ABCD"), tarife=TARIFE).erstellen()
    turnier = t.Turnier.laden("HL")
    turnier.tisch_anlegen(1, "Ober", list("ABCD"))
    for gewinner, art, stufe, laufende, herz in [
        (["A", "C"], wertung.SAUSPIEL, "Spiel", 0, False),        # A, C +10
        (["B"], wertung.SOLO, "Schneider", 3, True),              # B +180, Rest -60
        (["B", "C", "D"], wertung.WENZ, "Spiel", 0, False),       # A -60, Rest +20
    ]:
        turnier.spiel_eintragen(turnier.tischrunde(1, "Ober"), gewinner, art, stufe, laufende, herz)
    return turnier


def karten(turnier):
    return {k["titel"]: [(e["name"], e["wert"], e["detail"]) for e in k["eintraege"]]
            for k in highlights.highlights(turnier)}


def test_highlights(turnier):
    k = karten(turnier)
    assert k["Ein Spiel und ausgesorgt!"] == [("B", 180, "Runde 1 · Ober · Spiel 2")]
    assert "Das war teuer" not in k  # vier Mal -60: zu viele Gleichstände
    assert k["Läuft bei dir!"] == [("B", 90, "")]
    assert k["Geht auch alleine"] == [("B", 1, "")]
    assert k["„Muas ma spuin“"] == [("A", 1, "")]
    assert k["A Herz hot a jeder"] == [("B", 1, "")]
    assert k["Kleinvieh macht auch Mist!"] == [("A", 1, ""), ("C", 1, "")]
    assert k["Dynamisches Duo"] == [("A & C", 1, "")]
    assert k["Erzfeind"] == [("A → B", 75, "")]
    assert k["On fire"] == [("B", 2, "")]
    assert k["Pechsträhne"] == [("A", 2, ""), ("D", 2, "")]
    assert k["Keine Chance"] == [("A", 1, ""), ("C", 1, ""), ("D", 1, "")]
    assert k["Koa Risiko!"] == [("C", 0, ""), ("D", 0, "")]
    assert k["Warum spiel ich eigentlich mit?"] == [("C", -30, "")]
    assert k["Wilde Runde"] == [("Ober (A, B, C, D)", 2, "Runde 1")]
    assert "Comeback" not in k  # nur eine Runde
    assert "Solist" in k and "Alle Unter!" in k
    assert "Schwarz gspuit!" not in k


@pytest.mark.parametrize("gewinner, art, erwartet", [
    (["A", "C"], wertung.SAUSPIEL, ("A & C", wertung.SAUSPIEL)),
    (["B"], wertung.SOLO, ("B", wertung.SOLO)),
    (["B", "C", "D"], wertung.WENZ, ("B, C & D", f"gegen {wertung.WENZ}")),
])
def test_schwarz_gspuit(turnier, gewinner, art, erwartet):
    turnier.letztes_spiel_entfernen(turnier.tischrunde(1, "Ober"))
    turnier.spiel_eintragen(turnier.tischrunde(1, "Ober"), gewinner, art, "Schwarz")
    assert karten(turnier)["Schwarz gspuit!"] == [(*erwartet, "Runde 1 · Ober · Spiel 3")]


@pytest.mark.parametrize("gewinner, titel", [(["B"], "Tout gspuit!"), (["A", "C", "D"], "Zu hoch gepokert")])
def test_tout(turnier, gewinner, titel):
    turnier.letztes_spiel_entfernen(turnier.tischrunde(1, "Ober"))
    turnier.spiel_eintragen(turnier.tischrunde(1, "Ober"), gewinner, wertung.WENZ, wertung.TOUT)
    k = karten(turnier)
    assert k[titel] == [("B", wertung.WENZ, "Runde 1 · Ober · Spiel 3")]
    assert "Schwarz gspuit!" not in k
    andere = "Zu hoch gepokert" if titel == "Tout gspuit!" else "Tout gspuit!"
    assert andere not in k


def test_sie(turnier):
    turnier.letztes_spiel_entfernen(turnier.tischrunde(1, "Ober"))
    turnier.spiel_eintragen(turnier.tischrunde(1, "Ober"), ["D"], wertung.SOLO, wertung.SIE, wertung.SIE_LAUFENDE)
    k = karten(turnier)
    assert k["Des kimmt an d'Wand!"] == [("D", "", "Runde 1 · Ober · Spiel 3")]
    assert k["Läuft bei dir!"] == [("D", 4 * 8 * TARIFE["laufende"] * 3, "")]
    assert "Schwarz gspuit!" not in k


def test_minimum_karten_erst_nach_turnierende(turnier):
    turnier.letztes_spiel_entfernen(turnier.tischrunde(1, "Ober"))
    k = karten(turnier)
    for titel in ["Koa Risiko!", "A bisserl was geht immer", "Warum spiel ich eigentlich mit?", "Kaffeekränzchen"]:
        assert titel not in k
    assert "Ein Spiel und ausgesorgt!" in k


def test_leeres_turnier(tmp_path, monkeypatch):
    monkeypatch.setattr(einstellungen, "DATA_DIR", str(tmp_path))
    t.cache_leeren()
    t.Turnier(name="Leer", runden=2, spiele_pro_runde=3, startpunkte=0, tische=["x"],
              spieler=list("ABCD")).erstellen()
    assert highlights.highlights(t.Turnier.laden("Leer")) == []
