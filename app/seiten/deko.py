"""Gemeinsame Gestaltungselemente: Farbsymbole des bayerischen Blatts und farbige Werte."""

from dash import html

# Reihenfolge der Farben, auch für Sitzplätze (im Uhrzeigersinn) und Tische (reihum).
FARBEN = ["eichel", "gras", "herz", "schellen"]


def farbe(i: int) -> str:
    return FARBEN[i % len(FARBEN)]


def farb_icon(name: str, className: str = "farb-icon"):
    return html.Img(src=f"/assets/icons/{name}.svg", alt=name.capitalize(), className=className)


def farben_leiste():
    return html.Div([farb_icon(f) for f in FARBEN], className="farben-leiste")


def titel(text: str, untertitel=None, className: str = ""):
    return html.Header([
        html.H1(text, className="titel mb-0"),
        html.Div(untertitel, className="untertitel") if untertitel else None,
        farben_leiste(),
    ], className=f"seiten-kopf {className}")


def wert_klasse(zahl: int) -> str:
    return "positiv" if zahl > 0 else "negativ" if zahl < 0 else ""


def wert(zahl: int, vorzeichen: bool = True, bezug: int = 0):
    """Zahl grün/rot einfärben, je nachdem ob sie über oder unter `bezug` liegt."""
    text = f"{zahl:+d}" if vorzeichen else str(zahl)
    return html.Span(text, className=wert_klasse(zahl - bezug))
