import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.colors import Normalize
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import shutil
import tempfile
import requests
import subprocess
import numpy as np
from matplotlib.collections import LineCollection
from scipy.interpolate import interp1d
from scipy.interpolate import PchipInterpolator
from zoneinfo import ZoneInfo
from astral import LocationInfo
from astral.sun import sun
from datetime import date, datetime, timezone
import pytz
from pathlib import Path

# Basisverzeichnis
BASE_DIR = Path(__file__).parent



def download_file(url, target_path):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # Fehler werfen bei HTTP-Code != 200
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"Fehler beim Download von {url}: {e}")
        
        
def parse_kml_forecast_for_station_mosmix_s(kml_file, target_station_name):
    # XML einlesen
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Namespaces definieren
    ns = {
        "kml": "http://www.opengis.net/kml/2.2",
        "dwd": "https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd"
    }

    # Zeitstempel extrahieren
    time_steps = [elem.text for elem in root.findall(".//dwd:ForecastTimeSteps/dwd:TimeStep", ns)]
    timestamps = pd.to_datetime(time_steps)
    # In Berliner Zeitzone umrechnen
    timestamps_berlin = timestamps.tz_convert(ZoneInfo("Europe/Berlin"))
    num_steps = len(timestamps_berlin)

    # Nur die gesuchte Station verarbeiten
    for placemark in root.findall(".//kml:Placemark", ns):
        station_name_elem = placemark.find("kml:description", ns)
        station_name = station_name_elem.text if station_name_elem is not None else ""

        if station_name != target_station_name:
            continue  # Überspringen, wenn nicht die gesuchte Station

        station_id = placemark.find("kml:name", ns).text

        data = {
            "Zeit": timestamps_berlin,
            "Stations_ID": station_id,
            "Stationsname": station_name
        }

        for forecast_elem in placemark.findall(".//dwd:Forecast", ns):
            element_name = forecast_elem.get("{https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd}elementName")
            value_text = ''.join(v.text for v in forecast_elem.findall("dwd:value", ns)).strip()
            value_strings = value_text.split()
            values = [float(v) if v != '-' else None for v in value_strings]

            if len(values) == num_steps:
                data[element_name] = values
            else:
                print(f"Warnung: {element_name} bei Station {station_id} hat {len(values)} Werte, erwartet: {num_steps}")

        df = pd.DataFrame(data)
        df['TTT'] = df['TTT'] - 273  # Kelvin zu Celsius
        df['TTT'] = df['TTT'].round(0).astype(int)
        df['FF'] = df['FF'] * 3.6
        df['FF'] = df['FF'].round(0).astype(int)
        df['FX1'] = df['FX1'] * 3.6
        df['FX1'] = df['FX1'].round(0).astype(int)
        df['RR1c'] = df['RR1c'].round(1)
        return df

    # Falls Station nicht gefunden wurde
    print(f"Station '{target_station_name}' nicht gefunden.")
    return pd.DataFrame()


def parse_kml_forecast_mosmix_l(kml_file):
    # XML einlesen
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Namespace definieren
    ns = {
        "kml": "http://www.opengis.net/kml/2.2",
        "dwd": "https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd"
    }

    # Zeitstempel extrahieren
    time_steps = [elem.text for elem in root.findall(".//dwd:ForecastTimeSteps/dwd:TimeStep", ns)]
    timestamps = pd.to_datetime(time_steps)
    # In Berliner Zeitzone umrechnen
    timestamps_berlin = timestamps.tz_convert(ZoneInfo("Europe/Berlin"))
    num_steps = len(timestamps_berlin)

    # Basisdatenstruktur mit Zeitspalte
    data = {
        "Zeit": pd.to_datetime(timestamps_berlin)
    }

    # Forecasts extrahieren
    for forecast_elem in root.findall(".//dwd:Forecast", ns):
        element_name = forecast_elem.get("{https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd}elementName")
        value_text = ''.join(v.text for v in forecast_elem.findall("dwd:value", ns)).strip()
        value_strings = value_text.split()

        # Parse: '-' → None, sonst float
        values = [float(v) if v != '-' else None for v in value_strings]

        if len(values) == num_steps:
            data[element_name] = values
        else:
            print(f"Warnung: {element_name} hat {len(values)} Werte, erwartet: {num_steps}")

    df = pd.DataFrame(data)
    df['TTT'] = df['TTT']-273
    return df

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

url_mosmix_s = r"https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/all_stations/kml/MOSMIX_S_LATEST_240.kmz"  
filename_mosmix_s = url_mosmix_s.split("/")[-1]
kmz_file_s = DATA_DIR / filename_mosmix_s
url_mosmix_l = r"https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/10865/kml/MOSMIX_L_LATEST_10865.kmz"
filename_mosmix_l = url_mosmix_l.split("/")[-1]
kmz_file_mosmix_l = DATA_DIR / filename_mosmix_l


download_file(url_mosmix_s, kmz_file_s)

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(kmz_file_s, "r") as z:
        z.extractall(temp_dir)  # Entpacken ins temporäre Verzeichnis
        kml_file = os.path.join(temp_dir, z.namelist()[0])  # Nimmt die erste Datei
        
        df = parse_kml_forecast_for_station_mosmix_s(kml_file, "MUENCHEN STADT")


download_file(url_mosmix_l, kmz_file_mosmix_l)

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(kmz_file_mosmix_l, "r") as z:
        z.extractall(temp_dir)  # Entpackt alle Dateien
        kml_file = os.path.join(temp_dir, z.namelist()[0])  # Nimmt die erste Datei

        df_l = parse_kml_forecast_mosmix_l(kml_file)
        df_l.loc[:, 'wwT'] = df_l['wwT'].fillna(0)


df = pd.merge_asof(
    df.sort_values("Zeit"), 
    df_l.sort_values("Zeit"), 
    on="Zeit", 
    direction="nearest"  # Alternativ: "backward", "forward"
)

df_1 = df.head(24).reset_index(drop=True)
df_2 = df.iloc[24:48].reset_index(drop=True)

anzahl_std = len(df_1) - 1

# Bilddimensionen
width_per_hour = 50 # muss angepasst werden auf 25 wenn anstatt von 24 48 stunden gezeigt werden sollen
width = width_per_hour * len(df_1)
height = int((width/360) * 188)
dpi = 150

# Interpolation vorbereiten
x = list(range(0, anzahl_std + 1))
x_fine = np.linspace(min(x), max(x), 500)

# Temperaturkurve interpolieren
temp_interp = interp1d(x, df_1['TTT_x'], kind='cubic')
temp_y = temp_interp(x_fine)

# Regenkurve interpolieren mit PchipInterpolator
rain_interp = PchipInterpolator(x, df_1['RR1c_x'])
rain_y = rain_interp(x_fine)


# Matplotlib-Zeichenfläche
fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
ax.axis('off')
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)


# Regenfläche (nach oben zeigend von Basislinie)
rain_base = 0
rain_scale = 5
ax.fill_between(
    x_fine * width_per_hour,
    rain_base,
    rain_base + rain_y * rain_scale,
    edgecolor='navy',
    facecolor='blue',
    linewidth=0,
    alpha=0.3    
)


# Temperaturkurve mit Farbverlauf aus Colormap 'turbo'
temp_base = 132
temp_scale = 2.5

# Farbnormalisierung basierend auf Temperatur (abhängig von jahreszeit)
monat = int(pd.to_datetime(df_1['Zeit'][0]).strftime("%m"))
if monat in [12, 1, 2]:  # Winter
    norm_temp = Normalize(vmin=-10, vmax=14)
elif monat in [3, 4, 5, 9, 10, 11]:  # Frühling und Herbst
    norm_temp = Normalize(vmin=-8.33, vmax=33.33)
elif monat in [6, 7, 8]:  # Sommer
    norm_temp = Normalize(vmin=-7.33, vmax=36)


# alte limits     norm_temp = Normalize(vmin=min(temp_y)*0.9, vmax=max(temp_y)*1.1)
    

cmap_temp = colormaps['rainbow']


# Segmentweise einfärben (wie bei Liniensegmentierung)
for i in range(len(x_fine) - 1):
    x_segment = [x_fine[i] * width_per_hour, x_fine[i+1] * width_per_hour]
    y_segment = [temp_base + temp_y[i] * temp_scale, temp_base + temp_y[i+1] * temp_scale]

    color = cmap_temp(norm_temp((temp_y[i] + temp_y[i+1]) / 2))

    ax.fill_between(
        x_segment,
        [temp_base, temp_base],
        y_segment,
        facecolor=color,
        edgecolor=color,
        linewidth=0,
        alpha=0.5
    )


ax.set_ylim((0,220))
ax.plot([x_fine[0], x_fine[-1]], [220, 220], alpha=.1)
ax.plot([x_fine[0], x_fine[-1]], [0, 0], alpha=.1)
# In-Memory-Speicherung
buf = BytesIO()
plt.savefig(buf, format='PNG', pad_inches=0, transparent=True)  # Kein bbox_inches hier
plt.close()
buf.seek(0)
curve_img = Image.open(buf).convert("RGBA")

# Automatisch alle außen liegenden transparenten Pixel abschneiden
bbox = curve_img.getbbox()
curve_img = curve_img.crop(bbox)


# Zielgröße berechnen
target_width = width  # gleiche Breite wie Basisbild
target_height = height // 2  # halbe Höhe

# Resize auf Zielgröße
curve_img = curve_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

# Basisbild erstellen
base_img = Image.new("RGBA", (width, height), "lightgrey")

# Position: 20% der Basisbildhöhe von oben
paste_y = int(height * 0.2)

# Bild einfügen
base_img.paste(curve_img, (0, paste_y), curve_img)

# Zeichnen vorbereiten
draw = ImageDraw.Draw(base_img)


# Font laden
# FONT_PATH_BOLD = BASE_DIR / "fonts" / "arialbd.ttf"
# FONT_PATH = BASE_DIR / "fonts" / "arial.ttf"
# font = ImageFont.truetype(FONT_PATH, size=18)  
# font_bold = ImageFont.truetype(FONT_PATH_BOLD, size=21)  
font = ImageFont.load_default()
font_bold = font

# Colormap für Wind
norm1 = Normalize(vmin=0, vmax=35)
colormap1 = colormaps['gist_heat_r']

norm2 = Normalize(vmin=0, vmax=50)
colormap2 = colormaps['Reds']



# Deutsche Wochentagskürzel
wochentage = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

# Vorherigen Tag speichern, um Wechsel zu erkennen (optional)
previous_day = None

# Icons laden
ARROW_PATH = BASE_DIR / "icons" / "right-arrow.png"
SUNRISE_PATH = BASE_DIR / "icons" / "sunrise.png"
SUNSET_PATH = BASE_DIR / "icons" / "sunset.png"
FOG_PATH = BASE_DIR / "icons" / "fog.png"
RAIN_PATH = BASE_DIR / "icons" / "rain.png"
THUNDERSTORM_PATH = BASE_DIR / "icons" / "thunderstorm.png"
icon_arrow = Image.open(ARROW_PATH).convert("RGBA")
icon_arrow = icon_arrow.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))


icon_sunrise = Image.open(SUNRISE_PATH).convert("RGBA")
icon_sunset = Image.open(SUNSET_PATH).convert("RGBA")
icon_sunrise = icon_sunrise.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_sunset = icon_sunset.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_sunrise_width, icon_sunrise_height = icon_sunrise.size
icon_sunset_width, icon_sunset_height = icon_sunset.size


icon_fog = Image.open(FOG_PATH)
icon_rain = Image.open(RAIN_PATH)
icon_thunderstorm = Image.open(THUNDERSTORM_PATH)
icon_fog = icon_fog.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_rain = icon_rain.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_thunderstorm = icon_thunderstorm.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_fog_width, icon_fog_heigt = icon_fog.size
icon_rain_width, icon_rain_height = icon_rain.size
icon_thunderstorm_width, icon_thunderstorm_height = icon_thunderstorm.size

# Ort definieren für sonnenaufgang
stadt = LocationInfo(name="Muenchen", region="Germany", timezone="Europe/Berlin", latitude=48.166144, longitude=11.658285)
s = sun(stadt.observer, date=date.today(), tzinfo=stadt.timezone)


def draw_filled_circle(percentage, size=33, background="rgba(0,0,0,0)", fill_color="darkgrey", outline_color="black"):
    # Create image and drawing context
    img = Image.new("RGBA", (size, size), background)
    draw = ImageDraw.Draw(img)

    # Define bounding box for the circle
    bbox = [0, 0, size-1, size-1]

    # Calculate angle
    start_angle = -90  # Start from top (12 o'clock)
    end_angle = start_angle + (percentage / 100) * 360

    # Draw filled arc (pieslice)
    draw.pieslice(bbox, start=start_angle, end=end_angle, fill=fill_color)

    # Optional: draw circle outline
    draw.ellipse(bbox, outline=outline_color)

    return img


for i, row in df_1.iterrows():
    x0 = i * width_per_hour
    

    # Wetter icons
    if row['ww_x'] in [45, 49]:      # Nebel warnung
        x_target = x0 + width_per_hour // 2
        y_target = height - int(height * 0.77)
        position = (x_target - icon_fog_width // 2, y_target - icon_fog_heigt // 2)
        base_img.paste(icon_fog, position, icon_fog)
    if row['ww_x'] in [81, 82]:      # mäßige und äußerst hefitge regenshauer
        x_target = x0 + width_per_hour // 2
        y_target = height - int(height * 0.77)
        position = (x_target - icon_rain_width // 2, y_target - icon_rain_height // 2)
        base_img.paste(icon_rain, position, icon_rain)
    if row['ww_x'] == 95:      # Gewitter
        x_target = x0 + width_per_hour // 2
        y_target = height - int(height * 0.77)
        position = (x_target - icon_thunderstorm_width // 2, y_target - icon_thunderstorm_height // 2)
        base_img.paste(icon_thunderstorm, position, icon_thunderstorm)
    
    
    zeit = pd.to_datetime(row['Zeit'])  # Falls Zeit als String vorliegt
    stunde = zeit.hour

    # Wenn Stunde 00 ist → Wochentagskürzel anzeigen und sonnenauf unduntergang
    if stunde == 0:
        label = wochentage[zeit.weekday()]
    elif stunde == int(s['sunrise'].strftime('%H')):
        draw.text((x0 + 3, height - (height*0.93)), f"{s['sunrise'].strftime('%H:%M')}", font=font, fill="rgb(236, 87, 0)")
        x_target = x0 + width_per_hour // 2
        if row['ww_x'] in [45, 49, 81, 82, 95]:
            y_target = height - int(height * 0.77) + icon_fog_heigt + 2
        else:
            y_target = height - int(height * 0.77)
        position = (x_target - icon_sunrise_width // 2, y_target - icon_sunrise_height // 2)
        base_img.paste(icon_sunrise, position, icon_sunrise)
        label = f"{stunde:02d}h"
    elif stunde == int(s['sunset'].strftime('%H')):
        draw.text((x0 + 3, height - (height*0.93)), f"{s['sunset'].strftime('%H:%M')}", font=font, fill="rgb(236, 87, 0)")
        x_target = x0 + width_per_hour // 2
        if row['ww_x'] in [45, 49, 81, 82, 95]:
            y_target = height - int(height * 0.77) + icon_fog_heigt + 2
        else:
            y_target = height - int(height * 0.77)
        position = (x_target - icon_sunset_width // 2, y_target - icon_sunset_height // 2)
        base_img.paste(icon_sunset, position, icon_sunset)
        label = f"{stunde:02d}h"
    else:
        label = f"{stunde:02d}h"

    # Uhrzeit oder Wochentag zeichnen
    draw.text((x0 + 8, height - (height*0.98)), label, font=font_bold, fill="navy")

    # Temperatur (Zahl)
    if row['TTT_x'] == df_1['TTT_x'].max():
        draw.text((x0 + 10, height - (height*0.66)), f"{row['TTT_x']}°", font=font_bold, fill="rgb(219, 11, 11)")
    elif row['TTT_x'] == df_1['TTT_x'].min():
        draw.text((x0 + 10, height - (height*0.66)), f"{row['TTT_x']}°", font=font_bold, fill="rgb(13, 27, 181)")
    else:
        draw.text((x0 + 10, height - (height*0.66)), f"{row['TTT_x']}°", font=font_bold, fill="black")
    
    # Regendaten (Zahl)
    if row['RR1c_x'] != 0:
        draw.text((x0 + 11, height - (height*0.50)), f"{row['RR1c_x']}", font=font_bold, fill="black")
    if row['RR1c_x'] != 0 and row['DRR1'] != 0:
        draw.text((x0 + 14, height - (height*0.45)), f"{int(row['DRR1']/60)}", font=font_bold, fill="black")
    if row['RR1c_x'] != 0 and row['DRR1'] != 0:
        rain_intensity = (row['RR1c_x']/row['DRR1'])*3600
        if rain_intensity < 2:
            color = "#6dc6f7"  
        elif rain_intensity < 7:
            color = "#1f78b4"  
        elif rain_intensity < 15:
            color = "#33a02c"  
        elif rain_intensity < 25:
            color = "#f9301a"  
        else:
            color = "#b20003"  
        draw.text((x0 + 14, height - (height*0.40)), f"{round(rain_intensity)}", font=font_bold, fill=color)
    if row['wwP'] >= 10:
        draw.text((x0 + 6, height - (height*0.35)), f"{int(row['wwP'])}%", font=font_bold, fill="black")
    
    # # Wind-Kästchen average farbig 
    wind_color = tuple((np.array(colormap1(norm1(row['FF_x']))[:3]) * 255).astype(int))
    draw.rectangle([x0, height - (height*0.3), x0 + width_per_hour, height - (height*0.2)], fill=wind_color)
    draw.text((x0 + 14, height - (height*0.27)), f"{row['FF_x']}", font=font_bold, fill="lightgrey")

    # Wind max 
    wind_color = tuple((np.array(colormap2(norm2(row['FX1_x']))[:3]) * 255).astype(int))
    draw.rectangle([x0, height - (height*0.2), x0 + width_per_hour, height - (height*0.1)], fill=wind_color)
    draw.text((x0 + 14, height - (height*0.17)), f"{row['FX1_x']}", font=font_bold, fill="black")
    
    
    # Windrichtungspfeil (aus u/v)
    wind_dir_deg = row['DD_x']
    wind_dir_deg_corrected = wind_dir_deg + 90      # Icon für windrichtung zeigt ursprünglich nach rechts (Osten)
    
    rotated_icon_arrow = icon_arrow.rotate(wind_dir_deg_corrected, expand=True)        # expand=True sorgt dafür, dass nichts abgeschnitten wird
    rotated_icon_arrow_width, rotated_icon_arrow_height = rotated_icon_arrow.size      # der mittelpunkt des rotierten arrow stimmt nicht mit dem des unrotierten überein. deshalb muss es hier bestimmt werden
    
    x_target = x0 + width_per_hour // 2
    y_target = height - int(height * 0.05)
    position = (x_target - rotated_icon_arrow_width // 2, y_target - rotated_icon_arrow_width // 2)
    
    base_img.paste(rotated_icon_arrow, position, rotated_icon_arrow)
    

    # Linien zu besseren zuordnung
    draw.line([x0, height, x0, 0], fill='grey', width=0)
    
    
    # Wolkenbedeckung
    img = draw_filled_circle(row['Neff_x'], size=38)
    x_target = x0 + width_per_hour // 2
    y_target = height - int(height * 0.85)
    position = (x_target - img.size[0] // 2, y_target - img.size[1] // 2)
    base_img.paste(img, position, img)
    

    # Sichtweite ? parameter setzten 
    gut = False
    sehr_gut = False
    if 90000 <= row['VV_x'] < 120000:
        gut = True
        draw.circle((x0 + width_per_hour // 2, height - (height*0.85)), radius=5, fill="rgb(236, 87, 0)")
    if 120000 <= row['VV_x']:
        sehr_gut = True
        draw.circle((x0 + width_per_hour // 2, height - (height*0.85)), radius=5, fill="rgb(255,0,0)")
            

if gut:
    draw.text((x0, height - (height*0.93)), "Gute Sicht", font=font_bold, fill="rgb(236, 87, 0)")
    
if sehr_gut:
    draw.text((x0, height - (height*0.93)), "Sehr gute Sicht!", font=font_bold, fill="rgb(255,0,0)")
    

base_img.save(BASE_DIR / "erste reihe.png")

# zweites bild generieren
anzahl_std = len(df_2) - 1

# Bilddimensionen
width_per_hour = 50 # muss angepasst werden auf 25 wenn anstatt von 24 48 stunden gezeigt werden sollen
width = width_per_hour * len(df_2)
height = int((width/360) * 188)
dpi = 150

# Interpolation vorbereiten
x = list(range(0, anzahl_std + 1))
x_fine = np.linspace(min(x), max(x), 500)

# Temperaturkurve interpolieren
temp_interp = interp1d(x, df_2['TTT_x'], kind='cubic')
temp_y = temp_interp(x_fine)

# Regenkurve interpolieren mit PchipInterpolator
rain_interp = PchipInterpolator(x, df_2['RR1c_x'])
rain_y = rain_interp(x_fine)


# Matplotlib-Zeichenfläche
fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
ax.axis('off')
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)


# Regenfläche (nach oben zeigend von Basislinie)
rain_base = 0
rain_scale = 5
ax.fill_between(
    x_fine * width_per_hour,
    rain_base,
    rain_base + rain_y * rain_scale,
    edgecolor='navy',
    facecolor='blue',
    linewidth=0,
    alpha=0.3    
)


# Temperaturkurve mit Farbverlauf aus Colormap 'turbo'
temp_base = 132
temp_scale = 2.5

# Farbnormalisierung basierend auf Temperatur (abhängig von jahreszeit)
monat = int(pd.to_datetime(df_2['Zeit'][0]).strftime("%m"))
if monat in [12, 1, 2]:  # Winter
    norm_temp = Normalize(vmin=-10, vmax=14)
elif monat in [3, 4, 5, 9, 10, 11]:  # Frühling und Herbst
    norm_temp = Normalize(vmin=-8.33, vmax=33.33)
elif monat in [6, 7, 8]:  # Sommer
    norm_temp = Normalize(vmin=-7.33, vmax=36)


# alte limits     norm_temp = Normalize(vmin=min(temp_y)*0.9, vmax=max(temp_y)*1.1)
    

cmap_temp = colormaps['rainbow']


# Segmentweise einfärben (wie bei Liniensegmentierung)
for i in range(len(x_fine) - 1):
    x_segment = [x_fine[i] * width_per_hour, x_fine[i+1] * width_per_hour]
    y_segment = [temp_base + temp_y[i] * temp_scale, temp_base + temp_y[i+1] * temp_scale]

    color = cmap_temp(norm_temp((temp_y[i] + temp_y[i+1]) / 2))

    ax.fill_between(
        x_segment,
        [temp_base, temp_base],
        y_segment,
        facecolor=color,
        edgecolor=color,
        linewidth=0,
        alpha=0.5
    )


ax.set_ylim((0,220))
ax.plot([x_fine[0], x_fine[-1]], [220, 220], alpha=.1)
ax.plot([x_fine[0], x_fine[-1]], [0, 0], alpha=.1)
# In-Memory-Speicherung
buf = BytesIO()
plt.savefig(buf, format='PNG', pad_inches=0, transparent=True)  # Kein bbox_inches hier
plt.close()
buf.seek(0)
curve_img = Image.open(buf).convert("RGBA")

# Automatisch alle außen liegenden transparenten Pixel abschneiden
bbox = curve_img.getbbox()
curve_img = curve_img.crop(bbox)


# Zielgröße berechnen
target_width = width  # gleiche Breite wie Basisbild
target_height = height // 2  # halbe Höhe

# Resize auf Zielgröße
curve_img = curve_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

# Basisbild erstellen
base_img = Image.new("RGBA", (width, height), "lightgrey")

# Position: 20% der Basisbildhöhe von oben
paste_y = int(height * 0.2)

# Bild einfügen
base_img.paste(curve_img, (0, paste_y), curve_img)

# Zeichnen vorbereiten
draw = ImageDraw.Draw(base_img)


# Font laden
# FONT_PATH_BOLD = BASE_DIR / "fonts" / "arialbd.ttf"
# FONT_PATH = BASE_DIR / "fonts" / "arial.ttf"
# font = ImageFont.truetype(FONT_PATH, size=18)  
# font_bold = ImageFont.truetype(FONT_PATH_BOLD, size=21)  
font = ImageFont.load_default()
font_bold = font

# Colormap für Wind
norm1 = Normalize(vmin=0, vmax=35)
colormap1 = colormaps['gist_heat_r']

norm2 = Normalize(vmin=0, vmax=50)
colormap2 = colormaps['Reds']



# Deutsche Wochentagskürzel
wochentage = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

# Vorherigen Tag speichern, um Wechsel zu erkennen (optional)
previous_day = None

# Icons laden
ARROW_PATH = BASE_DIR / "icons" / "right-arrow.png"
SUNRISE_PATH = BASE_DIR / "icons" / "sunrise.png"
SUNSET_PATH = BASE_DIR / "icons" / "sunset.png"
FOG_PATH = BASE_DIR / "icons" / "fog.png"
RAIN_PATH = BASE_DIR / "icons" / "rain.png"
THUNDERSTORM_PATH = BASE_DIR / "icons" / "thunderstorm.png"
FONT_PATH_BOLD = BASE_DIR / "fonts" / "arialbd.ttf"
FONT_PATH = BASE_DIR / "fonts" / "arial.ttf"
icon_arrow = Image.open(ARROW_PATH).convert("RGBA")
icon_arrow = icon_arrow.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))


icon_sunrise = Image.open(SUNRISE_PATH).convert("RGBA")
icon_sunset = Image.open(SUNSET_PATH).convert("RGBA")
icon_sunrise = icon_sunrise.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_sunset = icon_sunset.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_sunrise_width, icon_sunrise_height = icon_sunrise.size
icon_sunset_width, icon_sunset_height = icon_sunset.size


icon_fog = Image.open(FOG_PATH)
icon_rain = Image.open(RAIN_PATH)
icon_thunderstorm = Image.open(THUNDERSTORM_PATH)
icon_fog = icon_fog.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_rain = icon_rain.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_thunderstorm = icon_thunderstorm.resize((int(width_per_hour*0.66), int(height*0.1*0.66)))
icon_fog_width, icon_fog_heigt = icon_fog.size
icon_rain_width, icon_rain_height = icon_rain.size
icon_thunderstorm_width, icon_thunderstorm_height = icon_thunderstorm.size

# Ort definieren für sonnenaufgang
stadt = LocationInfo(name="Muenchen", region="Germany", timezone="Europe/Berlin", latitude=48.166144, longitude=11.658285)
s = sun(stadt.observer, date=date.today(), tzinfo=stadt.timezone)


def draw_filled_circle(percentage, size=33, background="rgba(0,0,0,0)", fill_color="darkgrey", outline_color="black"):
    # Create image and drawing context
    img = Image.new("RGBA", (size, size), background)
    draw = ImageDraw.Draw(img)

    # Define bounding box for the circle
    bbox = [0, 0, size-1, size-1]

    # Calculate angle
    start_angle = -90  # Start from top (12 o'clock)
    end_angle = start_angle + (percentage / 100) * 360

    # Draw filled arc (pieslice)
    draw.pieslice(bbox, start=start_angle, end=end_angle, fill=fill_color)

    # Optional: draw circle outline
    draw.ellipse(bbox, outline=outline_color)

    return img


for i, row in df_2.iterrows():
    x0 = i * width_per_hour
    

    # Wetter icons
    if row['ww_x'] in [45, 49]:      # Nebel warnung
        x_target = x0 + width_per_hour // 2
        y_target = height - int(height * 0.77)
        position = (x_target - icon_fog_width // 2, y_target - icon_fog_heigt // 2)
        base_img.paste(icon_fog, position, icon_fog)
    if row['ww_x'] in [81, 82]:      # mäßige und äußerst hefitge regenshauer
        x_target = x0 + width_per_hour // 2
        y_target = height - int(height * 0.77)
        position = (x_target - icon_rain_width // 2, y_target - icon_rain_height // 2)
        base_img.paste(icon_rain, position, icon_rain)
    if row['ww_x'] == 95:      # Gewitter
        x_target = x0 + width_per_hour // 2
        y_target = height - int(height * 0.77)
        position = (x_target - icon_thunderstorm_width // 2, y_target - icon_thunderstorm_height // 2)
        base_img.paste(icon_thunderstorm, position, icon_thunderstorm)
    
    
    zeit = pd.to_datetime(row['Zeit'])  # Falls Zeit als String vorliegt
    stunde = zeit.hour

    # Wenn Stunde 00 ist → Wochentagskürzel anzeigen und sonnenauf unduntergang
    if stunde == 0:
        label = wochentage[zeit.weekday()]
    elif stunde == int(s['sunrise'].strftime('%H')):
        draw.text((x0 + 3, height - (height*0.93)), f"{s['sunrise'].strftime('%H:%M')}", font=font, fill="rgb(236, 87, 0)")
        x_target = x0 + width_per_hour // 2
        if row['ww_x'] in [45, 49, 81, 82, 95]:
            y_target = height - int(height * 0.77) + icon_fog_heigt + 2
        else:
            y_target = height - int(height * 0.77)
        position = (x_target - icon_sunrise_width // 2, y_target - icon_sunrise_height // 2)
        base_img.paste(icon_sunrise, position, icon_sunrise)
        label = f"{stunde:02d}h"
    elif stunde == int(s['sunset'].strftime('%H')):
        draw.text((x0 + 3, height - (height*0.93)), f"{s['sunset'].strftime('%H:%M')}", font=font, fill="rgb(236, 87, 0)")
        x_target = x0 + width_per_hour // 2
        if row['ww_x'] in [45, 49, 81, 82, 95]:
            y_target = height - int(height * 0.77) + icon_fog_heigt + 2
        else:
            y_target = height - int(height * 0.77)
        position = (x_target - icon_sunset_width // 2, y_target - icon_sunset_height // 2)
        base_img.paste(icon_sunset, position, icon_sunset)
        label = f"{stunde:02d}h"
    else:
        label = f"{stunde:02d}h"

    # Uhrzeit oder Wochentag zeichnen
    draw.text((x0 + 8, height - (height*0.98)), label, font=font_bold, fill="navy")

    # Temperatur (Zahl)
    if row['TTT_x'] == df_2['TTT_x'].max():
        draw.text((x0 + 10, height - (height*0.66)), f"{row['TTT_x']}°", font=font_bold, fill="rgb(219, 11, 11)")
    elif row['TTT_x'] == df_2['TTT_x'].min():
        draw.text((x0 + 10, height - (height*0.66)), f"{row['TTT_x']}°", font=font_bold, fill="rgb(13, 27, 181)")
    else:
        draw.text((x0 + 10, height - (height*0.66)), f"{row['TTT_x']}°", font=font_bold, fill="black")
    
    # Regendaten (Zahl)
    if row['RR1c_x'] != 0:
        draw.text((x0 + 11, height - (height*0.50)), f"{row['RR1c_x']}", font=font_bold, fill="black")
    if row['RR1c_x'] != 0 and row['DRR1'] != 0:
        draw.text((x0 + 14, height - (height*0.45)), f"{int(row['DRR1']/60)}", font=font_bold, fill="black")
    if row['RR1c_x'] != 0 and row['DRR1'] != 0:
        rain_intensity = (row['RR1c_x']/row['DRR1'])*3600
        if rain_intensity < 2:
            color = "#6dc6f7"  
        elif rain_intensity < 7:
            color = "#1f78b4"  
        elif rain_intensity < 15:
            color = "#33a02c"  
        elif rain_intensity < 25:
            color = "#f9301a"  
        else:
            color = "#b20003"  
        draw.text((x0 + 14, height - (height*0.40)), f"{round(rain_intensity)}", font=font_bold, fill=color)
    if row['wwP'] >= 10:
        draw.text((x0 + 6, height - (height*0.35)), f"{int(row['wwP'])}%", font=font_bold, fill="black")
    
    # # Wind-Kästchen average farbig 
    wind_color = tuple((np.array(colormap1(norm1(row['FF_x']))[:3]) * 255).astype(int))
    draw.rectangle([x0, height - (height*0.3), x0 + width_per_hour, height - (height*0.2)], fill=wind_color)
    draw.text((x0 + 14, height - (height*0.27)), f"{row['FF_x']}", font=font_bold, fill="lightgrey")

    # Wind max 
    wind_color = tuple((np.array(colormap2(norm2(row['FX1_x']))[:3]) * 255).astype(int))
    draw.rectangle([x0, height - (height*0.2), x0 + width_per_hour, height - (height*0.1)], fill=wind_color)
    draw.text((x0 + 14, height - (height*0.17)), f"{row['FX1_x']}", font=font_bold, fill="black")
    
    
    # Windrichtungspfeil (aus u/v)
    wind_dir_deg = row['DD_x']
    wind_dir_deg_corrected = wind_dir_deg + 90      # Icon für windrichtung zeigt ursprünglich nach rechts (Osten)
    
    rotated_icon_arrow = icon_arrow.rotate(wind_dir_deg_corrected, expand=True)        # expand=True sorgt dafür, dass nichts abgeschnitten wird
    rotated_icon_arrow_width, rotated_icon_arrow_height = rotated_icon_arrow.size      # der mittelpunkt des rotierten arrow stimmt nicht mit dem des unrotierten überein. deshalb muss es hier bestimmt werden
    
    x_target = x0 + width_per_hour // 2
    y_target = height - int(height * 0.05)
    position = (x_target - rotated_icon_arrow_width // 2, y_target - rotated_icon_arrow_width // 2)
    
    base_img.paste(rotated_icon_arrow, position, rotated_icon_arrow)
    

    # Linien zu besseren zuordnung
    draw.line([x0, height, x0, 0], fill='grey', width=0)
    
    
    # Wolkenbedeckung
    img = draw_filled_circle(row['Neff_x'], size=38)
    x_target = x0 + width_per_hour // 2
    y_target = height - int(height * 0.85)
    position = (x_target - img.size[0] // 2, y_target - img.size[1] // 2)
    base_img.paste(img, position, img)
    

    # Sichtweite ? parameter setzten 
    gut = False
    sehr_gut = False
    if 90000 <= row['VV_x'] < 120000:
        gut = True
        draw.circle((x0 + width_per_hour // 2, height - (height*0.85)), radius=5, fill="rgb(236, 87, 0)")
    if 120000 <= row['VV_x']:
        sehr_gut = True
        draw.circle((x0 + width_per_hour // 2, height - (height*0.85)), radius=5, fill="rgb(255,0,0)")
            

if gut:
    draw.text((x0, height - (height*0.93)), "Gute Sicht", font=font_bold, fill="rgb(236, 87, 0)")
    
if sehr_gut:
    draw.text((x0, height - (height*0.93)), "Sehr gute Sicht!", font=font_bold, fill="rgb(255,0,0)")

base_img.save(BASE_DIR / "zweite reihe.png")


# Bilder laden
oberes_bild = Image.open(BASE_DIR / "erste reihe.png").convert("RGBA")
unteres_bild = Image.open(BASE_DIR / "zweite reihe.png").convert("RGBA")

# Breite = maximale Breite der beiden Bilder
gesamt_breite = max(oberes_bild.width, unteres_bild.width)
gesamt_hoehe = oberes_bild.height + unteres_bild.height

# Neues Bild erstellen mit genügend Platz
kombiniert = Image.new("RGBA", (gesamt_breite, gesamt_hoehe), (0, 0, 0, 0))

# Bilder einfügen
kombiniert.paste(oberes_bild, (0, 0))
kombiniert.paste(unteres_bild, (0, oberes_bild.height))

draw = ImageDraw.Draw(kombiniert)
draw.line([0, oberes_bild.height, gesamt_breite, oberes_bild.height], fill='black', width=5)




kombiniert.save(BASE_DIR / "Wettervorhersage large widget.png", format="PNG")

os.remove(BASE_DIR / "erste reihe.png")
os.remove(BASE_DIR / "zweite reihe.png")


os.remove(kmz_file_s)
os.remove(kmz_file_mosmix_l)