# 🌤️ Wetterinfo

Ein Web-Projekt zur automatisierten Verarbeitung und interaktiven Visualisierung von Wetterdaten. Die Anwendung greift auf Daten des Deutschen Wetterdienstes (DWD) zu, verarbeitet diese und stellt sie über ein statisches Web-Frontend bereit.

## ✨ Features

- **Aktuelle Temperaturen & Wetterlage:** Visualisierung von DWD MOSMIX-, WarnMOS-Daten und lokalen Messwerten.
- **Regenradar & Vorhersage:** Interaktive Karten für den aktuellen Niederschlag und kurzfristige blending Prognosen.
- **UV-Index & Gefühlte Temperatur:** Darstellung detaillierter meteorologischer Parameter.
- **Wetter-Icons:** Selbst erstellte Icons für eine schnelle Informationsübersicht.
- **Vollautomatisierte Daten-Pipelines:** Backend-Code zur regelmäßigen und zuverlässigen beschaffung der Daten für das Frontend.

## 🏗 Architektur & Hosting

Das Projekt nutzt einen privaten Backendserver, um zyklisch aktuelle Wetterdaten abzurufen und zu verarbeiten.

* **Workflow:** Die Skripte in den Unterordner des `backend` Ordners werden regelmäßig per Cron-Job ausgeführt. Es lädt die neuesten Rohdaten herunter, führt die Verarbeitung mittels Python durch und generiert die entsprechenden statischen Dateien.
* **Hosting (GitHub Pages):** Das Frontend (`docs/`-Ordner) lädt die aktuellsten verarbeiteten Daten vom Server und stellt sie unter **[GitHub Pages](https://stefan436.github.io/Wetterinfo/)** bereit.


## 🛠️ Tech-Stack

- **Frontend:** HTML5, CSS3, JavaScript.
- **Backend Für Wetterzusammenfassung:** Python 3
- **Datenquellen:** DWD Open Data (MOSMIX, WarnMOS, Radar-Komposits, ICON-D2-RUC), Currentuvindex.com (UV-Index Messung).

## 📂 Projektstruktur

Das Repository ist in die Datenverarbeitung (`backend/`) und die Web-Darstellung (`docs/`) unterteilt:

```text
📦 wetterinfo
 ┣ 📂 backend                # Python-Backend für Datenbeschaffung und Verarbeitung
 ┃ ┣ 📂 BlendingForecast     # Vorhersage-Engine (ICON, Radar, Verschmelzung, Export)
 ┃ ┣ 📂 index                # Verarbeitung von DWD-Daten (UV, PT, MOSMIX, WarnMOS)
 ┃ ┗ 📂 widget               # Skript zur Widget-Generierung (create_widget_info.py)
 ┣ 📂 docs                   # Web-Frontend (GitHub Pages Root)
 ┃ ┣ 📂 data                 # Generierte Binär- und JSON-Dateien (z.B. coords_radarcomposite_rv.bin)
 ┃ ┣ 📂 icons                # Wetter-Icons
 ┃ ┣ 📂 scripts              # JavaScript-Logik (Menü, UV/PT, Map-Interaktionen)
 ┃ ┣ 📂 styles               # CSS-Stylesheets
 ┃ ┣ 📂 sites                # Weitere HTML-Seiten
 ┃ ┣ 📜 index.html           # Hauptseite
 ┣ 📜 .gitignore             # Git Ignore-Datei
 ┣ 📜 LICENSE                # Lizenzinformationen
 ┗ 📜 README.md              # Projektdokumentation
```

## ⚖️ Lizenz & Nutzungsbedingungen

Der Quellcode dieses Projekts steht unter der [MIT-Lizenz](LICENSE).

**Datenquellen (DWD):**
Die in diesem Projekt visualisierten Wetterdaten stammen vom Deutschen Wetterdienst (DWD). Detaillierte Informationen zu den genauen Datenquellen und den rechtlichen Hinweisen sind direkt auf den entsprechenden Unterseiten der Web-Anwendung (jeweils am unteren Seitenrand) zu entnehmen.
