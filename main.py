
import os
import fastf1 as f1
from fastf1.core import Laps
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider

os.makedirs('cache', exist_ok=True)
f1.Cache.enable_cache('cache')
driver_teams = {}

TEAM_COLORS = {
    'Ferrari': '#FF2800',
    'Red Bull Racing': '#3671C6',
    'Mercedes': '#6CD3BF',
    'McLaren': '#FF8000',
    'Alpine': '#FF87BC',
    'Aston Martin': '#00665E',
    'Williams': '#005AFF',
    'Cadillac': '#000000',
    'Haas F1 Team':'#9C9FA2',
    'AlphaTauri': '#2B4562',
    'Kick Sauber': '#52C41A',
    'Racing Bulls': '#FDD900',
    'alfa romeo':'#972738'
}
LINE_STYLES = ['-', '--']
SECTOR_MARKERS = ['o', 's', '^']
FPS = 30 
SHOW_TRAILS = False

mode = input("Choose the mode: 'LAP' for lap times or 'SECTOR' for sector time: ").upper().strip()
if mode not in {"LAP", "SECTOR"}:
    print("Invalid mode")
    exit()
    
year = input("Enter the year: ")
round_number = input("Enter the Round number (1-24): ")
type_of_session = input("Enter the type of session (R, Q, P): ").upper()

if not year.isdigit():
    print("Invalid year")
    exit()
if not round_number.isdigit():
    print("Invalid round number")
    exit()
if type_of_session not in {"R", "Q", "P", "FP1", "FP2", "FP3", "SQ"}:
    print("Invalid session type")
    exit()

year = int(year)
round_number = int(round_number)
session = f1.get_session(year, round_number, type_of_session)
session.load()

laps = session.laps
drivers_code = ','.join(sorted(laps['Driver'].unique()))
print(f"Available driver codes: {drivers_code}")
drivers_input = input("Enter the drivers like this: 'HAM,NOR,VER' or 'ALL': ").upper()
if drivers_input == "ALL":
    drivers = sorted(laps["Driver"].unique().tolist())
    print(f"Using all drivers: {', '.join(drivers)}")
else:
    drivers = [d.strip() for d in drivers_input.split(",")]
    available = set(laps["Driver"].unique())
    if not all(d in available for d in drivers):
        print("Invalid driver code entered")
        print("Available drivers:", ", ".join(sorted(available)))
        exit()

REPLAY_MODE = input("Replay mode: 'FASTEST' or 'RACE': ").upper().strip()

if REPLAY_MODE not in {"FASTEST", "RACE"}:
    print("Invalid replay mode")
    exit()

# Collect telemetry for all drivers
telemetry_data = {}
for drv in drivers:
    drv_laps = laps.pick_driver(drv)
    tel_list = []
    offset = 0.0

    if REPLAY_MODE == "FASTEST":
        lap = drv_laps.pick_fastest()
        if lap is None:
            continue
        t = lap.get_telemetry().dropna(subset=["X", "Y", "Time"])
        t["t"] = t["Time"].dt.total_seconds()
        tel_list.append(t)
    else:
        for _, lap in drv_laps.iterlaps():
            try:
                t = lap.get_telemetry().dropna(subset=["X", "Y", "Time"])
            except:
                continue
            if t.empty:
                continue
            t["t"] = t["Time"].dt.total_seconds() + offset
            offset = t["t"].iloc[-1]
            tel_list.append(t)

    if not tel_list:
        continue
    tel = pd.concat(tel_list, ignore_index=True)
    tel["t"] -= tel["t"].iloc[0]
    tel["race_time"] = tel["t"]
    dx = tel["X"].diff()
    dy = tel["Y"].diff()
    tel["dist"] = (dx**2 + dy**2).pow(0.5).fillna(0).cumsum()

    # Lap detection
    lap_starts = [0.0]
    for i in range(1, len(tel)):
        if tel["t"].iloc[i] - tel["t"].iloc[i - 1] > 20:
            lap_starts.append(tel["t"].iloc[i])
    tel.attrs["lap_starts"] = lap_starts
    telemetry_data[drv] = tel

fig1, ax1 = plt.subplots(figsize=(10, 8))
ax1.set_title("F1 Lap Replay", fontsize=16, fontweight='bold', pad=20)
ax1.set_aspect('equal')
plt.subplots_adjust(bottom=0.25, right=0.75, left=0.1)

# Plot track reference
ref_driver = drivers[0]
ref_lap = laps.pick_driver(ref_driver).pick_fastest()
track_tel = ref_lap.get_telemetry().dropna(subset=["X", "Y"])
ax1.plot(track_tel["X"], track_tel["Y"], color="lightgray", lw=2, alpha=0.7, zorder=1)

# Driver points and lines
points, lines = {}, {}
for drv, tel in telemetry_data.items():
    team = laps.pick_driver(drv)["Team"].iloc[0]
    color = TEAM_COLORS.get(team, "#888888")
    points[drv], = ax1.plot([], [], "o", color=color, markersize=10, markeredgecolor='white', markeredgewidth=1.5, zorder=10)
    lines[drv], = ax1.plot([], [], color=color, lw=2, alpha=0.7)

ax1.set_xlim(track_tel["X"].min() - 20, track_tel["X"].max() + 20)
ax1.set_ylim(track_tel["Y"].min() - 20, track_tel["Y"].max() + 20)
ax1.axis('off')

# Lap counter - repositioned
lap_text = ax1.text(0.02, 0.98, "Lap 1", transform=ax1.transAxes, fontsize=16, 
                    fontweight='bold', bbox=dict(facecolor='white', alpha=0.9, 
                    edgecolor='black', linewidth=2, boxstyle='round,pad=0.5'))

# IMPROVED LEADERBOARD
leaderboard_ax = fig1.add_axes([0.76, 0.25, 0.23, 0.65])
leaderboard_ax.set_xlim(0, 1)
leaderboard_ax.set_ylim(0, 1)
leaderboard_ax.axis("off")

# Play/Pause & sliders
is_paused = False
manual_scrub = False

def toggle_play(event):
    global is_paused
    if is_paused:
        ani.event_source.start()
        play_button.label.set_text("Pause")
    else:
        ani.event_source.stop()
        play_button.label.set_text("Play")
    is_paused = not is_paused

play_ax = fig1.add_axes([0.1, 0.1, 0.15, 0.06])
play_button = Button(play_ax, "Pause")
play_button.on_clicked(toggle_play)

time_slider_ax = fig1.add_axes([0.35, 0.12, 0.35, 0.03])
time_slider = Slider(time_slider_ax, "Time", 0.0, max(t["t"].iloc[-1] for t in telemetry_data.values()), valinit=0.0)

speed_slider_ax = fig1.add_axes([0.35, 0.06, 0.35, 0.03])
speed_slider = Slider(speed_slider_ax, "Speed", 0.25, 3.0, valinit=1.0)

def on_scrub(val):
    global manual_scrub
    manual_scrub = True
    update(int((val - 0) * FPS))
    fig1.canvas.draw_idle()

time_slider.on_changed(on_scrub)

# IMPROVED LEADERBOARD UPDATE FUNCTION
def update_leaderboard(current_t):
    snapshots = []
    for drv, tel in telemetry_data.items():
        idx = min(tel["t"].searchsorted(current_t), len(tel)-1)
        laps_done = sum(current_t >= t for t in tel.attrs["lap_starts"])
        race_time = tel["race_time"].iloc[idx]
        dist = tel["dist"].iloc[idx]
        finished = current_t > tel["t"].iloc[-1]
        snapshots.append((drv, laps_done, race_time, dist, finished))

    # Sort: most laps first, then by distance covered
    snapshots.sort(key=lambda x: (-x[1], -x[3]))

    leader_laps, leader_dist = snapshots[0][1], snapshots[0][3]

    leaderboard_ax.clear()
    leaderboard_ax.set_xlim(0, 1)
    leaderboard_ax.set_ylim(0, 1)
    leaderboard_ax.axis("off")
    
    # Title with background
    title_bg = plt.Rectangle((0, 0.94), 1, 0.06, facecolor='black', 
                              edgecolor='white', linewidth=2, transform=leaderboard_ax.transAxes)
    leaderboard_ax.add_patch(title_bg)
    leaderboard_ax.text(0.5, 0.97, "LEADERBOARD", fontsize=13, fontweight="bold", 
                        color='white', ha='center', va='center', transform=leaderboard_ax.transAxes)
    
    num_drivers = len(snapshots)
    line_height = 0.85 / max(num_drivers, 1)
    
    for i, (drv, laps_done, race_time, dist, finished) in enumerate(snapshots):
        team = laps.pick_driver(drv)["Team"].iloc[0]
        color = TEAM_COLORS.get(team, "#888888")
        
        y_pos = 0.90 - (i * line_height)
        
        # Calculate gap
        if i == 0:
            gap_str = "LEADER"
            gap_color = 'gold'
        elif laps_done < leader_laps:
            laps_down = leader_laps - laps_done
            gap_str = f"+{laps_down}L" if laps_down == 1 else f"+{laps_down}L"
            gap_color = 'red'
        else:
            # Use distance-based gap for more accuracy
            gap_dist = leader_dist - dist
            # Approximate: 1 second ≈ 80 meters (adjust based on track)
            gap_seconds = gap_dist / 80.0
            gap_str = f"+{gap_seconds:.1f}s"
            gap_color = 'white'
        
        if finished and i != 0:
            gap_str = "DNF"
            gap_color = 'gray'
        
        # Background box for each position
        if i == 0:
            bg_color = 'gold'
            bg_alpha = 0.3
        elif i < 3:
            bg_color = 'silver'
            bg_alpha = 0.2
        else:
            bg_color = 'lightgray'
            bg_alpha = 0.1
        
        pos_box = plt.Rectangle((0.02, y_pos - line_height*0.4), 0.96, line_height*0.8, 
                                facecolor=bg_color, alpha=bg_alpha, 
                                edgecolor=color, linewidth=2,
                                transform=leaderboard_ax.transAxes)
        leaderboard_ax.add_patch(pos_box)
        
        # Position number
        leaderboard_ax.text(0.08, y_pos, f"{i+1}", fontsize=12, fontweight='bold', 
                           ha='center', va='center', transform=leaderboard_ax.transAxes,
                           bbox=dict(boxstyle='circle', facecolor=color, edgecolor='white', linewidth=1.5))
        
        # Driver code
        leaderboard_ax.text(0.25, y_pos, drv, fontsize=11, fontweight='bold', 
                           color=color, ha='left', va='center', transform=leaderboard_ax.transAxes)
        
        # Gap
        leaderboard_ax.text(0.90, y_pos, gap_str, fontsize=10, fontweight='bold',
                           color=gap_color, ha='right', va='center', 
                           transform=leaderboard_ax.transAxes,
                           bbox=dict(facecolor='black', alpha=0.7, 
                                   edgecolor=gap_color, linewidth=1, pad=2))

# Animation update
def update(frame):
    global manual_scrub
    if manual_scrub:
        current_t = time_slider.val
        manual_scrub = False
    else:
        current_t = frame / FPS * speed_slider.val
        time_slider.set_val(current_t)

    for drv, tel in telemetry_data.items():
        idx = min(tel["t"].searchsorted(current_t), len(tel)-1)
        x, y = tel.loc[idx, ["X", "Y"]]
        points[drv].set_data([x], [y])
        if SHOW_TRAILS:
            lines[drv].set_data(tel["X"][:idx], tel["Y"][:idx])

    update_leaderboard(current_t)

    current_lap = max(sum(current_t >= t for t in tel.attrs["lap_starts"]) for tel in telemetry_data.values())
    lap_text.set_text(f"Lap {current_lap}")

    return list(points.values()) + list(lines.values())

# Run animation
frames = int(max(t["t"].iloc[-1] for t in telemetry_data.values()) * FPS)
ani = FuncAnimation(fig1, update, frames=frames, interval=1000/FPS, blit=False)
plt.show()

# LAP/SECTOR COMPARISON PLOT
if drivers_input != "ALL":
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    team_driver_count = {}

    for driver in drivers:
        driver_laps = laps[laps['Driver'] == driver].dropna(
            subset=['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']
        )

        lap_numbers = driver_laps['LapNumber']
        driver_team = driver_laps['Team'].iloc[0]
        color = TEAM_COLORS.get(driver_team, '#888888')

        count = team_driver_count.get(driver_team, 0)
        linestyle = LINE_STYLES[count % len(LINE_STYLES)]
        team_driver_count[driver_team] = count + 1

        if mode == "LAP":
            lap_times = driver_laps['LapTime'].dt.total_seconds()
            ax2.plot(lap_numbers, lap_times, linestyle=linestyle, color=color, marker='o',
                     label=f"{driver} Lap Time")

            fastest_idx = lap_times.idxmin()
            ax2.scatter(lap_numbers.loc[fastest_idx], lap_times.loc[fastest_idx],
                        s=140, edgecolors='black', color=color, zorder=5)

        else:  # SECTOR MODE
            for i in range(3):
                sector_times = driver_laps[f'Sector{i+1}Time'].dt.total_seconds()
                ax2.plot(
                    lap_numbers,
                    sector_times,
                    marker=SECTOR_MARKERS[i],
                    linestyle=linestyle,
                    color=color,
                    label=f"{driver} Sector {i+1}"
                )

        # Pit stops
        pit_laps = driver_laps[driver_laps['PitInTime'].notna()]['LapNumber']
        for pit in pit_laps:
            ax2.axvline(pit, color=color, linestyle=':', alpha=0.4)

    ax2.set_xlabel("Lap Number")
    ax2.set_ylabel("Time (s)")
    ax2.set_title("Lap Time Comparison" if mode == "LAP" else "Sector Time Comparison")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    plt.show()





