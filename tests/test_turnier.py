import csv
import os

import pytest

import auswertung
import einstellungen
import turnier as t
import wertung


TARIFE = {"sauspiel": 10, "solo": 20, "schneider": 10, "laufende": 10}


@pytest.fixture
def turnier(tmp_path, monkeypatch):
    monkeypatch.setattr(einstellungen, "DATA_DIR", str(tmp_path))
    t.cache_leeren()
    neu = t.Turnier(name="Test Türnier", runden=2, spiele_pro_runde=3, startpunkte=100,
                    tische=["Ober", "Unter"], spieler=["A", "B", "C", "D", "E", "F", "G", "H", "I"],
                    tarife=TARIFE)
    neu.erstellen()
    return t.Turnier.laden("Test Türnier")


def test_config_round_trip(turnier):
    assert turnier.tische == ["Ober", "Unter"]
    assert turnier.tarife == TARIFE
    assert t.turnier_liste() == ["Test Türnier"]


def test_doppelter_name(turnier):
    with pytest.raises(t.TurnierFehler):
        t.Turnier(name="Test Türnier", runden=1, spiele_pro_runde=1, startpunkte=0, tische=["x"],
                  spieler=list("ABCD")).erstellen()


def test_spieler_nur_an_einem_tisch(turnier):
    turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    with pytest.raises(t.TurnierFehler, match="anderen Tisch"):
        turnier.tisch_anlegen(1, "Unter", ["D", "E", "F", "G"])
    with pytest.raises(t.TurnierFehler, match="bereits angelegt"):
        turnier.tisch_anlegen(1, "Ober", ["E", "F", "G", "H"])
    turnier.tisch_anlegen(2, "Unter", ["D", "E", "F", "G"])
    assert turnier.aktuelle_runde("Unter") == 2
    assert turnier.aktuelle_runde("Ober") == 1


def test_spiele_eintragen_und_dateien(turnier):
    tr = turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    turnier.spiel_eintragen(tr, ["A", "C"], wertung.SAUSPIEL)
    tr = turnier.tischrunde(1, "Ober")
    turnier.spiel_eintragen(tr, ["B"], wertung.SOLO, "Schneider", 3, herzsolo=True)

    tr = turnier.tischrunde(1, "Ober")
    assert [s["geber"] for s in tr.spiele] == ["A", "B"]
    assert tr.spiele[1]["herzsolo"] == "B"
    assert tr.punkte_verlauf(100)[-1] == {"A": 50, "B": 270, "C": 50, "D": 30}

    with open(turnier.tisch_datei(1, "Ober", "punkte"), encoding="utf-8") as f:
        zeilen = list(csv.reader(f, delimiter="\t"))
    assert zeilen == [["spiel", "A", "B", "C", "D"], ["0", "100", "100", "100", "100"],
                      ["1", "110", "90", "110", "90"], ["2", "50", "270", "50", "30"]]


def test_veralteter_stand_wird_abgelehnt(turnier):
    tr = turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    turnier.spiel_eintragen(tr, ["A", "C"], wertung.SAUSPIEL)
    with pytest.raises(t.TurnierFehler, match="verändert"):
        turnier.spiel_eintragen(tr, ["A", "C"], wertung.SAUSPIEL)
    assert len(turnier.tischrunde(1, "Ober").spiele) == 1


def test_runde_beendet_und_rueckgaengig(turnier):
    turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    for _ in range(3):
        turnier.spiel_eintragen(turnier.tischrunde(1, "Ober"), ["A", "B"], wertung.SAUSPIEL)
    tr = turnier.tischrunde(1, "Ober")
    assert turnier.runde_beendet(tr)
    with pytest.raises(t.TurnierFehler, match="beendet"):
        turnier.spiel_eintragen(tr, ["A", "B"], wertung.SAUSPIEL)
    turnier.letztes_spiel_entfernen(tr)
    assert len(turnier.tischrunde(1, "Ober").spiele) == 2


def test_zusammenwerfen_nur_wenn_erlaubt(turnier):
    tr = turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    with pytest.raises(t.TurnierFehler, match="nicht erlaubt"):
        turnier.spiel_eintragen(tr, [], wertung.ZUSAMMENGEWORFEN)


def test_manuelle_aenderung_wird_erkannt(turnier):
    tr = turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    turnier.spiel_eintragen(tr, ["A", "C"], wertung.SAUSPIEL)
    assert turnier.tischrunde(1, "Ober").spiele[0]["punkte"]["A"] == 10
    pfad = turnier.tisch_datei(1, "Ober", "spiele")
    with open(pfad, encoding="utf-8") as f:
        inhalt = f.read()
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt.replace("\t10\t-10\t10\t-10", "\t20\t-20\t20\t-20"))
    os.utime(pfad, ns=(os.stat(pfad).st_mtime_ns + 10**9,) * 2)
    assert turnier.tischrunde(1, "Ober").spiele[0]["punkte"]["A"] == 20


def test_rangliste(turnier):
    tr = turnier.tisch_anlegen(1, "Ober", ["A", "B", "C", "D"])
    turnier.spiel_eintragen(tr, ["A"], wertung.WENZ)
    tr = turnier.tisch_anlegen(2, "Unter", ["A", "E", "F", "G"])
    turnier.spiel_eintragen(tr, ["E", "F"], wertung.SAUSPIEL)

    rangliste = {e["name"]: e for e in auswertung.rangliste(turnier)}
    assert rangliste["A"]["runden"] == {1: 60, 2: -10}
    assert rangliste["A"]["gesamt"] == 50
    assert rangliste["A"]["rang"] == 1
    assert rangliste["A"]["wenz_eigen_gewonnen"] == 1
    assert rangliste["B"]["wenz_fremd_verloren"] == 1
    assert "H" not in rangliste
