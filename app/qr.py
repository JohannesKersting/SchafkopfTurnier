"""QR-Codes für die Tische, zum Ausdrucken und Aufkleben."""

import html
import os
import socket
from urllib.parse import quote

import qrcode
from PIL import Image, ImageDraw, ImageFont

import einstellungen
from turnier import Turnier

QR_ORDNER = "qr"
# Pillows eingebaute Schrift kann keine Umlaute, daher wenn möglich eine Systemschrift.
SCHRIFTEN = ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]


def lokale_basis_url() -> str:
    """URL dieses Rechners im lokalen Netz. Der UDP-Socket sendet nichts, er ermittelt nur
    die Netzwerkschnittstelle, über die das Internet erreichbar wäre."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except OSError:
        ip = socket.gethostbyname(socket.gethostname())
    return f"http://{ip}:{einstellungen.PORT}"


def tisch_url(basis_url: str, turnier: str, tisch: str) -> str:
    return f"{basis_url.rstrip('/')}/{quote(turnier)}/{quote(tisch)}"


def qr_dateiname(tisch: str) -> str:
    return f"{tisch}.png"


def _schrift(groesse: int):
    for schrift in SCHRIFTEN:
        try:
            return ImageFont.truetype(schrift, groesse)
        except OSError:
            pass
    return ImageFont.load_default(size=groesse)


def _qr_bild(url: str, beschriftung: str) -> Image.Image:
    code = qrcode.make(url, border=2, box_size=12).convert("RGB")
    font = _schrift(48)
    hoehe_text = 90
    bild = Image.new("RGB", (code.width, code.height + hoehe_text), "white")
    bild.paste(code, (0, 0))
    ImageDraw.Draw(bild).text((code.width / 2, code.height + hoehe_text / 2), beschriftung,
                              fill="black", font=font, anchor="mm")
    return bild


def qr_codes_erzeugen(turnier: Turnier) -> str:
    """Schreibt ein PNG pro Tisch und eine Druckseite alle.html in <turnier>/qr/."""
    ordner = os.path.join(turnier.pfad, QR_ORDNER)
    os.makedirs(ordner, exist_ok=True)
    karten = []
    for tisch in turnier.tische:
        url = tisch_url(turnier.basis_url, turnier.name, tisch)
        _qr_bild(url, tisch).save(os.path.join(ordner, qr_dateiname(tisch)))
        karten.append(f'<figure><img src="{quote(qr_dateiname(tisch))}"><figcaption>'
                      f'{html.escape(turnier.name)}<br><small>{html.escape(url)}</small></figcaption></figure>')
    with open(os.path.join(ordner, "alle.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html><meta charset="utf-8"><title>QR-Codes {html.escape(turnier.name)}</title>
<style>
  body {{ font-family: sans-serif; display: flex; flex-wrap: wrap; gap: 1cm; }}
  figure {{ margin: 0; width: 8cm; text-align: center; break-inside: avoid; }}
  img {{ width: 100%; }}
</style>
{''.join(karten)}
""")
    return ordner
