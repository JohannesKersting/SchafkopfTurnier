"""Auswertungen über alle Tische eines Turniers für die Hauptseite."""

import wertung
from turnier import Turnier


def rangliste(turnier: Turnier) -> list[dict]:
    """Ein Eintrag pro Spieler, der schon an einem Tisch saß, sortiert und mit Rang.
    Punkte sind Gewinn/Verlust gegenüber den Startpunkten."""
    eintraege: dict[str, dict] = {}
    for runde in range(1, turnier.runden + 1):
        for tisch in turnier.tische:
            tr = turnier.tischrunde(runde, tisch)
            if not tr:
                continue
            endstand = tr.punkte_verlauf(turnier.startpunkte)[-1]
            for name in tr.spieler:
                eintrag = eintraege.setdefault(name, {"name": name, "runden": {}, "gesamt": 0,
                                                      **wertung.leere_statistik()})
                ergebnis = endstand[name] - turnier.startpunkte
                eintrag["runden"][runde] = ergebnis
                eintrag["gesamt"] += ergebnis
                for spiel in tr.spiele:
                    wertung.statistik_hinzufuegen(eintrag, name, spiel)
    return wertung.raenge(list(eintraege.values()))


def verlauf(turnier: Turnier, runde: int) -> dict[str, list[int]]:
    """Punkteverlauf je Spieler in einer Runde, Index = Spielnummer."""
    linien = {}
    for tisch in turnier.tische:
        tr = turnier.tischrunde(runde, tisch)
        if tr:
            punkte = tr.punkte_verlauf(turnier.startpunkte)
            for name in tr.spieler:
                linien[name] = [stand[name] for stand in punkte]
    return linien
