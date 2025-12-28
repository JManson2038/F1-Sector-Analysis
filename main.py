
import os
import fastf1 as f1
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


os.makedirs('cache', exist_ok=True)
f1.Cache.enable_cache('cache')

TEAM_COLORS = {
    'Ferrari': '#FF2800',           # Red
    'Red Bull Racing': '#0600EF',   # Blue
    'Mercedes': '#00D2BE',          # Silver/Turquoise
    'McLaren': '#FF8700',           # Papaya Orange
    'Alpine': '#0090FF',            # Blue
    'Aston Martin': '#00665E',      # British Racing Green
    'Williams': '#005AFF',          # Blue
    'Cadillac': '#000000',          # Black
    'Haas F1 Team': '#FFFFFF',      # White/Red/Black (using white as base)
    'AlphaTauri': '#2B4562',        # Navy Blue
    'Sauber': '#52C41A',            # Green
    'RB': '#00362F',                # Dark Green (Red Bull's second team)
}
LINE_STYLES = ['-', '--']
SECTOR_MARKERS = ['o', 's', '^']\



session = f1.get_session(2025, 12, 'R')
session.load()

laps = session.laps
print(laps['Driver'].unique())
print(laps.columns)
print(laps['Team'].unique())
drivers =  ["HAM","NOR","VER"]

plt.figure(figsize=(12, 6))

team_driver_count = {}

for driver_code in drivers:
    driver_laps = laps[laps['Driver'] == driver_code]
    driver_laps = driver_laps.dropna(subset=['Sector1Time', 'Sector2Time', 'Sector3Time'])
    sector_times =[ driver_laps['Sector1Time'].dt.total_seconds(),
        driver_laps['Sector2Time'].dt.total_seconds(),
        driver_laps['Sector3Time'].dt.total_seconds()]
    
    lap_numbers = driver_laps['LapNumber']



    driver_team = driver_laps['Team'].iloc[0]
    driver_color = TEAM_COLORS.get(driver_team)

    count = team_driver_count.get(driver_team,0)
    line_style = LINE_STYLES[count % len(LINE_STYLES)]
    team_driver_count[driver_team] = count + 1


    for i, sector_times in enumerate(sector_times):
        fastest_idx = sector_times.idxmin()
        fastest_lap = lap_numbers.loc[fastest_idx]
        fastest_time =sector_times.loc[fastest_idx]
        plt.scatter(
        fastest_lap,
        fastest_time,
        s=120,
        edgecolors='black',
        linewidths=1.5,
        color=driver_color,
        zorder=5
    )

        plt.plot(
        lap_numbers, sector_times, marker = SECTOR_MARKERS[i], linestyle = line_style, color = driver_color ,  label=f"{driver_code} - Sector {i+1}"
     )
    pit_laps = driver_laps[driver_laps['PitInTime'].notna()]['LapNumber']

    for pit_lap in pit_laps:
     plt.axvline(
        pit_lap,
        color=driver_color,
        linestyle=':',
        alpha=0.4
    )



plt.xlabel('Lap Number')
plt.ylabel('Sector Time (s)')
plt.title('Sector Times by Driver')
plt.grid(True)
plt.legend()
plt.show()
