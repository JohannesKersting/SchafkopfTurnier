from urllib.parse import quote

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback, ctx, no_update

import qr
import turnier as t
from turnier import Turnier, TurnierFehler

STANDARD_TISCHE = ["Ober", "Unter", "Sau", "König", "10", "9", "8", "7"]


def naechster_tischname(vorhandene: list[str]) -> str:
    for name in STANDARD_TISCHE:
        if name not in vorhandene:
            return name
    i = len(vorhandene) + 1
    while f"Tisch {i}" in vorhandene:
        i += 1
    return f"Tisch {i}"


def layout():
    return dbc.Container([
        html.H1("Admin", className="my-3"),
        dbc.Row([
            dbc.Col(turnier_liste(), md=5, className="mb-4"),
            dbc.Col(turnier_formular(), md=7),
        ]),
    ], fluid=True)


# --- Turnierliste ---

def turnier_liste():
    return html.Div([
        html.H2("Turniere"),
        dbc.Label("Basis-URL für QR-Codes"),
        dbc.Input(id="admin-basis_url", value=qr.lokale_basis_url()),
        dbc.FormText("Wird in neue QR-Codes geschrieben. Muss die Adresse dieses Rechners im Turnier-WLAN sein."),
        html.Div(id="admin-turnier_liste", className="my-3", children=turnier_eintraege()),
        dbc.Button("Cache leeren", id="admin-cache_leeren", color="secondary", outline=True, size="sm"),
        dbc.Alert(id="admin-meldung", is_open=False, dismissable=True, className="mt-3"),
    ])


def turnier_eintraege():
    namen = t.turnier_liste()
    if not namen:
        return html.P("Noch keine Turniere.", className="text-muted")
    eintraege = []
    for name in namen:
        turnier = Turnier.laden(name)
        eintraege.append(dbc.ListGroupItem([
            html.Div(dcc.Link(html.Strong(name), href=f"/{quote(name)}")),
            html.Small(str(turnier), className="text-muted d-block"),
            html.Div([html.A(tisch, href=f"/{quote(name)}/{quote(tisch)}", className="me-2")
                      for tisch in turnier.tische], className="small"),
            html.Div([
                dbc.Button("QR-Codes neu erzeugen", id={"type": "admin-qr", "turnier": name},
                           size="sm", color="secondary", outline=True, className="me-2 mt-2"),
                html.A("QR-Codes drucken", href=f"/_qr/{quote(name)}/alle.html", target="_blank",
                       className="small"),
            ]),
        ]))
    return dbc.ListGroup(eintraege)


@callback(
    Output("admin-meldung", "children", allow_duplicate=True),
    Output("admin-meldung", "color", allow_duplicate=True),
    Output("admin-meldung", "is_open", allow_duplicate=True),
    Input({"type": "admin-qr", "turnier": ALL}, "n_clicks"),
    State("admin-basis_url", "value"),
    prevent_initial_call=True,
)
def qr_neu_erzeugen(klicks, basis_url):
    if not any(klicks):
        return no_update, no_update, no_update
    turnier = Turnier.laden(ctx.triggered_id["turnier"])
    turnier.basis_url = (basis_url or "").strip()
    turnier.speichern()
    ordner = qr.qr_codes_erzeugen(turnier)
    return f"QR-Codes für {turnier.basis_url} erzeugt in {ordner}", "success", True


@callback(
    Output("admin-meldung", "children", allow_duplicate=True),
    Output("admin-meldung", "color", allow_duplicate=True),
    Output("admin-meldung", "is_open", allow_duplicate=True),
    Input("admin-cache_leeren", "n_clicks"),
    prevent_initial_call=True,
)
def cache_leeren(_):
    t.cache_leeren()
    return "Cache geleert, alle Dateien werden neu gelesen.", "info", True


# --- Neues Turnier ---

def zahl(label, id_, wert, minimum=1, maximum=None):
    return dbc.Col([
        dbc.Label(label, html_for=id_),
        dbc.Input(id=id_, type="number", min=minimum, max=maximum, step=1, value=wert, required=True),
    ], xs=6, md=3, className="mb-3")


def turnier_formular():
    return html.Div([
        html.H2("Neues Turnier erstellen"),
        dbc.Label("Turniername", html_for="admin-name"),
        dbc.Input(id="admin-name", className="mb-3"),
        dbc.Row([
            zahl("Runden", "admin-runden", 2, maximum=10),
            zahl("Spiele pro Runde", "admin-spiele", 32, maximum=200),
            zahl("Startpunkte", "admin-startpunkte", 100, minimum=0),
        ]),
        dbc.Row([
            zahl("Sauspiel", "admin-tarif_sauspiel", t.STANDARD_TARIFE["sauspiel"]),
            zahl("Solo / Wenz", "admin-tarif_solo", t.STANDARD_TARIFE["solo"]),
            zahl("Schneider-Stufe", "admin-tarif_schneider", t.STANDARD_TARIFE["schneider"], minimum=0),
            zahl("Pro Laufendem", "admin-tarif_laufende", t.STANDARD_TARIFE["laufende"], minimum=0),
        ]),
        dbc.Checkbox(id="admin-zusammenwerfen", label="Zusammenwerfen erlaubt", value=False, className="mb-3"),
        dbc.Label("Tische"),
        html.Div(id="admin-tische", children=tisch_felder(STANDARD_TISCHE[:4])),
        dbc.Button("+ Tisch", id="admin-tisch_hinzu", size="sm", color="secondary", outline=True,
                   className="mb-3"),
        html.Br(),
        dbc.Label("Spieler (ein Name pro Zeile)", html_for="admin-spieler"),
        dbc.Textarea(id="admin-spieler", rows=10, placeholder="Markus\nHeinz\n..."),
        dbc.FormText(id="admin-spieler_info"),
        html.Br(),
        dbc.Button("Turnier erstellen", id="admin-erstellen", color="primary", className="my-3"),
        dbc.Alert(id="admin-ergebnis", is_open=False),
    ])


def tisch_felder(namen: list[str]):
    return [
        dbc.InputGroup([
            dbc.Input(id={"type": "admin-tisch", "index": i}, value=name),
            dbc.Button("×", id={"type": "admin-tisch_weg", "index": i}, color="secondary", outline=True),
        ], size="sm", className="mb-1", style={"maxWidth": "20rem"})
        for i, name in enumerate(namen)
    ]


@callback(
    Output("admin-tische", "children"),
    Input("admin-tisch_hinzu", "n_clicks"),
    Input({"type": "admin-tisch_weg", "index": ALL}, "n_clicks"),
    State({"type": "admin-tisch", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def tische_aendern(_, weg_klicks, namen):
    namen = [n or "" for n in namen]
    if ctx.triggered_id == "admin-tisch_hinzu":
        namen.append(naechster_tischname(namen))
    elif any(weg_klicks):
        namen.pop(ctx.triggered_id["index"])
    else:
        return no_update
    return tisch_felder(namen)


def zeilen(text: str | None) -> list[str]:
    return [z.strip() for z in (text or "").splitlines() if z.strip()]


def liste_fehler(namen: list[str], art: str, minimum: int) -> str | None:
    if len(namen) < minimum:
        return f"Es braucht mindestens {minimum} {art}."
    if len(namen) != len(set(namen)):
        return f"{art} dürfen nicht doppelt vorkommen."
    for name in namen:
        if fehler := t.name_fehler(name, art):
            return fehler
    return None


@callback(
    Output("admin-spieler_info", "children"),
    Input("admin-spieler", "value"),
    Input({"type": "admin-tisch", "index": ALL}, "value"),
)
def spieler_info(spieler, tische):
    anzahl = len(zeilen(spieler))
    plaetze = 4 * len([n for n in tische if n and n.strip()])
    info = f"{anzahl} Spieler, {plaetze} Plätze an den Tischen."
    if anzahl > plaetze:
        info += f" {anzahl - plaetze} Spieler bleiben ohne Tisch."
    return info


@callback(
    Output("admin-ergebnis", "children"),
    Output("admin-ergebnis", "color"),
    Output("admin-ergebnis", "is_open"),
    Output("admin-turnier_liste", "children"),
    Input("admin-erstellen", "n_clicks"),
    State("admin-name", "value"),
    State("admin-runden", "value"),
    State("admin-spiele", "value"),
    State("admin-startpunkte", "value"),
    State("admin-tarif_sauspiel", "value"),
    State("admin-tarif_solo", "value"),
    State("admin-tarif_schneider", "value"),
    State("admin-tarif_laufende", "value"),
    State("admin-zusammenwerfen", "value"),
    State({"type": "admin-tisch", "index": ALL}, "value"),
    State("admin-spieler", "value"),
    State("admin-basis_url", "value"),
    prevent_initial_call=True,
)
def erstellen(_, name, runden, spiele, startpunkte, sauspiel, solo, schneider, laufende, zusammenwerfen,
              tische, spieler, basis_url):
    zahlen = [runden, spiele, startpunkte, sauspiel, solo, schneider, laufende]
    tische = [(n or "").strip() for n in tische]
    spieler = zeilen(spieler)
    fehler = (
        ("Bitte alle Zahlenfelder ausfüllen." if any(z is None for z in zahlen) else None)
        or liste_fehler(tische, "Tische", 1)
        or liste_fehler(spieler, "Spieler", 4)
    )
    if fehler:
        return fehler, "danger", True, no_update

    turnier = Turnier(
        name=(name or "").strip(), runden=runden, spiele_pro_runde=spiele, startpunkte=startpunkte,
        tische=tische, spieler=spieler,
        tarife={"sauspiel": sauspiel, "solo": solo, "schneider": schneider, "laufende": laufende},
        zusammenwerfen_erlaubt=bool(zusammenwerfen), basis_url=(basis_url or "").strip(),
    )
    try:
        turnier.erstellen()
    except TurnierFehler as e:
        return str(e), "danger", True, no_update
    qr.qr_codes_erzeugen(turnier)
    return f"Turnier erstellt: {turnier}", "success", True, turnier_eintraege()
