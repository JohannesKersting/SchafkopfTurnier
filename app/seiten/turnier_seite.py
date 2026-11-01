"""Hauptseite für den Bildschirm: Rangliste, Punkteverlauf und Tischübersicht, aktualisiert sich selbst."""

import os
from urllib.parse import quote

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback

import auswertung
import qr
from turnier import Turnier

AKTUALISIERUNG_MS = 5000


def layout(turnier: Turnier):
    return dbc.Container([
        html.H1(turnier.name, className="my-3"),
        dcc.Store(id="turnier-name", data=turnier.name),
        dcc.Interval(id="turnier-intervall", interval=AKTUALISIERUNG_MS),
        dbc.Tabs([
            dbc.Tab(html.Div(id="turnier-rangliste", className="mt-3"), label="Rangliste", tab_id="rangliste"),
            dbc.Tab(html.Div([
                dbc.RadioItems(id="turnier-verlauf_runde", inline=True, value=1, className="mt-3",
                               options=[{"label": f"Runde {r}", "value": r}
                                        for r in range(1, turnier.runden + 1)]),
                dcc.Graph(id="turnier-verlauf", style={"height": "75vh"}),
            ]), label="Verlauf", tab_id="verlauf"),
            dbc.Tab(html.Div([
                dbc.Switch(id="turnier-qr_anzeigen", label="QR-Codes anzeigen", value=False, className="mt-3"),
                html.Div(id="turnier-tische"),
            ]), label="Tische", tab_id="tische"),
        ], id="turnier-tabs", active_tab="rangliste", persistence=True),
    ], fluid=True)


def plus(zahl: int) -> str:
    return f"{zahl:+d}"


def gew_verl(eintrag: dict, schluessel: str) -> str:
    return f"{eintrag[schluessel + '_gewonnen']} / {eintrag[schluessel + '_verloren']}"


def rangliste_tabelle(turnier: Turnier):
    eintraege = auswertung.rangliste(turnier)
    if not eintraege:
        return html.P("Noch keine Tische angelegt.", className="text-muted")
    runden = range(1, turnier.runden + 1)
    kopf = html.Thead(html.Tr(
        [html.Th("Rang"), html.Th("Name")] + [html.Th(f"Runde {r}") for r in runden] +
        [html.Th("Gesamt"), html.Th("♥ Herzsoli"), html.Th("Sauspiele"), html.Th("Solo eigen"), html.Th("Solo fremd"),
         html.Th("Wenz eigen"), html.Th("Wenz fremd")]
    ))
    zeilen = [html.Tr(
        [html.Td(e["rang"]), html.Td(e["name"])] +
        [html.Td(plus(e["runden"][r]) if r in e["runden"] else "") for r in runden] +
        [html.Td(html.Strong(plus(e["gesamt"]))), html.Td(e["herzsoli"]),
         html.Td(gew_verl(e, "sauspiel")), html.Td(gew_verl(e, "solo_eigen")), html.Td(gew_verl(e, "solo_fremd")),
         html.Td(gew_verl(e, "wenz_eigen")), html.Td(gew_verl(e, "wenz_fremd"))]
    ) for e in eintraege]
    return html.Div([
        dbc.Table([kopf, html.Tbody(zeilen)], striped=True, hover=True, size="sm", className="text-nowrap"),
        html.Small("Spiele: gewonnen / verloren. Eigen: selbst gespielt, fremd: als Gegenspieler. "
                   "Bei Punktgleichstand entscheiden die Herzsoli.", className="text-muted"),
    ], className="table-responsive")


def verlauf_grafik(turnier: Turnier, runde: int):
    fig = go.Figure()
    for name, punkte in sorted(auswertung.verlauf(turnier, runde).items()):
        fig.add_trace(go.Scatter(x=list(range(len(punkte))), y=punkte, mode="lines", name=name))
    fig.update_layout(
        xaxis_title="Spiel", yaxis_title="Punkte", xaxis_range=[0, turnier.spiele_pro_runde],
        xaxis_dtick=max(1, turnier.spiele_pro_runde // 16),
        margin=dict(l=40, r=20, t=20, b=40), template="plotly_white",
        uirevision=runde,  # Zoom und ausgeblendete Linien bleiben bei Aktualisierung erhalten
    )
    return fig


def qr_uebersicht(turnier: Turnier):
    """Die QR-Codes gelten für alle Runden, daher nur ein Abschnitt."""
    karten = []
    for tisch in turnier.tische:
        pfad = os.path.join(turnier.pfad, qr.QR_ORDNER, qr.qr_dateiname(tisch))
        if os.path.exists(pfad):
            # Änderungszeit als Parameter, damit neu erzeugte Codes nicht aus dem Browser-Cache kommen
            src = f"/_qr/{quote(turnier.name)}/{quote(qr.qr_dateiname(tisch))}?v={os.stat(pfad).st_mtime_ns}"
            inhalt = html.Img(src=src, className="img-fluid")
        else:
            inhalt = [html.H5(tisch), html.P("QR-Code fehlt, bitte im Admin erzeugen.", className="text-muted")]
        # Das PNG enthält den Tischnamen schon
        karten.append(dbc.Col(dbc.Card(dbc.CardBody(inhalt), className="text-center"),
                              xs=12, sm=6, lg=4, xl=3, className="mb-3"))
    return dbc.Row(karten)


def tisch_uebersicht(turnier: Turnier):
    abschnitte = []
    for runde in range(1, turnier.runden + 1):
        karten = []
        for tisch in turnier.tische:
            tr = turnier.tischrunde(runde, tisch)
            if tr:
                stand = tr.punkte_verlauf(turnier.startpunkte)[-1]
                fortschritt = ("beendet" if turnier.runde_beendet(tr)
                               else f"Spiel {tr.naechstes_spiel} / {turnier.spiele_pro_runde}")
                zeilen = [html.Li([html.Span(n), html.Strong(stand[n])],
                                  className="d-flex justify-content-between") for n in tr.spieler]
            else:
                fortschritt = "nicht angelegt"
                zeilen = [html.Li(" ") for _ in range(4)]
            karten.append(dbc.Col(dbc.Card(dbc.CardBody([
                html.H5(html.A(tisch, href=f"/{quote(turnier.name)}/{quote(tisch)}",
                               className="text-reset text-decoration-none"), className="card-title mb-0"),
                html.Small(fortschritt, className="text-muted"),
                html.Ul(zeilen, className="list-unstyled mb-0 mt-2"),
            ])), xs=12, sm=6, lg=4, xl=3, className="mb-3"))
        abschnitte += [html.H3(f"Runde {runde}", className="h5"), dbc.Row(karten)]
    return abschnitte


@callback(
    Output("turnier-rangliste", "children"),
    Output("turnier-verlauf", "figure"),
    Output("turnier-tische", "children"),
    Input("turnier-intervall", "n_intervals"),
    Input("turnier-verlauf_runde", "value"),
    Input("turnier-qr_anzeigen", "value"),
    State("turnier-name", "data"),
)
def aktualisieren(_, runde, qr_anzeigen, name):
    turnier = Turnier.laden(name)
    tische = qr_uebersicht(turnier) if qr_anzeigen else tisch_uebersicht(turnier)
    return rangliste_tabelle(turnier), verlauf_grafik(turnier, runde), tische
