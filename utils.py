import sys
import os
sys.path.append(os.path.abspath(".."))

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates

from config import *

#--------------------------------------------------------------------------
# FILE DETECT
#--------------------------------------------------------------------------

def find_file(folder, pattern_keywords, extension=None, exclude_keywords=None):
    """
    Search folder (and one level of subfolders) for a file whose name
    contains ALL pattern_keywords (case-insensitive). Returns first match or None.
    """
    exclude_keywords = exclude_keywords or []
    search_dirs = [folder] + [
        os.path.join(folder, d)
        for d in os.listdir(folder)
        if os.path.isdir(os.path.join(folder, d))
    ]
    for search_dir in search_dirs:
        try:
            candidates = os.listdir(search_dir)
        except PermissionError:
            continue
        for fname in candidates:
            fname_upper = fname.upper()
            if extension and not fname_upper.endswith(extension.upper()):
                continue
            if all(kw.upper() in fname_upper for kw in pattern_keywords):
                if not any(ex.upper() in fname_upper for ex in exclude_keywords):
                    return os.path.join(search_dir, fname)
    return None

def detect_files(pid, meta, datadir):
    """
    Detect all data files for a participant. Returns a dict of paths.
    """
    folder = os.path.join(datadir, pid)
    date_full = meta["date"].replace("-", "")

    files = {}

    # HR file: contains participant ID + date, ends in .CSV, does NOT contain _RR
    files["hr"] = find_file(folder,
                            pattern_keywords=[pid, date_full],
                            extension=".CSV",
                            exclude_keywords=["_RR"])
    # Fallback: try short date
    if not files["hr"]:
        files["hr"] = find_file(folder,
                                pattern_keywords=[pid],
                                extension=".CSV",
                                exclude_keywords=["_RR"])

    # HRV/RR file: contains participant ID + _RR
    files["hrv"] = find_file(folder,
                             pattern_keywords=[pid, "_RR"],
                             extension=".CSV")
    if not files["hrv"]:
        files["hrv"] = find_file(folder,
                                 pattern_keywords=["_RR"],
                                 extension=".CSV")

    # ActLumus file: contains "ActLumus" or "Actlumus"
    files["actlumus"] = find_file(folder,
                                  pattern_keywords=["actlumus"],
                                  extension=".txt")

    # HOBO file: in HOBO/ subfolder or contains "HOBO"/"BLE"
    files["hobo"] = find_file(folder,
                              pattern_keywords=["BLE"],
                              extension=".csv")
    if not files["hobo"]:
        files["hobo"] = find_file(folder,
                                  pattern_keywords=["HOBO"],
                                  extension=".csv")

    # MSR file: contains "MSR"
    files["msr"] = find_file(folder,
                             pattern_keywords=["MSR"],
                             extension=".csv")

    # iButton hand: in iButtons/ subfolder, filename contains "hand"
    files["ibutton_hand"] = find_file(folder,
                                      pattern_keywords=["hand"],
                                      extension=".csv")

    # iButton chest: in iButtons/ subfolder, filename contains "chest"
    files["ibutton_chest"] = find_file(folder,
                                       pattern_keywords=["chest"],
                                       extension=".csv")

    return files

#--------------------------------------------------------------------------
# HELPERS
#--------------------------------------------------------------------------
def get_actlumus_start(path):
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.startswith('#') and ';' in line:
                return i
    return 0

def get_ibutton_start(path):
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if line.strip() == "":
                return i + 2
    return 0

def shade_stations(ax, windows, color="silver", alpha=0.25):
    for start_t, end_t in windows:
        ax.axvspan(start_t, end_t, color=color, alpha=alpha)

def format_time_axis(ax, spine_linewidth=0.5):
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 10)))
    plt.xticks(rotation=45, ha='right')
    for spine in ax.spines.values():
        spine.set_linewidth(spine_linewidth)

def save_plot_pair(out_dir, base_name, save_png=True, save_pdf=True, dpi=400):
    os.makedirs(out_dir, exist_ok=True)
    if save_png:
        plt.savefig(
            os.path.join(out_dir, f"{base_name}.png"),
            dpi=dpi,
            bbox_inches="tight",
            facecolor="white"
        )
    if save_pdf:
        plt.savefig(
            os.path.join(out_dir, f"{base_name}.pdf"),
            bbox_inches="tight"
        )

#--------------------------------------------------------------------------
# DATA LOADERS
#--------------------------------------------------------------------------
def load_rr(pid, meta, detected):
    if not detected.get("hrv"):
        return None
    try:
        df = pd.read_csv(detected["hrv"])
        m = df.iloc[0]
        start_dt = pd.to_datetime(f"{m['Date']} {m['Start time']}", dayfirst=True)
        cols = df.iloc[1].tolist()
        clean = df.iloc[2:].copy()
        clean.columns = cols
        clean["Time"] = pd.to_timedelta(clean["Time"], errors="coerce")
        rr_col = next((c for c in clean.columns if "RR" in str(c).upper()), None)
        if not rr_col:
            return None
        clean["rr"] = pd.to_numeric(clean[rr_col], errors="coerce")
        clean["timestamp"] = start_dt + clean["Time"]
        clean = clean.dropna(subset=["timestamp", "rr"]).sort_values("timestamp")
        return clean.set_index("timestamp")["rr"]
    except Exception as e:
        print(f"[RR load error {pid}]: {e}")
        return None

def load_hr(path):
    if not path:
        return None
    try:
        # Polar files: Row 0 = Metadata, Row 1 = Headers
        df = pd.read_csv(path, low_memory=False)
        m = df.iloc[0]

        # Try to find date and time in the metadata row
        # Some Polar exports use 'Date' and 'Start time', others might use smth else
        date_val = m.get('Date') or m.get('date') or df.iloc[0, 1]
        time_val = m.get('Start time') or m.get('start time') or df.iloc[0, 2]

        start_dt = pd.to_datetime(f"{date_val} {time_val}", dayfirst=True)

        # Define headers from row 1
        cols = df.iloc[1].tolist()
        clean = df.iloc[2:].copy()
        clean.columns = cols

        # Time and Value column detection
        time_col = next((c for c in clean.columns if "TIME" in str(c).upper()), None)
        val_col = next((c for c in clean.columns if "HR" in str(c).upper() or "RR" in str(c).upper()), None)

        if not time_col or not val_col:
            return None

        clean["Time"] = pd.to_timedelta(clean[time_col], errors="coerce")
        clean["val"] = pd.to_numeric(clean[val_col], errors="coerce")
        clean["timestamp"] = start_dt + clean["Time"]

        return clean.dropna(subset=["timestamp", "val"]).set_index("timestamp")["val"]
    except Exception as e:
        print(f"[Polar error]: {e}")
        return None

def load_actlumus(path, meta, variable_name):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start_line = 0
        for i, line in enumerate(lines[:60]):
            if not line.startswith('#') and ';' in line:
                start_line = i
                break

        df = pd.read_csv(path, sep=';', header=0, skiprows=start_line, engine='python')
        df.columns = [c.strip().upper() for c in df.columns]

        # Date/Time column detection
        time_col = next((c for c in df.columns if "DATE" in c and "TIME" in c), None)
        if not time_col:
            return None

        df["timestamp"] = pd.to_datetime(df[time_col], errors="coerce")
        shift = pd.Timedelta(minutes=meta["actlumus_shift_min"], seconds=meta["actlumus_shift_sec"])
        df["timestamp"] -= shift

        variable_map = {
            "light": "LIGHT",
            "melanopic_edi": "MELANOPIC",
            "actlumus_temp": "TEMPERATURE",
            "IR": "IR"
        }

        target = variable_map.get(variable_name)
        actual_col = next((c for c in df.columns if target in c), None)

        if not actual_col:
            return None

        df["val"] = pd.to_numeric(df[actual_col], errors="coerce")
        return df.dropna(subset=["timestamp", "val"]).set_index("timestamp")["val"]
    except Exception as e:
        print(f"[ActLumus load error]: {e}")
        return None

def load_ibutton(path):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        skip = 0
        for i, line in enumerate(lines[:50]):
            if line.strip() == "":
                skip = i + 1
                break

        df = pd.read_csv(path, sep=',', header=None,
                         names=["Date", "Time", "Unit", "Value", "Decimal"],
                         skiprows=skip, engine='python')
        df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"], format="%d.%m.%y %H:%M:%S", errors="coerce")
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
        df["Decimal"] = pd.to_numeric(df["Decimal"], errors="coerce")
        df["val"] = df["Value"] + df["Decimal"] / 1000
        return df.dropna(subset=["timestamp", "val"]).set_index("timestamp")["val"]
    except Exception as e:
        print(f"[iButton load error]: {e}")
        return None

#--------------------------------------------------------------------------
# PREPROCESSING HEART RATE VARIABILITY DATA FOR CUMULATIVE GRAPHS
#--------------------------------------------------------------------------
def preprocess_rr(rr_series,
                   plausible_min=00, plausible_max=5000,
                   jump_threshold=00,
                   smooth_window=1):
    """
      1. Removes clearly implausible values (outside [plausible_min, plausible_max] ms)
      2. Interpolates sudden unrealistic jumps (> jump_threshold ms change)
      3. Apply rolling-mean smoothing for visualization

    Parameters
    plausible_min : lower bound in ms
    plausible_max: upper bound in ms
    jump_threshold: consecutive change threshold in ms
    smooth_window : rolling mean window size (set to 1 to skip)
    """

    # remove implausible values
    rr = rr_series.copy().astype(float)
    rr[(rr < plausible_min) | (rr > plausible_max)] = np.nan

    # detect and interpolate sudden jumps
    # A jump is flagged when the absolute value of the change from the previous sample exceeds jump_threshold ms.
    diff = rr.diff().abs()
    rr[diff > jump_threshold] = np.nan

    # Linear interpolation over NaNs (i.e. flagged jumps)
    rr = rr.interpolate(method="time", limit_direction="both", limit=10)
    rr = rr.dropna()

    # smoothing
    if smooth_window > 1:
        rr = rr.rolling(window=smooth_window, center=True, min_periods=1).mean()

    return rr