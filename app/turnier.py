"""Turnier-Konfiguration und Tisch-Dateien. Die Dateien sind die einzige Datenquelle,
gelesene Dateien werden anhand ihres Änderungszeitpunkts im Speicher gecacht."""

import csv
import io
import os
import re
import threading
from dataclasses import dataclass, field, asdict

import yaml

import einstellungen
import wertung

CONFIG_DATEI = "turnier.yaml"
TRENNZEICHEN = "\t"
SPIELE_SPALTEN = ["spiel", "geber", "spielart", "stufe", "laufende", "spieler", "herzsolo"]
STANDARD_TARIFE = {"sauspiel": 1, "solo": 2, "schneider": 1, "laufende": 1}
RESERVIERTE_NAMEN = {"admin", "assets"}

_schreib_lock = threading.Lock()
_cache: dict[str, tuple[tuple[int, int, int], object]] = {}


class TurnierFehler(Exception):
    """Fehler, die dem Benutzer angezeigt werden."""


def cache_leeren() -> None:
    _cache.clear()


def _gecacht(pfad: str, lader):
    """Liefert lader(pfad), liest die Datei aber nur neu, wenn sie sich geändert hat."""
    try:
        stat = os.stat(pfad)
    except FileNotFoundError:
        _cache.pop(pfad, None)
        return None
    version = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
    eintrag = _cache.get(pfad)
    if eintrag and eintrag[0] == version:
        return eintrag[1]
    wert = lader(pfad)
    _cache[pfad] = (version, wert)
    return wert


def _atomar_schreiben(pfad: str, inhalt: str) -> None:
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(inhalt)
    os.replace(tmp, pfad)


def name_fehler(name: str, art: str) -> str | None:
    """Prüft Turnier-, Tisch- oder Spielernamen. Gibt eine Fehlermeldung oder None zurück."""
    if not name:
        return f"{art} dürfen nicht leer sein."
    if re.search(r"[/\\]", name):
        return f"{art} dürfen keine '/' oder '\\' enthalten."
    if name.startswith((".", "_")):
        return f"{art} dürfen nicht mit '.' oder '_' beginnen."
    return None


def turnier_liste() -> list[str]:
    if not os.path.isdir(einstellungen.DATA_DIR):
        return []
    return sorted(n for n in os.listdir(einstellungen.DATA_DIR)
                  if os.path.isfile(os.path.join(einstellungen.DATA_DIR, n, CONFIG_DATEI)))


@dataclass
class Tischrunde:
    """Eine Runde an einem Tisch: Sitzordnung und alle bisher gespielten Spiele."""
    runde: int
    tisch: str
    spieler: list[str]
    spiele: list[dict] = field(default_factory=list)

    @property
    def naechstes_spiel(self) -> int:
        return len(self.spiele) + 1

    def punkte_verlauf(self, startpunkte: int) -> list[dict[str, int]]:
        """Punktestand nach jedem Spiel, Index 0 = Startpunkte."""
        stand = {s: startpunkte for s in self.spieler}
        verlauf = [dict(stand)]
        for spiel in self.spiele:
            for s in self.spieler:
                stand[s] += spiel["punkte"][s]
            verlauf.append(dict(stand))
        return verlauf


@dataclass
class Turnier:
    name: str
    runden: int
    spiele_pro_runde: int
    startpunkte: int
    tische: list[str]
    spieler: list[str]
    tarife: dict = field(default_factory=lambda: dict(STANDARD_TARIFE))
    zusammenwerfen_erlaubt: bool = False
    basis_url: str = ""

    # --- Konfiguration ---

    @property
    def pfad(self) -> str:
        return os.path.join(einstellungen.DATA_DIR, self.name)

    @classmethod
    def laden(cls, name: str) -> "Turnier | None":
        if name_fehler(name, "Turniere"):
            return None
        return _gecacht(os.path.join(einstellungen.DATA_DIR, name, CONFIG_DATEI), cls._aus_datei)

    @classmethod
    def _aus_datei(cls, pfad: str) -> "Turnier":
        with open(pfad, encoding="utf-8") as f:
            daten = yaml.safe_load(f)
        daten["name"] = os.path.basename(os.path.dirname(pfad))
        daten["tische"] = [str(t) for t in daten["tische"]]
        daten["spieler"] = [str(s) for s in daten["spieler"]]
        daten["tarife"] = {**STANDARD_TARIFE, **(daten.get("tarife") or {})}
        return cls(**daten)

    def speichern(self) -> None:
        inhalt = yaml.safe_dump(asdict(self), allow_unicode=True, sort_keys=False)
        _atomar_schreiben(os.path.join(self.pfad, CONFIG_DATEI), inhalt)

    def erstellen(self) -> None:
        if fehler := name_fehler(self.name, "Turniernamen"):
            raise TurnierFehler(fehler)
        if self.name.lower() in RESERVIERTE_NAMEN:
            raise TurnierFehler(f"Der Name '{self.name}' ist reserviert.")
        os.makedirs(einstellungen.DATA_DIR, exist_ok=True)
        try:
            os.mkdir(self.pfad)
        except FileExistsError:
            raise TurnierFehler("Dieser Name ist bereits vergeben.")
        self.speichern()

    def __str__(self):
        return (f"{self.name}: {self.runden} Runden mit {self.spiele_pro_runde} Spielen pro Runde "
                f"an {len(self.tische)} Tischen mit {len(self.spieler)} Spielern.")

    # --- Tisch-Dateien ---

    def tisch_datei(self, runde: int, tisch: str, art: str) -> str:
        return os.path.join(self.pfad, f"runde{runde}_{tisch}_{art}.tsv")

    def tischrunde(self, runde: int, tisch: str) -> Tischrunde | None:
        return _gecacht(self.tisch_datei(runde, tisch, "spiele"),
                        lambda pfad: _spiele_lesen(pfad, runde, tisch))

    def aktuelle_runde(self, tisch: str) -> int:
        """Höchste Runde, für die der Tisch angelegt ist. 0, wenn noch nie."""
        return max((r for r in range(1, self.runden + 1)
                    if os.path.exists(self.tisch_datei(r, tisch, "spiele"))), default=0)

    def runde_beendet(self, tischrunde: Tischrunde) -> bool:
        return len(tischrunde.spiele) >= self.spiele_pro_runde

    def sitzende_spieler(self, runde: int) -> dict[str, str]:
        """Spieler, die in dieser Runde schon an einem Tisch sitzen -> Tischname."""
        belegt = {}
        for tisch in self.tische:
            tr = self.tischrunde(runde, tisch)
            if tr:
                belegt.update({s: tisch for s in tr.spieler})
        return belegt

    def tisch_anlegen(self, runde: int, tisch: str, spieler: list[str]) -> Tischrunde:
        if len(spieler) != 4 or not all(spieler):
            raise TurnierFehler("Es müssen alle vier Plätze besetzt sein.")
        if len(set(spieler)) != 4:
            raise TurnierFehler("Ein Spieler kann nicht auf zwei Plätzen sitzen.")
        with _schreib_lock:
            if os.path.exists(self.tisch_datei(runde, tisch, "spiele")):
                raise TurnierFehler("Der Tisch wurde in dieser Runde bereits angelegt.")
            belegt = self.sitzende_spieler(runde)
            doppelt = [f"{s} (Tisch {belegt[s]})" for s in spieler if s in belegt]
            if doppelt:
                raise TurnierFehler(f"Sitzen schon an einem anderen Tisch: {', '.join(doppelt)}")
            tr = Tischrunde(runde, tisch, spieler)
            self._dateien_schreiben(tr)
        return tr

    def spiel_eintragen(self, tr: Tischrunde, gewinner: list[str], spielart: str,
                        stufe: str = wertung.STUFEN[0], laufende: int = 0, herzsolo: bool = False) -> None:
        """Hängt ein Spiel an. `tr` ist der Stand, den der Benutzer gesehen hat; hat sich die Datei
        inzwischen geändert (z.B. doppelt abgeschickt), wird abgebrochen."""
        if spielart == wertung.ZUSAMMENGEWORFEN and not self.zusammenwerfen_erlaubt:
            raise TurnierFehler("Zusammenwerfen ist in diesem Turnier nicht erlaubt.")
        punkte = wertung.punkte_aenderungen(self.tarife, tr.spieler, gewinner, spielart, stufe, laufende)
        solist = wertung.solospieler(tr.spieler, gewinner) if spielart in (wertung.SOLO, wertung.WENZ) else ""
        with _schreib_lock:
            aktuell = self._aktuell_pruefen(tr)
            if self.runde_beendet(aktuell):
                raise TurnierFehler("Die Runde ist bereits beendet.")
            aktuell.spiele.append({
                "spiel": aktuell.naechstes_spiel,
                "geber": wertung.geber(aktuell.spieler, aktuell.naechstes_spiel),
                "spielart": spielart,
                "stufe": stufe if spielart != wertung.ZUSAMMENGEWORFEN else "",
                "laufende": laufende,
                "spieler": solist,
                "herzsolo": solist if herzsolo and spielart == wertung.SOLO else "",
                "punkte": punkte,
            })
            self._dateien_schreiben(aktuell)

    def letztes_spiel_entfernen(self, tr: Tischrunde) -> None:
        with _schreib_lock:
            aktuell = self._aktuell_pruefen(tr)
            if not aktuell.spiele:
                raise TurnierFehler("Es gibt kein Spiel zum Entfernen.")
            aktuell.spiele.pop()
            self._dateien_schreiben(aktuell)

    def _aktuell_pruefen(self, tr: Tischrunde) -> Tischrunde:
        aktuell = _spiele_lesen(self.tisch_datei(tr.runde, tr.tisch, "spiele"), tr.runde, tr.tisch)
        if aktuell.spieler != tr.spieler or len(aktuell.spiele) != len(tr.spiele):
            raise TurnierFehler("Der Tisch wurde inzwischen verändert. Die Ansicht ist jetzt aktualisiert.")
        return aktuell

    def _dateien_schreiben(self, tr: Tischrunde) -> None:
        """Die Spiele-Datei ist die Quelle, die Punkte-Datei wird daraus erzeugt."""
        _atomar_schreiben(self.tisch_datei(tr.runde, tr.tisch, "spiele"), _tsv(
            [SPIELE_SPALTEN + tr.spieler] +
            [[spiel[s] for s in SPIELE_SPALTEN] + [spiel["punkte"][s] for s in tr.spieler] for spiel in tr.spiele]
        ))
        _atomar_schreiben(self.tisch_datei(tr.runde, tr.tisch, "punkte"), _tsv(
            [["spiel"] + tr.spieler] +
            [[i] + [stand[s] for s in tr.spieler] for i, stand in enumerate(tr.punkte_verlauf(self.startpunkte))]
        ))


def _tsv(zeilen: list[list]) -> str:
    puffer = io.StringIO()
    csv.writer(puffer, delimiter=TRENNZEICHEN, lineterminator="\n").writerows(zeilen)
    return puffer.getvalue()


def _spiele_lesen(pfad: str, runde: int, tisch: str) -> Tischrunde:
    """Liest die Spiele-Datei. Spalten: SPIELE_SPALTEN, danach eine Spalte pro Spieler."""
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        zeilen = [z for z in csv.reader(f, delimiter=TRENNZEICHEN) if any(zelle.strip() for zelle in z)]
    n = len(SPIELE_SPALTEN)
    spieler = zeilen[0][n:]
    spiele = []
    for zeile in zeilen[1:]:
        spiel = dict(zip(SPIELE_SPALTEN, zeile[:n]))
        spiel["spiel"] = int(spiel["spiel"])
        spiel["laufende"] = int(spiel["laufende"] or 0)
        spiel["punkte"] = {s: int(p) for s, p in zip(spieler, zeile[n:])}
        spiele.append(spiel)
    return Tischrunde(runde, tisch, spieler, spiele)
