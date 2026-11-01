import os
from urllib.parse import quote, unquote

import dash
import dash_bootstrap_components as dbc
import flask
from dash import dcc, html, Input, Output, callback

import einstellungen
import qr
import turnier as t
from seiten import admin, deko, tisch, turnier_seite

server = flask.Flask(__name__)
# Bootstrap, Schriften und Icons liegen in assets/, damit die App ohne Internet funktioniert.
app = dash.Dash(__name__, server=server, title="Schafkopf Turnier", suppress_callback_exceptions=True,
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
app.index_string = app.index_string.replace(
    "{%favicon%}", '<link rel="icon" type="image/svg+xml" href="/assets/icons/herz.svg">')

app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(id="seite"),
])


def startseite():
    return dbc.Container([
        deko.titel("Schafkopf Turnier"),
        dbc.ListGroup([dbc.ListGroupItem(dcc.Link(name, href=f"/{quote(name)}")) for name in t.turnier_liste()]),
        dcc.Link("Admin", href="/admin", className="d-block mt-3"),
    ])


def nicht_gefunden(text):
    return dbc.Container(dbc.Alert(text, color="danger", className="mt-3"))


@callback(Output("seite", "children"), Input("url", "pathname"))
def seite_anzeigen(pfad):
    """Eigenes Routing statt Dash Pages, damit Turnier- und Tischnamen mit Umlauten,
    Leerzeichen oder Emojis sauber aus der URL dekodiert werden."""
    teile = [unquote(teil) for teil in (pfad or "/").strip("/").split("/") if teil]
    if not teile:
        return startseite()
    if teile == ["admin"]:
        return admin.layout()
    turnier = t.Turnier.laden(teile[0])
    if not turnier:
        return nicht_gefunden(f"Turnier '{teile[0]}' nicht gefunden.")
    if len(teile) == 1:
        return turnier_seite.layout(turnier)
    if len(teile) == 2:
        return tisch.layout(turnier, teile[1])
    return nicht_gefunden("Seite nicht gefunden.")


@server.route("/_qr/<turnier>/<path:datei>")
def qr_datei(turnier, datei):
    if t.name_fehler(turnier, "Turniere"):
        flask.abort(404)
    return flask.send_from_directory(os.path.join(einstellungen.DATA_DIR, turnier, qr.QR_ORDNER), datei)


if __name__ == "__main__":
    debug = os.getenv("DEBUG", "False") == "True"
    app.run(debug=debug, host="0.0.0.0", port=einstellungen.PORT, threaded=True)
