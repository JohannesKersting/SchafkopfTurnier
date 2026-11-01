# Schafkopf Turnier

Kleine Dash-App, um bei einem Schafkopfturnier die Punkte pro Tisch per Handy einzutragen.
Alle Daten liegen als Dateien in `data/`, eine Datenbank gibt es nicht.

## Starten

```bash
conda env create -f environment.yaml
conda activate SchafkopfTunier
python app/app.py
```

Die App läuft auf Port 8050 und ist im lokalen Netz erreichbar. Mit `PORT`, `DATA_DIR` und `DEBUG=True` lässt
sich das anpassen.

## Seiten

| URL | Inhalt |
| --- | --- |
| `/admin` | Turniere anlegen, QR-Codes neu erzeugen und drucken, Cache leeren |
| `/<Turnier>` | Bildschirmansicht: Rangliste, Punkteverlauf, Tische |
| `/<Turnier>/<Tisch>` | Handyansicht für einen Tisch, erreichbar über den QR-Code |

## Dateien

```
data/<Turnier>/
  turnier.yaml                 # Konfiguration, darf von Hand bearbeitet werden
  qr/<Tisch>.png, qr/alle.html # QR-Codes zum Ausdrucken
  runde1_<Tisch>_spiele.tsv    # ein Spiel pro Zeile, Punkteänderung je Spieler
  runde1_<Tisch>_punkte.tsv    # laufender Punktestand, wird aus der Spiele-Datei erzeugt
```

**Korrekturen:** In `runde<N>_<Tisch>_spiele.tsv` die betroffene Zeile ändern oder löschen. Die Rangliste
übernimmt das sofort. Die Punkte-Datei wird erst beim nächsten Eintrag an diesem Tisch neu erzeugt.

Die Runde eines Tisches ist die höchste Runde, für die eine Spiele-Datei existiert. Einen Tisch zurücksetzen
heißt also, seine beiden Dateien dieser Runde zu löschen.

## Tests

```bash
pytest -p no:dash tests
```
