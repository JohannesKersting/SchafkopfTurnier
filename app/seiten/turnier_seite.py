"""Hauptseite für den Bildschirm: Rangliste, Punkteverlauf und Tischübersicht, aktualisiert sich selbst."""

import os
from urllib.parse import quote

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback

import auswertung
import highlights
import qr
from seiten import deko
from turnier import Turnier

AKTUALISIERUNG_MS = 5000


def layout(turnier: Turnier):
    return dbc.Container([
        deko.titel(turnier.name),
        dcc.Store(id="turnier-name", data=turnier.name),
        dcc.Interval(id="turnier-intervall", interval=AKTUALISIERUNG_MS),
        dbc.Tabs([
            dbc.Tab(html.Div(id="turnier-rangliste", className="mt-3"), label="Rangliste", tab_id="rangliste"),
            dbc.Tab(html.Div([
                dbc.RadioItems(id="turnier-verlauf_runde", inline=True, value=1, className="mt-3",
                               options=[{"label": f"Runde {r}", "value": r}
                                        for r in range(1, turnier.runden + 1)] +
                                       ([{"label": "Alle Runden", "value": auswertung.ALLE_RUNDEN}]
                                        if turnier.runden > 1 else [])),
                dcc.Graph(id="turnier-verlauf", style={"height": "75vh"}),
            ]), label="Verlauf", tab_id="verlauf"),
            dbc.Tab(html.Div(id="turnier-highlights", className="mt-3"), label="Highlights", tab_id="highlights"),
            dbc.Tab(html.Div([
                dbc.Switch(id="turnier-qr_anzeigen", label="QR-Codes anzeigen", value=False, className="my-3"),
                html.Div(id="turnier-tische"),
            ]), label="Tische", tab_id="tische"),
        ], id="turnier-tabs", active_tab="rangliste", persistence=True),
    ], fluid=True)


def gew_verl(eintrag: dict, schluessel: str):
    gewonnen, verloren = eintrag[schluessel + "_gewonnen"], eintrag[schluessel + "_verloren"]
    return [html.Span(gewonnen, className="positiv" if gewonnen else ""), " / ",
            html.Span(verloren, className="negativ" if verloren else "")]


def rangliste_tabelle(turnier: Turnier):
    eintraege = auswertung.rangliste(turnier)
    if not eintraege:
        return html.P("Noch keine Tische angelegt.", className="text-muted")
    runden = range(1, turnier.runden + 1)
    kopf = html.Thead(html.Tr(
        [html.Th("Rang"), html.Th("Name")] + [html.Th(f"Runde {r}") for r in runden] +
        [html.Th("Gesamt"), html.Th([deko.farb_icon("herz"), " Herzsoli"]), html.Th("Sauspiele"),
         html.Th("Solo eigen"), html.Th("Solo fremd"), html.Th("Wenz eigen"), html.Th("Wenz fremd")]
    ))
    zeilen = [html.Tr(
        [html.Td(e["rang"]), html.Td(e["name"])] +
        [html.Td(deko.wert(e["runden"][r]) if r in e["runden"] else "") for r in runden] +
        [html.Td(html.Strong(deko.wert(e["gesamt"]))), html.Td(e["herzsoli"]),
         html.Td(gew_verl(e, "sauspiel")), html.Td(gew_verl(e, "solo_eigen")), html.Td(gew_verl(e, "solo_fremd")),
         html.Td(gew_verl(e, "wenz_eigen")), html.Td(gew_verl(e, "wenz_fremd"))]
    ) for e in eintraege]
    return html.Div([
        dbc.Table([kopf, html.Tbody(zeilen)], striped=True, hover=True, size="sm",
                  className="text-nowrap rangliste"),
        html.Small("Spiele: gewonnen / verloren. Eigen: selbst gespielt, fremd: als Gegenspieler. "
                   "Bei Punktgleichstand entscheiden die Herzsoli.", className="text-muted"),
    ], className="table-responsive")


def namen_entzerren(enden: list[tuple[str, int, int]], abstand: float) -> dict[str, float]:
    """Verschiebt die Namen an den Linienenden so, dass sie sich nicht überlappen.
    `enden` sind (name, x, y) des letzten Punkts, nur Namen mit gleichem x können kollidieren."""
    positionen = {}
    for x in {x for _, x, _ in enden}:
        gruppe = sorted((y, name) for name, gx, y in enden if gx == x)
        vorher = None
        for y, name in gruppe:
            y = y if vorher is None else max(y, vorher + abstand)
            positionen[name] = vorher = y
    return positionen


def runden_trennung(fig, turnier: Turnier) -> None:
    """Bei allen Runden: jede zweite Runde hinterlegt, gestrichelte Grenzen, Rundenname oben."""
    n = turnier.spiele_pro_runde
    for r in range(1, turnier.runden + 1):
        von = (r - 1) * n
        if r % 2 == 0:
            fig.add_vrect(x0=von, x1=von + n, fillcolor="#efe4c9", opacity=0.6, line_width=0, layer="below")
        if r > 1:
            fig.add_vline(x=von, line=dict(color="#a8987a", width=1.5, dash="dash"), layer="below")
        fig.add_annotation(x=von + n / 2, y=1, yref="paper", yanchor="bottom", showarrow=False,
                           text=f"Runde {r}", font=dict(family="Grenze Gotisch, serif", size=20, color="#2b2118"))


def verlauf_grafik(turnier: Turnier, runde: int):
    alle = runde == auswertung.ALLE_RUNDEN
    linien = sorted(auswertung.verlauf(turnier, runde).items())
    n = turnier.spiele_pro_runde
    fig = go.Figure()
    for name, punkte in linien:
        # Fehlen Spiele (Runde nicht fertig gespielt), wird die Linie unterbrochen statt quer verbunden
        x, y, daten = [], [], []
        for px, py, r, spiel in punkte:
            if x and px > x[-1] + 1:
                x.append(None), y.append(None), daten.append(None)
            x.append(px), y.append(py), daten.append((r, spiel))
        # Punkt nur am Linienende, er verbindet die Linie mit ihrem Namen
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=name, line=dict(width=2),
                                 marker=dict(size=[0] * (len(x) - 1) + [8]), customdata=daten,
                                 hovertemplate=f"{name} · Runde %{{customdata[0]}}, Spiel %{{customdata[1]}}"
                                               f" · %{{y}} Punkte<extra></extra>"))

    if linien:
        alle_punkte = [p[1] for _, punkte in linien for p in punkte]
        abstand = max(max(alle_punkte) - min(alle_punkte), 10) * 0.045
        enden = [(name, punkte[-1][0], punkte[-1][1]) for name, punkte in linien]
        positionen = namen_entzerren(enden, abstand)
        for name, x, y in enden:
            diff = y - turnier.startpunkte
            farbe = "#287000" if diff > 0 else "#cb2714" if diff < 0 else "#6f604c"
            fig.add_annotation(x=x, y=positionen[name], showarrow=False, xanchor="left", xshift=8,
                               text=f"{name} <span style='color:{farbe}'>{f'{diff:+d}' if diff else '±0'}</span>",
                               font=dict(size=13, color="#2b2118"))

    schritt = max(1, n // 16)
    if alle:
        runden_trennung(fig, turnier)
        # Spielnummer zählt in jeder Runde neu, an der Grenze steht das Rundenende
        schritt = max(1, n * turnier.runden // 16)
        ticks = [x for x in range(0, n * turnier.runden + 1) if (x % n) % schritt == 0 or x % n == 0]
        fig.update_xaxes(tickmode="array", tickvals=ticks,
                         ticktext=[str(n if x and x % n == 0 else x % n) for x in ticks])

    fig.update_layout(
        xaxis_title="Spiel", yaxis_title="Punkte" + (" gesamt" if alle else ""),
        xaxis_range=[0, n * (turnier.runden if alle else 1)], xaxis_dtick=schritt,
        margin=dict(l=40, r=260, t=40 if alle else 20, b=40),
        # Legende an den rechten Rand der ganzen Grafik, dazwischen bleibt Platz für die Namen an den Linienenden
        legend=dict(xref="container", x=1, xanchor="right", yref="paper", y=1, yanchor="top"), template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fffaf0",
        font=dict(family="Vollkorn, Georgia, serif", color="#2b2118", size=14),
        uirevision=runde,  # Zoom und ausgeblendete Linien bleiben bei Aktualisierung erhalten
    )
    fig.update_xaxes(gridcolor="#ece2cb", zerolinecolor="#d8cbb0")
    fig.update_yaxes(gridcolor="#ece2cb", zerolinecolor="#d8cbb0")
    return fig


def spielkarte(farbe: str, inhalt: list, className: str = ""):
    """Karte im Stil einer Spielkarte: Farbsymbol in den Ecken und groß als Wasserzeichen."""
    return html.Div([
        deko.farb_icon(farbe, "wasserzeichen"),
        deko.farb_icon(farbe, "ecke ecke-oben"),
        deko.farb_icon(farbe, "ecke ecke-unten"),
    ] + inhalt, className=f"spielkarte {className}")


def karten_spalte(karte):
    return dbc.Col(karte, xs=12, sm=6, lg=4, xl=3, className="mb-3")


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
        karten.append(karten_spalte(dbc.Card(dbc.CardBody(inhalt), className="text-center")))
    return dbc.Row(karten)


def tisch_uebersicht(turnier: Turnier):
    abschnitte = []
    for runde in range(1, turnier.runden + 1):
        karten = []
        for i, tisch in enumerate(turnier.tische):
            tr = turnier.tischrunde(runde, tisch)
            if tr:
                stand = tr.punkte_verlauf(turnier.startpunkte)[-1]
                fortschritt = ("beendet" if turnier.runde_beendet(tr)
                               else f"Spiel {tr.naechstes_spiel} / {turnier.spiele_pro_runde}")
                zeilen = [html.Li([html.Span(n), html.Strong(deko.wert(stand[n], vorzeichen=False,
                                                                        bezug=turnier.startpunkte))],
                                  className="d-flex justify-content-between") for n in tr.spieler]
            else:
                fortschritt = "nicht angelegt"
                zeilen = [html.Li(" ") for _ in range(4)]
            karten.append(karten_spalte(spielkarte(deko.farbe(i), [
                html.H5(html.A(tisch, href=f"/{quote(turnier.name)}/{quote(tisch)}",
                               className="text-reset text-decoration-none"), className="karten-titel"),
                html.Small(fortschritt, className="text-muted"),
                html.Ul(zeilen, className="list-unstyled mb-0 mt-2"),
            ])))
        abschnitte += [html.H3(f"Runde {runde}", className="h4"), dbc.Row(karten)]
    return abschnitte


def highlight_wert(wert, vorzeichen: bool, einheit: str):
    if isinstance(wert, float) and not wert.is_integer():
        return f"{wert:.1f}".replace(".", ",") + einheit
    if isinstance(wert, (int, float)):
        return [deko.wert(int(wert)) if vorzeichen else str(int(wert)), einheit]
    return wert


def highlights_karten(turnier: Turnier):
    karten = highlights.highlights(turnier)
    if not karten:
        return html.P("Noch keine Highlights, erst einmal spielen.", className="text-muted")
    # Spaltenlayout statt Bootstrap-Raster: schmale Karten, die sich je nach Höhe versetzt anordnen
    return html.Div([spielkarte(k["farbe"], [
        html.H5(k["titel"], className="karten-titel"),
        html.Small(k["erklaerung"], className="text-muted d-block"),
        html.Ul([html.Li([
            html.Div([html.Span(e["name"]),
                      html.Small(e["detail"], className="text-muted d-block") if e["detail"] else None]),
            html.Strong(highlight_wert(e["wert"], k["vorzeichen"], k["einheit"]), className="ms-2 text-nowrap"),
        ], className="d-flex justify-content-between align-items-start") for e in k["eintraege"]],
            className="list-unstyled mb-0 mt-2"),
    ], className="highlight") for k in karten], className="highlight-raster")


@callback(
    Output("turnier-rangliste", "children"),
    Output("turnier-verlauf", "figure"),
    Output("turnier-tische", "children"),
    Output("turnier-highlights", "children"),
    Input("turnier-intervall", "n_intervals"),
    Input("turnier-verlauf_runde", "value"),
    Input("turnier-qr_anzeigen", "value"),
    State("turnier-name", "data"),
)
def aktualisieren(_, runde, qr_anzeigen, name):
    turnier = Turnier.laden(name)
    tische = qr_uebersicht(turnier) if qr_anzeigen else tisch_uebersicht(turnier)
    return rangliste_tabelle(turnier), verlauf_grafik(turnier, runde), tische, highlights_karten(turnier)
