"""
This script is used to create flows from a history of gate openings at Lake Lawtonka and Lake Ellsworth provided by the City of Lawton.
It reads the historic gate data from a Excel file, and computes the flow at each lake using the weir flow equation used by the City of Lawton.
A second Excel file is used for the rating curve, which provides the coefficient of discharge for different elevations.

FOR FLOW UNDER GATE : - Q = 2/3 * Sqrt( 2g ) * C * L * ( H1^(3/2) - H2^(3/2) ) [REFERENCE USBR 'DESIGN OF SMALL DAMS' PAGE 386]

Q = flow in cfs
g = acceleration due to gravity (32.2 ft/s^2)
C = coefficient of discharge (0.6 for a sharp-crested weir) [An elevation-Coefficient table is provided in the rating curve Excel file]
L = length of the gate opening in feet = 20' for both lakes.
H1 = Height of the Head = Lake elevation - Spillway Invert Elevation (ft) [Lake Lawtonka = 1,335.55 ft, Lake Ellsworth = 1,225.00 ft]
H2 = Height of the Head from the bottom to the top of the gate opening = H1 - d [gate openings are defined in the rating tables as column d] [ for Lawtonka vary from 0 to 10', for Ellsworth vary from 0 to 17']
H1 - H2 = Height of the Head from the top of the gate opening to the lake elevation

Lake Surface Elevation
─────────────────────────────────────────────────────────────────────────────────
|<------------- H1 (Total Head =  Lake Surface - Spillway Invert Elevation) --->|  
|                                                                               | 
|                                                                               |
|<------------- H1 - H2 (Head From top of Gate to Lake Surface)---------------->| 
|                            ┌──────────────┐                                   | 
|                            │  Gate Open   │                                   |  
|                            │  Height = d  │                                   |  
|                            └──────────────┘                                   |  
─────────────────────────────────────────────────────────────────────────────────
Spillway Invert Elevation
"""
# %%
import pandas as pd

#%%
# Read the historic gate data from an Excel file for each lake
gate_file = r"L:\2022\22W02330 - Lawton Stormwater MP\Correspondence\Incoming\City of Lawton\Reservoir Operations\Gate Operations Spreadsheet 2015-2025.xlsx"
lawtonka_gate_data = pd.read_excel(gate_file, sheet_name="Lawtonka", skiprows=1)
ellsworth_gate_data = pd.read_excel(gate_file, sheet_name="Ellsworth", skiprows=1)
# %%
# lawtonka_gate_data

# %%
# For the Gates column we have a header that just says "Gates", then has a seconda header row for each gate number.
# so we need to remove that "Gates" row just for those columns lawtonka columns: [4:12]
# and ells worth c olumns [4:19] and shift up.

# rename lawtonks columns[4:12] for lawtonka to match row 0, but only those columns hsould be renamed
lawtonka_gate_data.columns = lawtonka_gate_data.columns[:4].tolist() + \
    lawtonka_gate_data.iloc[0, 4:12].tolist() + lawtonka_gate_data.columns[12:].tolist()

# rename ellsworth columns[4:19] for ellsworth to match row 0, but only those columns should be renamed
ellsworth_gate_data.columns = ellsworth_gate_data.columns[:4].tolist() + \
    ellsworth_gate_data.iloc[0, 4:19].tolist() + ellsworth_gate_data.columns[19:].tolist()


# drop the last column for both dataframes by index.
lawtonka_gate_data = lawtonka_gate_data.iloc[:, :-1]
ellsworth_gate_data = ellsworth_gate_data.iloc[:, :-1]

# drop the first row for both dataframes, which is the header row we just used to rename the columns
lawtonka_gate_data = lawtonka_gate_data.iloc[1:, :]
ellsworth_gate_data = ellsworth_gate_data.iloc[1:, :]

# drop any row where the Date column is just a Year YYYY instead of YYYY-MM-DD
lawtonka_gate_data = lawtonka_gate_data[~lawtonka_gate_data['Date'].astype(str).str.match(r'^\d{4}$')]
ellsworth_gate_data = ellsworth_gate_data[~ellsworth_gate_data['Date'].astype(str).str.match(r'^\d{4}$')]

# where there are missing values in the Date column, we will fill them with the previous value
lawtonka_gate_data['Date'] = lawtonka_gate_data['Date'].fillna(method='ffill')
ellsworth_gate_data['Date'] = ellsworth_gate_data['Date'].fillna(method='ffill')


# any rows that are missing in both the Time and Lake Elevation columns will be dropped
lawtonka_gate_data = lawtonka_gate_data.dropna(subset=['Time', 'Lake Elevation'])
ellsworth_gate_data = ellsworth_gate_data.dropna(subset=['Time', 'Lake Elevation'])

# reformat the data columns to datetime
lawtonka_gate_data['Date'] = pd.to_datetime(lawtonka_gate_data['Date'], errors='coerce')
ellsworth_gate_data['Date'] = pd.to_datetime(ellsworth_gate_data['Date'], errors='coerce')

lawtonka_gate_data
# %%
import re
def normalize_time_string(time_str):
    """
    Normalize various time string formats to HH:MM:SS (24-hour) format.
    Handles:
      - '123' -> '1:23:00'
      - '1234' -> '12:34:00'
      - '12345' -> '12:34:5'
      - '1:23' -> '01:23:00'
      - '12:34' -> '12:34:00'
      - '1:24A'/'1:24P' -> '01:24:00'/'13:24:00'
      - already in HH:MM:SS or similar, returns as is
    """
    if pd.isna(time_str):
        return time_str
    s = str(time_str).strip().upper()
    # Handle AM/PM like '1:24A' or '1:24P'
    ampm_match = re.match(r'^(\d{1,2}):(\d{2})([AP])$', s)
    if ampm_match:
        hour, minute, ap = ampm_match.groups()
        hour = int(hour)
        if ap == 'P' and hour != 12:
            hour += 12
        elif ap == 'A' and hour == 12:
            hour = 0
        return f"{hour:02}:{minute}:00"
    # Handle 'H:MM' or 'HH:MM'
    hmm_match = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if hmm_match:
        hour, minute = hmm_match.groups()
        return f"{int(hour):02}:{minute}:00"
    # Handle 'HHMM' or 'HMM'
    if s.isdigit():
        if len(s) == 3:  # '123' -> '1:23:00'
            return f"{int(s[0]):02}:{s[1:]}:00"
        elif len(s) == 4:  # '1234' -> '12:34:00'
            return f"{s[:2]}:{s[2:]}:00"
        elif len(s) == 5:  # '12345' -> '12:34:5'
            return f"{s[:2]}:{s[2:4]}:{s[4:]}"
    # Already in HH:MM:SS or unknown, return as is
    return s

# Apply the normalization to the Time column
lawtonka_gate_data['Time'] = lawtonka_gate_data['Time'].apply(normalize_time_string)
ellsworth_gate_data['Time'] = ellsworth_gate_data['Time'].apply(normalize_time_string)

lawtonka_gate_data
# %%


# reformat the time columns to datetime
from dateutil import parser

def parse_time(val):
    try:
        return parser.parse(str(val)).time()
    except Exception:
        return pd.NaT

lawtonka_gate_data['Time'] = lawtonka_gate_data['Time'].apply(parse_time)
ellsworth_gate_data['Time'] = ellsworth_gate_data['Time'].apply(parse_time)

# any rows that are missing in both the Time and Lake Elevation columns will be dropped
lawtonka_gate_data = lawtonka_gate_data.dropna(subset=['Time', 'Lake Elevation'])
ellsworth_gate_data = ellsworth_gate_data.dropna(subset=['Time', 'Lake Elevation'])

# replace the time values in the Date column with the alue from the Time column.
lawtonka_gate_data['Date'] = lawtonka_gate_data['Date'].astype(str) + ' ' + lawtonka_gate_data['Time'].astype(str)
ellsworth_gate_data['Date'] = ellsworth_gate_data['Date'].astype(str) + ' ' + ellsworth_gate_data['Time'].astype(str)

# drop the Time and the 4th column from both dataframes
# lawtonka_gate_data = lawtonka_gate_data.drop(columns=['Time', lawtonka_gate_data.columns[3]])
# ellsworth_gate_data = ellsworth_gate_data.drop(columns=['Time', ellsworth_gate_data.columns[3]])

# for the gate columns we need to convert the values to numeric, and convert from inches to feet.
# first ensure any missing values are set to 0
lawtonka_gate_data.iloc[:, 2:] = lawtonka_gate_data.iloc[:, 2:].fillna(0)
ellsworth_gate_data.iloc[:, 2:] = ellsworth_gate_data.iloc[:, 2:].fillna(0)
# then convert the values to numeric, and convert from inches to feet
lawtonka_gate_data.iloc[:, 2:] = lawtonka_gate_data.iloc[:, 2:].replace(r'"', '', regex=True)
lawtonka_gate_data.iloc[:, 2:] = lawtonka_gate_data.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0) / 12.0
ellsworth_gate_data.iloc[:, 2:] = ellsworth_gate_data.iloc[:, 2:].replace(r'"', '', regex=True)
ellsworth_gate_data.iloc[:, 2:] = ellsworth_gate_data.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0) / 12.0

# round the gate columns to 2 decimal places
lawtonka_gate_data.iloc[:, 2:] = lawtonka_gate_data.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0).round(2)
ellsworth_gate_data.iloc[:, 2:] = ellsworth_gate_data.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0).round(2)

lawtonka_gate_data
# ellsworth_gate_data

# %%
# for each gate column, we need to compute the flow and sum the flows for each gage to a total flow column.
# The flow is computed using the weir flow equation:
# FOR FLOW UNDER GATE : - Q = 2/3 * Sqrt( 2g ) * C * L * ( H1^(3/2) - H2^(3/2) ) [REFERENCE USBR 'DESIGN OF SMALL DAMS' PAGE 386]

# Q = flow in cfs
# g = acceleration due to gravity (32.2 ft/s^2)
# C = coefficient of discharge (0.6 for a sharp-crested weir) [An elevation-Coefficient table is provided in the rating curve Excel file]
# L = length of the gate opening in feet = 20' for both lakes.
# H1 = Height of the Head = Lake elevation - Spillway Invert Elevation (ft) [Lake Lawtonka = 1,335.55 ft, Lake Ellsworth = 1,225.00 ft]
# H2 = Height of the Head from the bottom to the top of the gate opening = H1 - d [gate openings are defined in the rating tables as column d] [ for Lawtonka vary from 0 to 10', for Ellsworth vary from 0 to 17']
# H1 - H2 = Height of the Head from the top of the gate opening to the lake elevation

# Open the rating curve Excel file for each lake
rating_curve_file = r"L:\2022\22W02330 - Lawton Stormwater MP\Correspondence\Incoming\City of Lawton\Reservoir Operations\#LAKE DISCHARGE CALCULATOR.xlsx"
lawtonka_rating_curve = pd.read_excel(rating_curve_file, sheet_name="LAWTONKA DISCHARGE RATES", skiprows=12)
ellsworth_rating_curve = pd.read_excel(rating_curve_file, sheet_name="ELLSWORTH DISCHARGE RATES", skiprows=12)

# round the 'd' column to 2 decimal places for consistency
lawtonka_rating_curve['d'] = pd.to_numeric(lawtonka_rating_curve['d'], errors='coerce').round(2)
ellsworth_rating_curve['d'] = pd.to_numeric(ellsworth_rating_curve['d'], errors='coerce').round(2)

# ensure lake elevation columns are numeric
lawtonka_gate_data['Lake Elevation'] = pd.to_numeric(lawtonka_gate_data['Lake Elevation'], errors='coerce')
ellsworth_gate_data['Lake Elevation'] = pd.to_numeric(ellsworth_gate_data['Lake Elevation'], errors='coerce')

lawtonka_rating_curve

# %%
# for each gate column value, look up that valuein the'd' column of the rating curve, and get the corresponding 'C',  value.
def get_coefficient_of_discharge(gate_opening, rating_curve):
    # Find the row in the rating curve where 'd' is equal to the gate opening.
    row = rating_curve[rating_curve['d'] == gate_opening]
    if row.empty:
        # Find the closest value in 'd' if exact match is not found
        # Drop NaN values in 'd' before finding the closest index
        valid_d = rating_curve['d'].dropna()
        closest_idx = (valid_d - gate_opening).abs().idxmin()
        closest_d = rating_curve.loc[closest_idx, 'd']
        print(f"Gate opening {gate_opening} not found. Using closest d value: {closest_d}")
        row = rating_curve.loc[[closest_idx]]
    if not row.empty:
        return row['C'].values[0]  # Return the coefficient of discharge
    else:
        raise ValueError(f"Gate opening {gate_opening} not found in rating curve.")
# Function to calculate flow for a single gate opening
def calculate_flow(gate_opening, lake_elevation, rating_curve):
    g = 32.2  # acceleration due to gravity in ft/s^2
    C = get_coefficient_of_discharge(gate_opening, rating_curve)  # Coefficient of discharge from rating curve
    L = 20.0  # Length of the gate opening in feet
    H1 = lake_elevation - (1335.55 if 'Lawtonka' in rating_curve.name else 1225.00)  # Height of the head
    H2 = H1 - gate_opening  # Height of the head from the bottom to the top of the gate opening
    if H2 < 0:
        return 0.0  # If H2 is negative, flow is zero
    flow = (2/3) * (g**0.5) * C * L * (H1**(3/2) - H2**(3/2))  # Weir flow equation
    return flow
# Function to calculate total flow for all gates in a row
def calculate_total_flow(row, rating_curve):

    total_flow = 0.0
    for gate in row[2:]:  # Skip the first two columns (Date and Lake Elevation)
        if gate > 0:  # Only calculate flow for open gates
            print(f"Calculating flow for {row['Date']}, gate opening: {gate} ft at lake elevation: {row['Lake Elevation']} ft")
            total_flow += calculate_flow(gate, row['Lake Elevation'], rating_curve)

    return round(total_flow, 2)

# set name attribute for rating curves to identify them later
lawtonka_rating_curve.name = "Lawtonka"
ellsworth_rating_curve.name = "Ellsworth"

# Apply the flow calculation to each row in the gate data
lawtonka_gate_data['Total Flow (cfs)'] = lawtonka_gate_data.apply(lambda row: calculate_total_flow(row, lawtonka_rating_curve), axis=1)
ellsworth_gate_data['Total Flow (cfs)'] = ellsworth_gate_data.apply(lambda row: calculate_total_flow(row, ellsworth_rating_curve), axis=1)

lawtonka_gate_data

#%%
# %%
# check the data type of the time column
lawtonka_gate_data['Date'].dtype
# %%
# i need the data column to be datetime objects
lawtonka_gate_data['Date'] = pd.to_datetime(lawtonka_gate_data['Date'], errors='coerce')
ellsworth_gate_data['Date'] = pd.to_datetime(ellsworth_gate_data['Date'], errors='coerce')

type(lawtonka_gate_data['Date'].iloc[0])
# %%
# set Date column as index
lawtonka_gate_data.set_index('Date', inplace=True)
ellsworth_gate_data.set_index('Date', inplace=True)

# %%
# check if times are all unique and are in ascending order
# lawtonka_gate_data.index.is_unique
# show which dates are not unique
lawtonka_gate_data[lawtonka_gate_data.index.duplicated(keep=False)]

# %%
# export the results to DSS
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer, UNDEFINED
# from datetime import datetime

dss_file = "gages.dss"
def write_to_dss(df, pathname):
    """
    Write the df to a DSS file with the specified pathname.
    """
    print (f"Writing data to DSS file at pathname: {pathname}")
    # datetime_list = df['Date'].dt.to_pydatetime().tolist()
    # datetime_list to a list of strings in the format "ddMMMyyyy HH:MM"
    # datetime_list = [dt.strftime("%d%b%Y %H:%M:%S") for dt in datetime_list]
    # datetime_list = [datetime.strptime(s, "%d%b%Y %H:%M:%S") for s in datetime_list]
    # print (f"{datetime_list}")
    # df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d %H:%M:%S")
    # convert the Date column to a string of the format "ddMMMyyyy HH:MM:SS"
    # df["Date"] = df["Date"].dt.strftime("%d%b%Y %H:%M:%S")
    
    # create a TimeSeriesContainer object
    tsc = TimeSeriesContainer()
    tsc.pathname = pathname
    # tsc.startDateTime = df.index.min().strftime("%d%b%Y %H:%M:%S")
    tsc.numberValues = len(df)
    tsc.times = df.index.to_numpy()# Convert to datetime objects
    tsc.values = df["Total Flow (cfs)"].tolist()
    tsc.units = "cfs"
    tsc.type = "INST"
    tsc.interval = -1
    with HecDss.Open(dss_file) as dss:        
        dss.deletePathname(tsc.pathname)
        dss.put(tsc)

write_to_dss(lawtonka_gate_data, "//LAWTONKA/RES FLOW-OUT//IR-CENTURY/Obs Gate Ops")
write_to_dss(ellsworth_gate_data, "//ELLSWORTH/RES FLOW-OUT//IR-CENTURY/Obs Gate Ops")

# %%
