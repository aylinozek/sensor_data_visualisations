import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import openpyxl
import warnings
warnings.filterwarnings("ignore")

#--------------------------------------------------------------------------
# PATHS and PARTICIPANT SETTINGS (Below are placeholders, update accordingly)
#--------------------------------------------------------------------------
base_dir = "path/to/your/data"   #(stations.ipynb)
data_dir = "/path/to/data"       #(stations_cumulative.ipynb)
save_id = "P01"

hr_file = "hr.csv"
actlumus_file = "actlumus.txt"
hrv_file = "rr.csv"
hobo_file = "hobo.csv"
msr_file = "msr.csv"
iButton_file_chest = "iButtons_chest.csv"
iButton_file_hand = "iButtons_hand.csv"

actlumus_shift_min = 0
actlumus_shift_sec = 0

start = '00:00:00'
end = '08:00:00'

#--------------------------------------------------------------------------
# STATION TIMINGS and PARTICIPANT GROUPS (Below are dummy example values)
#--------------------------------------------------------------------------
S_TIMINGS_study_date_1 = {
    "S1": ("00:00:00", "00:04:00"), "S2": ("00:10:00", "00:14:00"),
    "S3": ("00:20:00", "00:24:00"), "S4": ("00:30:00", "00:34:00"),
    "S5": ("00:40:00", "00:44:00"), "S6": ("00:50:00", "00:54:00"),
    "S7": ("01:00:00", "01:04:00"), "S8": ("01:10:00", "01:14:00"),
}

S_TIMINGS = {"S_TIMINGS_EXAMPLE": S_TIMINGS_study_date_1}

groups = {
    "2000-01-01": (["P01", "P02"], "S_TIMINGS_EXAMPLE", (0, 0)),
    "2000-01-02": (["P03", "P04"], "S_TIMINGS_EXAMPLE", (0, 0)),
}

PARTICIPANT_MAP = {
    "P01": ("2000-01-01", S_TIMINGS_study_date_1),
    "P02": ("2000-01-01", S_TIMINGS_study_date_1),
}

#--------------------------------------------------------------------------
# VARIABLES and PLOT SETTINGS
#--------------------------------------------------------------------------
actlumus_cols_keep = ['DATE/TIME', 'LIGHT', 'MELANOPIC EDI', 'TEMPERATURE', 'IR LIGHT']
actlumus_variables = ['LIGHT', 'MELANOPIC EDI', 'TEMPERATURE', 'IR LIGHT']
actlumus_y_labels = ['Light', 'Melanopic EDI', 'Temperature', 'IR Light']

VARIABLES = ["hr", "rr", "light", "melanopic_edi", "actlumus_temp", "IR", "temp_hand", "temp_chest"]

var_labels = {
    "hr": "Heart Rate (bpm)",
    "rr": "RR Interval (ms)",
    "light": "Light (lux)",
    "melanopic_edi": "Melanopic EDI",
    "actlumus_temp": "Actlumus Temp",
    "IR": "IR",
    "temp_hand": "Hand Temperature (°C)",
    "temp_chest": "Chest Temperature (°C)",
}

cumulative_out = os.path.join(data_dir, "cumulative_plots")