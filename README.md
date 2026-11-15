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

## Wertung

Ein Spiel kostet jeden Gegenspieler Grundtarif (Sauspiel oder Solo/Wenz) plus je Schneider-Stufe und
Laufendem den eingestellten Tarif. Beim Solo bekommt bzw. zahlt der Solist das Dreifache.

- **Tout** (Solo, Wenz): `Tout-Faktor × (Grundtarif + Laufende)`, Schneider und Schwarz zählen nicht extra.
- **Sie** (nur Solo, immer gewonnen): `Sie-Faktor × (Grundtarif + 8 Laufende)`.

Die Faktoren (Standard 2 und 4) werden beim Erstellen des Turniers festgelegt. Ein gewonnenes Solo mit allen
8 Laufenden ist immer ein Sie, die Eingabe am Tisch wählt das eine automatisch mit dem anderen aus.

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

## Gestaltung

Alles liegt in `app/assets/`, damit die App auch ohne Internet läuft.

- Bootstrap 5.3.6, Farben überschrieben in `theme.css`
- Schriften: [Grenze Gotisch](https://fonts.google.com/specimen/Grenze+Gotisch) und
  [Vollkorn](https://fonts.google.com/specimen/Vollkorn), beide SIL Open Font License
- Farbsymbole: `Bay eichel.svg`, `Bay gras.svg`, `Bay herz.svg` und `Bay schellen.svg` von
  [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Bay_herz.svg), gemeinfrei
