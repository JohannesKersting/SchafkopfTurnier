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


ALLE_RUNDEN = 0


def verlauf(turnier: Turnier, runde: int) -> dict[str, list[tuple[int, int, int, int]]]:
    """Punkteverlauf je Spieler als Liste von (x, punkte, runde, spiel).

    Bei einer einzelnen Runde ist x die Spielnummer. Bei ALLE_RUNDEN laufen die Runden hintereinander
    (x = (runde - 1) * spiele_pro_runde + spiel) und die Punkte sind der Gesamtstand: Startpunkte plus
    die Ergebnisse der früheren Runden. Der Start einer späteren Runde fällt dann auf das Ende der
    vorherigen und wird weggelassen."""
    alle = runde == ALLE_RUNDEN
    runden = range(1, turnier.runden + 1) if alle else [runde]
    linien: dict[str, list] = {}
    vorher: dict[str, int] = {}  # Ergebnis der früheren Runden
    for r in runden:
        versatz = (r - 1) * turnier.spiele_pro_runde if alle else 0
        ergebnisse = {}
        for tisch in turnier.tische:
            tr = turnier.tischrunde(r, tisch)
            if not tr:
                continue
            punkte = tr.punkte_verlauf(turnier.startpunkte)
            for name in tr.spieler:
                linie = linien.setdefault(name, [])
                for spiel, stand in enumerate(punkte):
                    if spiel == 0 and linie:
                        continue
                    linie.append((versatz + spiel, stand[name] + vorher.get(name, 0), r, spiel))
                ergebnisse[name] = punkte[-1][name] - turnier.startpunkte
        for name, ergebnis in ergebnisse.items():
            vorher[name] = vorher.get(name, 0) + ergebnis
    return linien
