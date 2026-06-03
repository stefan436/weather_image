# 🌤️ Wetterinfo

Ein Web-Projekt zur automatisierten Verarbeitung und interaktiven Visualisierung von Wetterdaten. Die Anwendung greift auf Daten des Deutschen Wetterdienstes (DWD) zu, verarbeitet diese und stellt sie über ein statisches Web-Frontend bereit.

## ✨ Features

- **Aktuelle Temperaturen & Wetterlage:** Visualisierung von DWD MOSMIX-Daten und lokalen Messwerten.
- **Regenradar & Vorhersage:** Interaktive Karten für den aktuellen Niederschlag und kurzfristige Prognosen.
- **UV-Index & Gefühlte Temperatur:** Darstellung detaillierter meteorologischer Parameter.
- **Wetter-Icons:** Selbst erstellte Icons für eine schnelle Informationsübersicht.
- **Vollautomatisierte Daten-Pipelines:** GitHub-Actions-Workflow sorgt für stündliche und zuverlässige Wetterzusammenfassung (weather-summary.json), welche in einem Widget dargestellt werden kann.

## 🚀 Live-Demo

Die Anwendung wird über **[GitHub Pages](https://stefan436.github.io/Wetterinfo/)** gehostet.

## 🏗 Architektur & Automatisierung

Das Projekt nutzt **GitHub Actions**, um zyklisch aktuelle Wetterdaten abzurufen, zu verarbeiten und die Webseite zu aktualisieren.

* **Workflow (`deploy_weather_app.yml`):** Das Skript wird regelmäßig per Cron-Job ausgeführt. Es lädt die neuesten Rohdaten herunter, führt die Python-Verarbeitungsskripte aus und generiert die entsprechenden statischen Dateien im `docs/`-Ordner.
* **Hosting (GitHub Pages):** Der `docs/`-Ordner wird nach der Generierung als Artefakt verpackt und direkt über GitHub Pages deployed. 


## 🛠️ Tech-Stack

- **Frontend:** HTML5, CSS3, JavaScript (Marching-Squares-Algorithmus für Isolinien und mehr).
- **Backend Für Wetterzusammenfassung:** Python 3
- **Datenquellen:** DWD Open Data (MOSMIX, Radar-Komposits), Currentuvindex.com (UV-Index Messung).
- **CI/CD & Automatisierung:** GitHub Actions.

## 📂 Projektstruktur

Das Repository ist in die Datenverarbeitung (Root) und die Web-Darstellung (`docs/`) unterteilt:

```text
📦 wetterinfo
 ┣ 📂 .github/workflows      # CI/CD Pipelines für automatische Updates
 ┣ 📂 docs                   # Web-Frontend (GitHub Pages Root)
 ┃ ┣ 📂 data                 # Generierte JSON- und Binärdateien (Koordinaten, MOSMIX, etc.)
 ┃ ┣ 📂 icons                # Wetter-Icons
 ┃ ┣ 📂 scripts              # JavaScript-Logik (Menü, UV/PT, Map-Interaktionen)
 ┃ ┣ 📂 styles               # CSS-Stylesheets
 ┃ ┣ 📜 index.html           # Hauptseite
 ┃ ┣ 📜 Regenradar.html      # Regenradar-Ansicht
 ┃ ┗ 📜 ...                  # Weitere HTML-Ansichten
 ┣ 📜 create_widget_info.py  # Python-Skript zur Widget-Generierung
 ┣ 📜 process_dwd_uv_and_pt.py # Skript zur UV-Index und PT-Berechnung
```

## ⚖️ Lizenz & Nutzungsbedingungen

Der Quellcode dieses Projekts steht unter der [MIT-Lizenz](LICENSE).

**Datenquellen (DWD):**
Die in diesem Projekt visualisierten Wetterdaten stammen vom Deutschen Wetterdienst (DWD). Detaillierte Informationen zu den genauen Datenquellen und den rechtlichen Hinweisen sind direkt auf den entsprechenden Unterseiten der Web-Anwendung (jeweils am unteren Seitenrand) zu entnehmen.
