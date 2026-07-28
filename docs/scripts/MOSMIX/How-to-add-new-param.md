# Cheat-Sheet: Neue Parameter ins Wetter-Dashboard integrieren

## Fall 1: Standard-Parameter (Einzelner Wert)

1. **Bezeichnung festlegen (`src/config/elementNamesMap.js`)**  
   Kürzel aus der `.json` in einen lesbaren Namen übersetzen:
   ```javascript
   "JSON_KEY": "Anzeigename",
    ```

2. **Einheit & Umrechnung (`src/config/constants.js`)**  
    In `unitProcessingConfig` definieren:
    ```javascript
    JSON_KEY: { unit: "%", convert: (v) => v * 100 },
    ```

3. **Im UI freischalten (`src/config/constants.js`)**  
    Den `"Anzeigename"` in das Array `includedDropdownElements` einfügen.
    *(Optional: Für eine feste Positionierung zusätzlich in `preferredOrder` eintragen).*

4. **Darstellung (`src/ui/plot.js`)**  
    Ohne Anpassung wird automatisch ein Standard-Graph gezeichnet.
    * Feste Achsen: In `getLayout()` anpassen.
    * Eigenes Design: `if (param === "Anzeigename")`-Block in `renderPlot()` vor dem Standard-Plot ergänzen.



## Fall 2: Kombinierter Parameter (1 Hauptwert + mehrere Sub-Werte)

*Ziel: Mehrere Parameter in einem gemeinsamen Graphen plotten (z.B. Hauptwahrscheinlichkeit + Modelle).*

1. **Sammelparameter (`MAIN_KEY`) in `seriesMap` initialisieren (`src/api/weatherParser.js`)**  
    `MAIN_KEY` *kann beliebig genannt werden.*
    Prüfe, ob alle `SUB_KEY`s vorhanden sind und initialisiere `MAIN_KEY`:
    ```javascript
    if (
        seriesMap["SUB_KEY_1"] || 
        seriesMap["SUB_KEY_2"] || 
        seriesMap["SUB_KEY_3"] || 
        seriesMap["SUB_KEY_4"]
    ) {
        seriesMap["MAIN_KEY"] = []; 
    }
    ```

2. **Alle Werte benennen (`src/config/elementNamesMap.js`)**  
    Kürzel des Hauptparameters UND aller Sub-Parameter übersetzen:
    ```javascript
    "MAIN_KEY": "Haupt-Anzeigename",
    "SUB_KEY_1": "Sub-Anzeigename 1",
    // ...
    ```

3. **Im UI freischalten (`src/config/constants.js`)**  
    **WICHTIG:** Nur den `"Haupt-Anzeigename"` in `includedDropdownElements` (und ggf. `preferredOrder`) eintragen. Die Sub-Parameter werden unsichtbar im Hintergrund geladen.

4. **Feste Achsen definieren (`src/ui/plot.js` -> `getLayout()`)**  
    Achsen-Limits für den `"Haupt-Anzeigename"` festlegen.

5. **Graphen zeichnen (`src/ui/plot.js` -> `renderPlot()`)**  
    Vor dem Standard-Plot eine eigene Routine für den Hauptwert einfügen und zwingend mit `return` beenden:
    ```javascript
    if (param === "Haupt-Anzeigename") {
        // 1. Haupt-Trace definieren und in traces pushen (Nutzt xData/yData)
        // 2. Sub-Werte aus dem Hintergrundspeicher abrufen und pushen:
        if (seriesMap["Sub-Anzeigename 1"]) {
            // Trace für Sub-Wert erstellen (x: xData, y: seriesMap["Sub-Anzeigename 1"])
        }

        // 3. Layout mergen & Plot rendern (WICHTIG: enforcePanAfterZoom anhängen!)
        Plotly.newPlot(plotlyDiv, traces, layout, getConfig()).then(() =>
            enforcePanAfterZoom(plotlyDiv)
        );

        // 4. WICHTIG: Funktion beenden, Standard-Plot überspringen!
        return; 
    }
    ```