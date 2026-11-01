"""Tischansicht fürs Handy: Spieler zuordnen, Spiele eintragen.

Alle Buttons haben die ID {"type": "tisch-btn", "aktion": ..., "wert": ...} und landen in einem
Callback, der den UI-Zustand (dcc.Store) bzw. die Dateien ändert und die Ansicht neu aufbaut."""

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback, clientside_callback, ctx
from dash.exceptions import PreventUpdate

import wertung
from seiten import deko
from turnier import Turnier, TurnierFehler

# Sitzplätze im Uhrzeigersinn ab oben links, in der Reihenfolge des 2x2-Rasters (Zeile für Zeile).
RASTER_REIHENFOLGE = [0, 1, 3, 2]


def layout(turnier: Turnier, tisch: str):
    if tisch not in turnier.tische:
        return dbc.Container(dbc.Alert(f"Tisch '{tisch}' gibt es in {turnier.name} nicht.", color="danger"))
    ui = {"turnier": turnier.name, "tisch": tisch}
    inhalt = ansicht(turnier, ui)
    return dbc.Container([
        deko.titel(f"Tisch {tisch}", turnier.name),
        dcc.Store(id="tisch-ui", data=ui),
        html.Div(id="tisch-inhalt", children=inhalt),
    ], className="tisch-seite")


def btn(label, aktion, wert="", **kwargs):
    return dbc.Button(label, id={"type": "tisch-btn", "aktion": aktion, "wert": wert}, **kwargs)


def raster(kacheln: list):
    return html.Div([kacheln[i] for i in RASTER_REIHENFOLGE], className="kachel-raster")


def ecken(sitz: int):
    """Farbsymbol des Sitzplatzes in zwei Ecken, wie auf einer Spielkarte."""
    farbe = deko.farbe(sitz)
    return [deko.farb_icon(farbe, "ecke ecke-oben"), deko.farb_icon(farbe, "ecke ecke-unten")]


def kachel(inhalt, sitz: int, ausgewaehlt=False, **kwargs):
    return html.Div(ecken(sitz) + inhalt, className="kachel" + (" ausgewaehlt" if ausgewaehlt else ""), **kwargs)


# --- Ansichten ---

def ansicht(turnier: Turnier, ui: dict, meldung=None, farbe="danger"):
    """Baut die Ansicht aus Dateien + UI-Zustand. Merkt sich in `ui`, welchen Stand der Benutzer sieht."""
    tisch = ui["tisch"]
    runde = turnier.aktuelle_runde(tisch)
    tr = turnier.tischrunde(runde, tisch) if runde else None
    ui["runde"] = runde
    ui["gesehen"] = len(tr.spiele) if tr else 0

    # Schwebt unten über dem Inhalt, damit nichts verrutscht. Fehler bleiben, bis man sie wegklickt.
    teile = [dbc.Alert(meldung, color=farbe, dismissable=True, className="py-2 meldung",
                       duration=None if farbe == "danger" else 2500)] if meldung else []
    if not tr or ui.get("setup_runde"):
        teile += setup_ansicht(turnier, ui.get("setup_runde") or 1, zurueck=bool(tr))
    elif turnier.runde_beendet(tr):
        teile += ende_ansicht(turnier, tr, ui)
    else:
        teile += spiel_ansicht(turnier, tr, ui)
    return teile


def freie_spieler(turnier: Turnier, runde: int) -> list[str]:
    belegt = turnier.sitzende_spieler(runde)
    return [s for s in turnier.spieler if s not in belegt]


def setup_ansicht(turnier: Turnier, runde: int, zurueck: bool):
    frei = freie_spieler(turnier, runde)
    sitze = [
        kachel([
            html.Div(f"Platz {i + 1}" + (" · gibt zuerst" if i == 0 else ""), className="small text-muted"),
            dcc.Dropdown(id={"type": "tisch-sitz", "index": i}, options=frei, searchable=True,
                         placeholder="Wählen…", className="text-start"),
        ], sitz=i)
        for i in range(4)
    ]
    return [
        html.P(f"Runde {runde}: Wer sitzt am Tisch?", className="text-center fw-bold"),
        html.P("Plätze im Uhrzeigersinn, oben links beginnt.", className="text-center small text-muted"),
        dcc.Store(id="tisch-frei", data=frei),
        raster(sitze),
        html.Div([
            btn("Tisch starten", "anlegen", runde, color="primary", size="lg", className="w-100"),
            btn("Zurück", "zurueck", color="secondary", outline=True, className="w-100 mt-2") if zurueck else None,
        ], className="mt-3"),
    ]


def punkte_kacheln(turnier: Turnier, tr, ui: dict, klickbar: bool, geber: str | None):
    stand = tr.punkte_verlauf(turnier.startpunkte)[-1]
    auswahl = ui.get("auswahl", [])
    kacheln = []
    for sitz, name in enumerate(tr.spieler):
        inhalt = [
            html.Div(name, className="kachel-name"),
            html.Div(stand[name], className="kachel-punkte " + deko.wert_klasse(stand[name] - turnier.startpunkte)),
            html.Div("Geber", className="badge badge-geber" + ("" if name == geber else " invisible")),
        ]
        if klickbar:
            kacheln.append(html.Button(ecken(sitz) + inhalt, id={"type": "tisch-btn", "aktion": "kachel", "wert": name},
                                       className="kachel" + (" ausgewaehlt" if name in auswahl else "")))
        else:
            kacheln.append(kachel(inhalt, sitz, ausgewaehlt=name in auswahl))
    return raster(kacheln)


def spiel_ansicht(turnier: Turnier, tr, ui: dict):
    phase = ui.get("phase", "start")
    auswahl = ui.get("auswahl", [])
    teile = [
        html.P([f"Runde {tr.runde} · ", html.Strong(f"Spiel {tr.naechstes_spiel}"),
                f" von {turnier.spiele_pro_runde}"], className="text-center"),
    ]
    # Während der Eingabe ersetzt sie die Kacheln, damit man nicht scrollen muss.
    if phase in ("start", "frage"):
        teile.append(punkte_kacheln(turnier, tr, ui, klickbar=phase == "start",
                                    geber=wertung.geber(tr.spieler, tr.naechstes_spiel)))

    if phase == "start":
        hinweis = "Gewinner antippen" if not auswahl else f"{len(auswahl)} Gewinner gewählt"
        teile.append(html.Div([
            html.P(hinweis, className="text-center text-muted small my-2"),
            btn("Punkte eintragen", "eintragen", color="primary", size="lg", className="w-100",
                disabled=not wertung.moegliche_spielarten(len(auswahl))),
            btn("Zusammengeworfen", "frage", "zusammengeworfen", color="secondary", outline=True,
                className="w-100 mt-2") if turnier.zusammenwerfen_erlaubt else None,
            btn("Letztes Spiel rückgängig", "frage", "rueckgaengig", color="link", size="sm",
                className="w-100 mt-3 text-muted") if tr.spiele else None,
        ]))
    elif phase == "frage":
        teile += frage(ui["frage"], tr)
    elif phase == "soloart":
        teile.append(html.Div([
            html.P("Solo oder Wenz?", className="text-center fw-bold mt-3"),
            html.Div([btn(art, "spielart", art, color="primary", size="lg", className="flex-fill")
                      for art in wertung.moegliche_spielarten(len(auswahl))], className="d-flex gap-2"),
            btn("Abbrechen", "abbrechen", color="secondary", outline=True, className="w-100 mt-2"),
        ]))
    elif phase == "eingabe":
        teile += eingabe(turnier, tr, ui)
    return teile


def frage(art: str, tr):
    text = {
        "rueckgaengig": f"Spiel {len(tr.spiele)} wirklich löschen?",
        "zusammengeworfen": f"Spiel {tr.naechstes_spiel} als zusammengeworfen eintragen?",
    }[art]
    return [html.Div([
        html.P(text, className="text-center fw-bold mt-3"),
        html.Div([
            btn("Ja", art, color="danger" if art == "rueckgaengig" else "primary", className="flex-fill"),
            btn("Nein", "abbrechen", color="secondary", outline=True, className="flex-fill"),
        ], className="d-flex gap-2"),
    ])]


def auswahl_knoepfe(optionen: list[tuple[str, object]], aktiv, aktion: str):
    return html.Div([
        btn(label, aktion, wert, color="primary", outline=wert != aktiv, className="py-2 px-1")
        for label, wert in optionen
    ], className="auswahl-raster mb-2")


def eingabe(turnier: Turnier, tr, ui: dict):
    spielart = ui["spielart"]
    tarife = turnier.tarife
    stufe, laufende = ui.get("stufe", wertung.STUFEN[0]), ui.get("laufende", 0)
    basis = tarife["sauspiel"] if spielart == wertung.SAUSPIEL else tarife["solo"]

    stufen = [(f"{s} {basis + i * tarife['schneider']}", s) for i, s in enumerate(wertung.STUFEN)]
    laeufer = [("Keine" if n == 0 else f"{n} (+{n * tarife['laufende']})", n)
               for n in wertung.laufende_optionen(spielart)]

    aenderung = wertung.punkte_aenderungen(tarife, tr.spieler, ui["auswahl"], spielart, stufe, laufende)
    stand = tr.punkte_verlauf(turnier.startpunkte)[-1]
    titel = spielart
    if spielart != wertung.SAUSPIEL:
        solist = wertung.solospieler(tr.spieler, ui["auswahl"])
        titel += f" von {solist}, " + ("gewonnen" if solist in ui["auswahl"] else "verloren")

    return [html.Div([
        html.P(titel, className="text-center fw-bold mt-3"),
        auswahl_knoepfe(stufen, stufe, "stufe"),
        html.Div("Laufende", className="small text-muted"),
        auswahl_knoepfe(laeufer, laufende, "laufende"),
        btn([deko.farb_icon("herz"), "Herzsolo"], "herzsolo", color="herzsolo",
            className="w-100 mb-2" + (" aktiv" if ui.get("herzsolo") else "")) if spielart == wertung.SOLO else None,
        dbc.ListGroup([
            dbc.ListGroupItem([
                html.Span(name),
                html.Span([html.Strong(deko.wert(aenderung[name])), f" → {stand[name] + aenderung[name]}"]),
            ], className="d-flex justify-content-between py-1")
            for name in tr.spieler
        ], className="my-2"),
        html.Div([
            btn("Abbrechen", "abbrechen", color="secondary", outline=True, className="flex-fill"),
            btn("Bestätigen", "bestaetigen", color="success", size="lg", className="flex-fill"),
        ], className="d-flex gap-2"),
    ])]


def ende_ansicht(turnier: Turnier, tr, ui: dict):
    letzte = tr.runde >= turnier.runden
    return [
        html.P(f"Runde {tr.runde} beendet", className="text-center fw-bold"),
        punkte_kacheln(turnier, tr, ui, klickbar=False, geber=None),
        html.Div([
            html.P("Turnier beendet. Danke fürs Spielen!", className="text-center mt-3") if letzte else
            btn(f"Runde {tr.runde + 1} starten", "naechste_runde", tr.runde + 1, color="primary", size="lg",
                className="w-100 mt-3"),
            btn("Letztes Spiel rückgängig", "frage", "rueckgaengig", color="link", size="sm",
                className="w-100 mt-3 text-muted"),
        ]) if ui.get("phase") != "frage" else html.Div(frage(ui["frage"], tr)),
    ]


# --- Callbacks ---

def zuruecksetzen(ui: dict) -> dict:
    return {k: ui[k] for k in ("turnier", "tisch", "runde", "gesehen") if k in ui}


@callback(
    Output("tisch-inhalt", "children"),
    Output("tisch-ui", "data"),
    Input({"type": "tisch-btn", "aktion": ALL, "wert": ALL}, "n_clicks"),
    State({"type": "tisch-sitz", "index": ALL}, "value"),
    State("tisch-ui", "data"),
    prevent_initial_call=True,
)
def aktion(_, sitze, ui):
    # Der Callback feuert auch, wenn neue Buttons gerendert werden; dann ist nichts geklickt.
    if not any(t["value"] for t in ctx.triggered):
        raise PreventUpdate
    aktion, wert = ctx.triggered_id["aktion"], ctx.triggered_id["wert"]
    turnier = Turnier.laden(ui["turnier"])
    meldung, farbe = None, "danger"

    try:
        if aktion in ("bestaetigen", "zusammengeworfen", "rueckgaengig"):
            tr = aktuellen_stand_pruefen(turnier, ui)
            if aktion == "rueckgaengig":
                turnier.letztes_spiel_entfernen(tr)
                meldung, farbe = f"Spiel {len(tr.spiele)} gelöscht.", "warning"
            elif aktion == "zusammengeworfen":
                turnier.spiel_eintragen(tr, [], wertung.ZUSAMMENGEWORFEN)
                meldung, farbe = f"Spiel {tr.naechstes_spiel} zusammengeworfen.", "success"
            else:
                turnier.spiel_eintragen(tr, ui["auswahl"], ui["spielart"], ui.get("stufe", wertung.STUFEN[0]),
                                        ui.get("laufende", 0), ui.get("herzsolo", False))
                meldung, farbe = f"Spiel {tr.naechstes_spiel} eingetragen.", "success"
            ui = zuruecksetzen(ui)
        elif aktion == "anlegen":
            # ALL liefert die Dropdowns in DOM-Reihenfolge (Raster), nicht in Sitzreihenfolge.
            sitze = [s["value"] for s in sorted(ctx.states_list[0], key=lambda s: s["id"]["index"])]
            turnier.tisch_anlegen(wert, ui["tisch"], sitze)
            ui = zuruecksetzen(ui)
        elif aktion == "kachel":
            auswahl = ui.get("auswahl", [])
            ui["auswahl"] = [n for n in auswahl if n != wert] if wert in auswahl else auswahl + [wert]
        elif aktion == "eintragen":
            arten = wertung.moegliche_spielarten(len(ui.get("auswahl", [])))
            if len(arten) == 1:
                ui.update(phase="eingabe", spielart=arten[0])
            elif arten:
                ui["phase"] = "soloart"
        elif aktion == "spielart":
            ui.update(phase="eingabe", spielart=wert, stufe=wertung.STUFEN[0], laufende=0, herzsolo=False)
        elif aktion in ("stufe", "laufende"):
            ui[aktion] = wert
        elif aktion == "herzsolo":
            ui["herzsolo"] = not ui.get("herzsolo")
        elif aktion == "frage":
            ui.update(phase="frage", frage=wert)
        elif aktion == "abbrechen":
            ui["phase"] = "start"
        elif aktion == "naechste_runde":
            ui = {**zuruecksetzen(ui), "setup_runde": wert}
        elif aktion == "zurueck":
            ui = zuruecksetzen(ui)
    except TurnierFehler as e:
        meldung, ui = str(e), zuruecksetzen(ui)

    return ansicht(turnier, ui, meldung, farbe), ui


def aktuellen_stand_pruefen(turnier: Turnier, ui: dict):
    """Verhindert, dass ein doppelt abgeschicktes oder veraltetes Formular etwas einträgt."""
    tr = turnier.tischrunde(ui["runde"], ui["tisch"])
    if not tr or turnier.aktuelle_runde(ui["tisch"]) != ui["runde"] or len(tr.spiele) != ui["gesehen"]:
        raise TurnierFehler("Der Tisch wurde inzwischen verändert. Die Ansicht ist jetzt aktualisiert.")
    return tr


# Ein Spieler, der auf einem Platz gewählt ist, verschwindet aus den anderen Dropdowns. Läuft im Browser,
# damit eine verspätete Server-Antwort nicht ein gerade geöffnetes Dropdown zurücksetzt.
clientside_callback(
    """function(werte, frei) {
        return werte.map(eigener => frei.filter(s => s === eigener || !werte.includes(s)));
    }""",
    Output({"type": "tisch-sitz", "index": ALL}, "options"),
    Input({"type": "tisch-sitz", "index": ALL}, "value"),
    State("tisch-frei", "data"),
    prevent_initial_call=True,
)
