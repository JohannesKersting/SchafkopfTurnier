"""Highlights für die Hauptseite: besondere Spiele, Spieler und Tische. Kein Dash, kein Datei-IO.

Jede Karte ist ein Dict {titel, erklaerung, farbe, eintraege, vorzeichen, einheit}, jeder Eintrag
{name, wert, detail}. Teilen sich mehr als MAX_EINTRAEGE den Bestwert, entfällt die Karte."""

from collections import Counter, defaultdict
from itertools import combinations

import wertung
from turnier import Turnier

MAX_EINTRAEGE = 3
SAUSPIEL_PROFI_MINDESTENS = 8
SOLI = (wertung.SOLO, wertung.WENZ)
SCHNEIDER_ODER_SCHWARZ = ("Schneider", "Schwarz")

# Farbsymbol je Karte, fest statt reihum, damit gleiche Symbole nicht untereinander stehen
# und eine Karte ihr Symbol behält, wenn andere Karten auftauchen oder verschwinden.
FARBEN = {
    "Ein Spiel und ausgesorgt!": "schellen", "Das war teuer": "schellen", "Solist": "gras",
    "Alle Unter!": "eichel", "Geht auch alleine": "herz", "„Muas ma spuin“": "gras",
    "„Spui ruhig dei Solo!“": "eichel", "Läuft bei dir!": "eichel", "Koa Risiko!": "herz",
    "Kleinvieh macht auch Mist!": "gras", "Comeback": "herz", "Nächstes Mal ein Bier weniger…": "schellen",
    "A Herz hot a jeder": "herz", "On fire": "eichel", "Pechsträhne": "gras", "Dynamisches Duo": "herz",
    "Erzfeind": "eichel", "A bisserl was geht immer": "gras", "Keine Chance": "schellen",
    "Warum spiel ich eigentlich mit?": "herz", "Achterbahn": "eichel", "Schwarz gspuit!": "gras", "Tout gspuit!": "herz",
    "Zu hoch gepokert": "schellen", "Des kimmt an d'Wand!": "eichel",
    "Sauspiel-Profi": "schellen", "Haifischbecken": "eichel", "Kaffeekränzchen": "herz", "Wilde Runde": "gras",
}


def waehle(werte: dict, groesste: bool = True) -> list | None:
    """Schlüssel mit dem besten Wert. Beim Maximum zählen nur Werte > 0.
    Keine Kandidaten oder mehr als MAX_EINTRAEGE Gleichstände -> None."""
    if groesste:
        werte = {k: w for k, w in werte.items() if w > 0}
    if not werte:
        return None
    bester = (max if groesste else min)(werte.values())
    sieger = [k for k, w in werte.items() if w == bester]
    return sieger if len(sieger) <= MAX_EINTRAEGE else None


def laengste_serie(deltas: list[int], gewonnen: bool) -> int:
    laengste = aktuell = 0
    for d in deltas:
        aktuell = aktuell + 1 if (d > 0) == gewonnen else 0
        laengste = max(laengste, aktuell)
    return laengste


def zahlungen(delta: dict[str, int]) -> dict[tuple[str, str], float]:
    """Wer zahlt wem wie viel in einem Spiel. Jeder Verlierer verteilt seinen Verlust anteilig auf die
    Gewinner: beim Sauspiel je die Hälfte, beim Solo zahlt bzw. bekommt der Solist von jedem den Spielwert."""
    gewinn = {s: d for s, d in delta.items() if d > 0}
    summe = sum(gewinn.values())
    return {(verlierer, gewinner): -d * g / summe
            for verlierer, d in delta.items() if d < 0 for gewinner, g in gewinn.items()}


def _spiel_detail(spiel: dict) -> str:
    return f"Runde {spiel['runde']} · {spiel['tisch']} · Spiel {spiel['nr']}"


def _karte(titel: str, erklaerung: str, sieger: list | None, eintrag, vorzeichen: bool = False,
           einheit: str = "") -> dict | None:
    if not sieger:
        return None
    return {"titel": titel, "erklaerung": erklaerung, "farbe": FARBEN.get(titel, "eichel"), "eintraege": [eintrag(k) for k in sieger],
            "vorzeichen": vorzeichen, "einheit": einheit}


def turnier_beendet(turnier: Turnier, tischrunden: list) -> bool:
    """Alle angelegten Tische sind fertig und jeder Spieler hat alle Runden gespielt."""
    runden = defaultdict(set)
    for tr in tischrunden:
        if not turnier.runde_beendet(tr):
            return False
        for name in tr.spieler:
            runden[name].add(tr.runde)
    return bool(runden) and all(len(r) == turnier.runden for r in runden.values())


def highlights(turnier: Turnier) -> list[dict]:
    tischrunden = [tr for runde in range(1, turnier.runden + 1) for tisch in turnier.tische
                   if (tr := turnier.tischrunde(runde, tisch))]
    namen = list(dict.fromkeys(name for tr in tischrunden for name in tr.spieler))
    beendet = turnier_beendet(turnier, tischrunden)

    # Alle echten Spiele chronologisch (Runde, dann Spielnummer), Zusammengeworfene zählen nirgends
    spiele = [{"runde": tr.runde, "tisch": tr.tisch, "nr": s["spiel"], "art": s["spielart"], "stufe": s["stufe"],
               "laufende": s["laufende"], "solist": s["spieler"], "herzsolo": s["herzsolo"], "delta": s["punkte"]}
              for tr in sorted(tischrunden, key=lambda tr: tr.runde) for s in tr.spiele
              if s["spielart"] != wertung.ZUSAMMENGEWORFEN]

    def zaehle(bedingung) -> dict[str, int]:
        """Anzahl Spiele je Spieler, für die bedingung(spiel, name, delta) gilt. Alle Spieler mit 0 vorbelegt."""
        zaehler = dict.fromkeys(namen, 0)
        for s in spiele:
            for name, d in s["delta"].items():
                if bedingung(s, name, d):
                    zaehler[name] += 1
        return zaehler

    def spieler_eintrag(werte):
        return lambda name: {"name": name, "wert": werte[name], "detail": ""}

    karten = []

    # --- Einzelne Spiele ---
    einzel = {(name, i): d for i, s in enumerate(spiele) for name, d in s["delta"].items()}

    def einzel_eintrag(schluessel):
        name, i = schluessel
        return {"name": name, "wert": einzel[schluessel], "detail": _spiel_detail(spiele[i])}

    karten.append(_karte("Ein Spiel und ausgesorgt!", "Meiste Punkte in einem einzelnen Spiel gewonnen",
                         waehle(einzel), einzel_eintrag, vorzeichen=True))
    karten.append(_karte("Das war teuer", "Meiste Punkte in einem einzelnen Spiel verloren",
                         waehle({k: d for k, d in einzel.items() if d < 0}, groesste=False), einzel_eintrag,
                         vorzeichen=True))

    # --- Soli ---
    def eigenes(*arten):
        return lambda s, name, d: s["art"] in arten and s["solist"] == name

    for titel, erklaerung, werte in [
        ("Solist", "Meiste Farbsoli gespielt", zaehle(eigenes(wertung.SOLO))),
        ("Alle Unter!", "Meiste Wenzen gespielt", zaehle(eigenes(wertung.WENZ))),
        ("Geht auch alleine", "Meiste Farbsoli und Wenzen gewonnen",
         zaehle(lambda s, name, d: eigenes(*SOLI)(s, name, d) and d > 0)),
        ("„Muas ma spuin“", "Meiste Farbsoli und Wenzen verloren",
         zaehle(lambda s, name, d: eigenes(*SOLI)(s, name, d) and d < 0)),
        ("„Spui ruhig dei Solo!“", "Meiste Farbsoli und Wenzen als Gegenspieler vereitelt",
         zaehle(lambda s, name, d: s["art"] in SOLI and s["solist"] != name and d > 0)),
    ]:
        karten.append(_karte(titel, erklaerung, waehle(werte), spieler_eintrag(werte)))

    laufende_punkte = dict.fromkeys(namen, 0)
    for s in spiele:
        wert = wertung.spielwert(turnier.tarife, s["art"], s["stufe"], s["laufende"])
        for name, d in s["delta"].items():
            if d > 0:  # brutto: nur Laufende aus gewonnenen Spielen
                laufende_punkte[name] += (d // wert * s["laufende"] * turnier.tarife["laufende"]
                                          * wertung.faktor(turnier.tarife, s["stufe"]))
    karten.append(_karte("Läuft bei dir!", "Meiste Punkte allein durch Laufende bekommen",
                         waehle(laufende_punkte), spieler_eintrag(laufende_punkte)))

    if beendet:
        soli = zaehle(eigenes(*SOLI))
        karten.append(_karte("Koa Risiko!", "Wenigste Farbsoli und Wenzen gespielt",
                             waehle(soli, groesste=False), spieler_eintrag(soli)))

    kleinvieh = zaehle(lambda s, name, d: d > 0 and s["art"] == wertung.SAUSPIEL
                       and s["stufe"] == wertung.STUFEN[0] and s["laufende"] == 0)
    karten.append(_karte("Kleinvieh macht auch Mist!", "Meiste Sauspiele ohne Schneider und Laufende gewonnen",
                         waehle(kleinvieh), spieler_eintrag(kleinvieh)))

    # --- Rundenvergleich: nur Runden, die für den Spieler beendet sind ---
    ergebnisse = defaultdict(dict)
    for tr in tischrunden:
        if turnier.runde_beendet(tr):
            endstand = tr.punkte_verlauf(turnier.startpunkte)[-1]
            for name in tr.spieler:
                ergebnisse[name][tr.runde] = endstand[name] - turnier.startpunkte
    sprung = {(name, r): runden[r + 1] - runden[r]
              for name, runden in ergebnisse.items() for r in runden if r + 1 in runden}

    def sprung_eintrag(schluessel):
        name, r = schluessel
        return {"name": name, "wert": sprung[schluessel], "detail": f"Runde {r} → {r + 1}"}

    karten.append(_karte("Comeback", "Größte Verbesserung von einer Runde zur nächsten",
                         waehle(sprung), sprung_eintrag, vorzeichen=True))
    karten.append(_karte("Nächstes Mal ein Bier weniger…", "Größte Verschlechterung von einer Runde zur nächsten",
                         waehle({k: w for k, w in sprung.items() if w < 0}, groesste=False), sprung_eintrag,
                         vorzeichen=True))

    herzsoli = zaehle(lambda s, name, d: s["herzsolo"] == name)
    karten.append(_karte("A Herz hot a jeder", "Meiste Herzsoli gespielt", waehle(herzsoli),
                         spieler_eintrag(herzsoli)))

    # --- Serien, über Rundengrenzen hinweg ---
    deltas = {name: [s["delta"][name] for s in spiele if name in s["delta"]] for name in namen}
    for titel, erklaerung, gewonnen in [("On fire", "Längste Serie gewonnener Spiele", True),
                                        ("Pechsträhne", "Längste Serie verlorener Spiele", False)]:
        serien = {name: laengste_serie(d, gewonnen) for name, d in deltas.items()}
        karten.append(_karte(titel, erklaerung, waehle(serien), spieler_eintrag(serien)))

    # --- Paare ---
    duos = Counter()
    for s in spiele:
        if s["art"] == wertung.SAUSPIEL:
            duos.update(combinations(sorted(n for n, d in s["delta"].items() if d > 0), 2))
    karten.append(_karte("Dynamisches Duo", "Meiste gemeinsam gewonnene Sauspiele", waehle(duos),
                         lambda paar: {"name": " & ".join(paar), "wert": duos[paar], "detail": ""}))

    bezahlt = defaultdict(float)
    for s in spiele:
        for paar, betrag in zahlungen(s["delta"]).items():
            bezahlt[paar] += betrag
    netto = {(a, b): betrag - bezahlt.get((b, a), 0) for (a, b), betrag in bezahlt.items()}
    karten.append(_karte("Erzfeind", "Meiste Punkte unterm Strich an einen einzelnen Spieler verloren",
                         waehle(netto),
                         lambda paar: {"name": f"{paar[0]} → {paar[1]}", "wert": netto[paar], "detail": ""}))

    # --- Schneider ---
    def tout_gewonnen(s):
        return s["stufe"] == wertung.TOUT and s["delta"][s["solist"]] > 0

    geschneidert = zaehle(lambda s, name, d: d < 0 and (s["stufe"] in SCHNEIDER_ODER_SCHWARZ or tout_gewonnen(s)))
    if beendet:
        karten.append(_karte("A bisserl was geht immer", "Am seltensten Schneider oder Schwarz gespielt worden",
                             waehle(geschneidert, groesste=False), spieler_eintrag(geschneidert)))
    karten.append(_karte("Keine Chance", "Am häufigsten Schneider oder Schwarz gespielt worden",
                         waehle(geschneidert), spieler_eintrag(geschneidert)))

    if beendet:
        gesamt = {name: sum(r.values()) for name, r in ergebnisse.items()}
        karten.append(_karte("Warum spiel ich eigentlich mit?", "Endergebnis am nächsten am Startwert",
                             waehle({n: abs(g) for n, g in gesamt.items()}, groesste=False),
                             spieler_eintrag(gesamt), vorzeichen=True))

    # --- Weitere ---
    spannen = {}
    for tr in tischrunden:
        verlauf = tr.punkte_verlauf(turnier.startpunkte)
        for name in tr.spieler:
            werte = [stand[name] for stand in verlauf]
            spannen[(name, tr.runde)] = max(werte) - min(werte)
    karten.append(_karte("Achterbahn", "Größte Spanne zwischen Höchst- und Tiefststand in einer Runde",
                         waehle(spannen),
                         lambda k: {"name": k[0], "wert": spannen[k], "detail": f"Runde {k[1]}"}))

    def schwarz_eintrag(s):
        gewinner = [n for n, d in s["delta"].items() if d > 0]
        art = f"gegen {s['art']}" if s["art"] in SOLI and s["solist"] not in gewinner else s["art"]
        return {"name": " & ".join([", ".join(gewinner[:-1]), gewinner[-1]] if len(gewinner) > 1 else gewinner),
                "wert": art, "detail": _spiel_detail(s)}

    # Ehrenlisten ohne Gleichstands-Grenze: jedes Spiel ist ein eigener Eintrag
    karten.append(_karte("Schwarz gspuit!", "Ein Spiel schwarz gewonnen",
                         [s for s in spiele if s["stufe"] == "Schwarz"], schwarz_eintrag))

    def solist_eintrag(s):
        return {"name": s["solist"], "wert": s["art"], "detail": _spiel_detail(s)}

    touts = [s for s in spiele if s["stufe"] == wertung.TOUT]
    karten.append(_karte("Tout gspuit!", "Ein Tout gewonnen", [s for s in touts if tout_gewonnen(s)],
                         solist_eintrag))
    karten.append(_karte("Zu hoch gepokert", "Ein Tout verloren", [s for s in touts if not tout_gewonnen(s)],
                         solist_eintrag))
    karten.append(_karte("Des kimmt an d'Wand!", "Alle Ober und Unter auf der Hand",
                         [s for s in spiele if s["stufe"] == wertung.SIE],
                         lambda s: {"name": s["solist"], "wert": "", "detail": _spiel_detail(s)}))

    sauspiele = zaehle(lambda s, name, d: s["art"] == wertung.SAUSPIEL)
    sauspiel_siege = zaehle(lambda s, name, d: s["art"] == wertung.SAUSPIEL and d > 0)
    quoten = {n: sauspiel_siege[n] / sauspiele[n] for n in namen if sauspiele[n] >= SAUSPIEL_PROFI_MINDESTENS}
    karten.append(_karte("Sauspiel-Profi",
                         f"Höchste Siegquote im Sauspiel, ab {SAUSPIEL_PROFI_MINDESTENS} Sauspielen",
                         waehle(quoten),
                         lambda n: {"name": n, "wert": round(100 * quoten[n]),
                                    "detail": f"{sauspiel_siege[n]} von {sauspiele[n]} gewonnen"},
                         einheit=" %"))

    # --- Tische ---
    sitzordnung = {(tr.runde, tr.tisch): tr.spieler for tr in tischrunden}

    def tisch_eintrag(werte):
        return lambda k: {"name": f"{k[1]} ({', '.join(sitzordnung[k])})", "wert": werte[k],
                          "detail": f"Runde {k[0]}"}

    umsatz = {(tr.runde, tr.tisch): sum(d for s in tr.spiele for d in s["punkte"].values() if d > 0)
              for tr in tischrunden}
    karten.append(_karte("Haifischbecken", "Tisch, an dem in einer Runde die meisten Punkte den Besitzer wechselten",
                         waehle(umsatz), tisch_eintrag(umsatz)))
    if beendet:
        karten.append(_karte("Kaffeekränzchen",
                             "Tisch, an dem in einer Runde die wenigsten Punkte den Besitzer wechselten",
                             waehle(umsatz, groesste=False), tisch_eintrag(umsatz)))
    wild = {(tr.runde, tr.tisch): sum(s["spielart"] in SOLI for s in tr.spiele) for tr in tischrunden}
    karten.append(_karte("Wilde Runde", "Tisch mit den meisten Farbsoli und Wenzen in einer Runde",
                         waehle(wild), tisch_eintrag(wild)))

    return [k for k in karten if k]
