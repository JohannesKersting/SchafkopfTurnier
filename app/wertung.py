"""Reine Spiellogik: Punkte eines Spiels, Statistiken und Rangliste. Kein Dash, kein Datei-IO."""

SAUSPIEL = "Sauspiel"
SOLO = "Solo"
WENZ = "Wenz"
ZUSAMMENGEWORFEN = "Zusammengeworfen"

STUFEN = ["Spiel", "Schneider", "Schwarz"]

# Erlaubte Laufende (von, bis) je Spielart. 0 = keine Laufenden.
LAUFENDE = {
    SAUSPIEL: (3, 8),
    SOLO: (3, 8),
    WENZ: (2, 4),
}


def laufende_optionen(spielart: str) -> list[int]:
    von, bis = LAUFENDE[spielart]
    return [0] + list(range(von, bis + 1))


def spielwert(tarife: dict, spielart: str, stufe: str, laufende: int) -> int:
    """Wert des Spiels pro Gegenspieler."""
    if laufende not in laufende_optionen(spielart):
        raise ValueError(f"{laufende} Laufende sind bei {spielart} nicht möglich.")
    basis = tarife["sauspiel"] if spielart == SAUSPIEL else tarife["solo"]
    return basis + STUFEN.index(stufe) * tarife["schneider"] + laufende * tarife["laufende"]


def solospieler(spieler: list[str], gewinner: list[str]) -> str:
    """Bei einem Gewinner hat der Solospieler gewonnen, bei drei Gewinnern verloren."""
    if len(gewinner) == 1:
        return gewinner[0]
    if len(gewinner) == 3:
        return next(s for s in spieler if s not in gewinner)
    raise ValueError("Ein Solo braucht genau einen oder drei Gewinner.")


def moegliche_spielarten(anzahl_gewinner: int) -> list[str]:
    if anzahl_gewinner == 2:
        return [SAUSPIEL]
    if anzahl_gewinner in (1, 3):
        return [SOLO, WENZ]
    return []


def punkte_aenderungen(tarife: dict, spieler: list[str], gewinner: list[str], spielart: str,
                       stufe: str = STUFEN[0], laufende: int = 0) -> dict[str, int]:
    """Punkteänderung je Spieler für ein Spiel. Die Summe ist immer 0."""
    if spielart == ZUSAMMENGEWORFEN:
        return {s: 0 for s in spieler}
    if spielart not in moegliche_spielarten(len(gewinner)):
        raise ValueError(f"{spielart} passt nicht zu {len(gewinner)} Gewinnern.")

    wert = spielwert(tarife, spielart, stufe, laufende)
    if spielart == SAUSPIEL:
        return {s: wert if s in gewinner else -wert for s in spieler}

    solist = solospieler(spieler, gewinner)
    vorzeichen = 1 if solist in gewinner else -1
    return {s: vorzeichen * (3 * wert if s == solist else -wert) for s in spieler}


def geber(spieler: list[str], spielnummer: int) -> str:
    """Spieler 0 (oben links) gibt das erste Spiel, danach im Uhrzeigersinn."""
    return spieler[(spielnummer - 1) % len(spieler)]


def leere_statistik() -> dict:
    return {
        "sauspiel_gewonnen": 0, "sauspiel_verloren": 0,
        "solo_eigen_gewonnen": 0, "solo_eigen_verloren": 0,
        "solo_fremd_gewonnen": 0, "solo_fremd_verloren": 0,
        "wenz_eigen_gewonnen": 0, "wenz_eigen_verloren": 0,
        "wenz_fremd_gewonnen": 0, "wenz_fremd_verloren": 0,
        "herzsoli": 0,
    }


def statistik_hinzufuegen(statistik: dict, name: str, spiel: dict) -> None:
    """Zählt ein Spiel (Zeile der Spiele-Datei) in die Statistik von `name` ein."""
    delta = spiel["punkte"][name]
    ergebnis = "gewonnen" if delta > 0 else "verloren"
    art = spiel["spielart"]
    eigen = spiel["spieler"] == name

    if art == SAUSPIEL:
        statistik[f"sauspiel_{ergebnis}"] += 1
    elif art in (SOLO, WENZ):
        statistik[f"{art.lower()}_{'eigen' if eigen else 'fremd'}_{ergebnis}"] += 1

    if spiel["herzsolo"] == name:
        statistik["herzsoli"] += 1


def raenge(eintraege: list[dict]) -> list[dict]:
    """Sortiert nach Gesamtpunkten, dann Herzsoli. Gleichstand in beidem ergibt den gleichen Rang."""
    sortiert = sorted(eintraege, key=lambda e: (-e["gesamt"], -e["herzsoli"]))
    vorher = None
    for i, eintrag in enumerate(sortiert):
        schluessel = (eintrag["gesamt"], eintrag["herzsoli"])
        if schluessel != vorher:
            rang = i + 1
            vorher = schluessel
        eintrag["rang"] = rang
    return sortiert
