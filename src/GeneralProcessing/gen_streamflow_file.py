"""
Streamflow File Preparation
===============================================
gen_streamflow_file.py contains a class GenStreamflowFile that handles fetching and combining streamflow data from USGS and Environment Canada and generating output in the OBSTXT and ENSIM formats.

Parameters:
------------
`fetch_hydrometric_data_ca`: Fetches flow data from Canadian stations.
`extract_flow_data_us`: Fetches flow data from US stations.
`write_flow_data_to_file_obstxt`: Writes the data in OBSTXT format.
`write_flow_data_to_file_ensim`: Writes the data in ENSIM format.

Example Usage (Please check MESH_streamflowFile_example.ipynb for step by step example)
-----------------------------------------------------------------------------------------
>>> from GeneralProcessing.gen_streamflow_file import GenStreamflowFile
>>> gen_flow = GenStreamflowFile()
>>> 
>>> # 1) Historical daily‐mean (1980–2018)
>>> station_ca = ["05GG001", "05AC012"]
>>> station_us = ["06132200", "05020500"]
>>> start_date = "1980-03-01"
>>> end_date   = "2018-01-10"
>>> df_ca, meta_ca = gen_flow.fetch_hydrometric_data_ca(station_ca, start_date, end_date)
>>> df_us, meta_us = gen_flow.extract_flow_data_us(station_us, start_date, end_date)
>>> combined = pd.merge(df_ca, df_us, on="Date", how="outer")
>>> 
>>> # 2) Realtime provisional (last 1 month by 1-day windows)
>>> from datetime import datetime, timezone
>>> from dateutil.relativedelta import relativedelta
>>> end_dt = datetime.now(timezone.utc).replace(microsecond=0)
>>> start_dt = end_dt - relativedelta(months=1)
>>> start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
>>> end   = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
>>> df_rt, meta_rt = gen_flow.fetch_hydrometric_realtime_full_range(
...     station_numbers=["05GG001","05AC012"],
...     start=start, end=end,
...     window_days=1, freq_hours=12
... )
>>> 
>>> # 3) Write files
>>> all_meta = meta_ca + meta_us + meta_rt
>>> gen_flow.write_flow_data_to_file_obstxt("streamflow_obs.txt", combined, all_meta)
>>> gen_flow.write_flow_data_to_file_ensim("streamflow.tb0", combined, all_meta)
"""

import pandas as pd
import numpy as np
import requests
from owslib.ogcapi.features import Features
from datetime import datetime, timedelta, timezone
import time
from typing import Optional

class GenStreamflowFile:
    def __init__(self):
        self.oafeat = Features("https://api.weather.gc.ca/")

    def create_date_range(self, start_date, end_date):
        return pd.date_range(start=start_date, end=end_date)

    def extract_flow_data_us(self, station_list, start_date, end_date):
        dates = self.create_date_range(start_date, end_date)
        data_dict = {'Date': dates}
        date_index_dict = {str(date.date()): idx for idx, date in enumerate(dates)}
        station_info = []
        print(len(station_list))

        # Initialize the data dictionary with NaN values for each station
        for station in station_list:
            data_dict[station] = [-1] * len(dates)  # Fill with -1 by default

        for station in station_list:
            start_time_station = time.time()
            url = f"https://waterservices.usgs.gov/nwis/dv/?format=json&sites={station}&startDT={start_date}&endDT={end_date}&parameterCd=00060&statCd=00003"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # Check if 'timeSeries' is not empty
                if 'value' in data and 'timeSeries' in data['value'] and data['value']['timeSeries']:
                    time_series = data['value']['timeSeries'][0]
                    variable_info = time_series['variable']
                    unit = variable_info.get('unit', {}).get('unitCode', None)
                    parameter_units = variable_info.get('variableDescription', None)

                    records = time_series['values'][0]['value']
                    flow_data = pd.DataFrame(records)
                    flow_data['value'] = pd.to_numeric(flow_data['value'], errors='coerce')

                    # Convert flow data to cms if the unit is cfs
                    if unit == 'ft3/s' or parameter_units == 'Cubic Feet per Second':
                        flow_data['value'] = flow_data['value'] * 0.0283168
                    
                    flow_data['dateTime'] = pd.to_datetime(flow_data['dateTime']).dt.date.astype(str)

                    for date, flow in zip(flow_data['dateTime'], flow_data['value']):
                        if date in date_index_dict:
                            date_index = date_index_dict[date]
                            data_dict[station][date_index] = flow
                    
                    site_info = time_series['sourceInfo']
                    station_info.append({
                        'Station_Number': site_info['siteCode'][0]['value'],
                        'Station_Name': site_info['siteName'],
                        'Latitude': site_info['geoLocation']['geogLocation']['latitude'],
                        'Longitude': site_info['geoLocation']['geogLocation']['longitude'],
                        'Drainage_Area': next((prop['value'] for prop in site_info['siteProperty'] if prop['name'] == 'drain_area_va'), None),
                        'Unit': unit,
                        'Parameter_Units': parameter_units
                    })
                else:
                    print(f"Flow data not found for station: {station}")
                    # Append placeholder station info if data not found
                    station_info.append({
                        'Station_Number': station,
                        'Station_Name': "Unknown",
                        'Latitude': -1,
                        'Longitude': -1,
                        'Drainage_Area': None,
                        'Unit': None,
                        'Parameter_Units': None
                    })
            else:
                print(f"Failed to retrieve data for station: {station}")
                # Append placeholder station info if request fails
                station_info.append({
                    'Station_Number': station,
                    'Station_Name': "Unknown",
                    'Latitude': -1,
                    'Longitude': -1,
                    'Drainage_Area': None,
                    'Unit': None,
                    'Parameter_Units': None
                })
            
            end_time_station = time.time()
            print(f"Time taken to retrieve data for station {station}: {end_time_station - start_time_station} seconds")

        combined_df = pd.DataFrame(data_dict)
        return combined_df, station_info
        
    def extract_flow_data_us_with_metadata(
        self,
        station_list: list[str],
        start_date: str,
        end_date: str,
        limit: int = 1000
    ) -> tuple[pd.DataFrame, list[dict]]:
        """
        Fetch daily‐mean discharge and full station metadata for USGS gauges.

        Parameters
        ----------
        station_list : list[str]
            USGS station numbers (e.g. ['06132200']).
        start_date : str
            Start date in 'YYYY-MM-DD' format.
        end_date : str
            End   date in 'YYYY-MM-DD' format.
        limit : int
            Page size for API requests (default=1000).

        Returns
        -------
        df : pd.DataFrame
            Indexed by Date, one column per station with daily mean discharge [m³/s].
        station_info : list[dict]
            Metadata for each station, including:
              Station_Number, Station_Name, Latitude, Longitude,
              Drainage_Area, Contrib_Drainage_Area, Elevation_m, Datum
        """
        # ensure numpy is imported: import numpy as np
        # 1) build daily index
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        df = pd.DataFrame({'Date': dates})
        idx = {d.strftime('%Y-%m-%d'): i for i, d in enumerate(dates)}
        for st in station_list:
            df[st] = np.nan

        # 2) fetch daily‐mean via DV service
        for st in station_list:
            t0 = time.time()
            r = requests.get(
                "https://waterservices.usgs.gov/nwis/dv/",
                params={
                    'format':     'json',
                    'sites':      st,
                    'startDT':    start_date,
                    'endDT':      end_date,
                    'parameterCd':'00060',
                    'statCd':     '00003'
                }
            )
            r.raise_for_status()
            series = r.json().get('value', {}).get('timeSeries', [])
            if series:
                for rec in series[0]['values'][0]['value']:
                    date = rec['dateTime'][:10]
                    try:
                        val = float(rec['value'])
                    except (TypeError, ValueError):
                        val = np.nan
                    if date in idx:
                        df.iat[idx[date], df.columns.get_loc(st)] = val
            print(f"Fetched DV for {st} in {time.time()-t0:.1f}s")

        df.set_index('Date', inplace=True)

        # 3) fetch expanded site metadata via RDB Site service
        station_info = []
        def to_float(x):
            try: return float(x)
            except: return np.nan

        for st in station_list:
            t0 = time.time()
            r = requests.get(
                "https://waterservices.usgs.gov/nwis/site",
                params={
                    'format':     'rdb',
                    'sites':      st,
                    'siteOutput': 'expanded',
                    'siteStatus': 'all'
                }
            )
            r.raise_for_status()
            # strip comments, skip types row, read data row
            lines = [L for L in r.text.splitlines() if not L.startswith('#') and L.strip()]
            if len(lines) >= 3:
                header = lines[0].split('\t')
                values = lines[2].split('\t')
                meta   = dict(zip(header, values))
            else:
                meta = {}

            station_info.append({
                'Station_Number':        meta.get('site_no', st),
                'Station_Name':          meta.get('station_nm'),
                'Latitude':              to_float(meta.get('dec_lat_va')),
                'Longitude':             to_float(meta.get('dec_long_va')),
                'Drainage_Area':         to_float(meta.get('drain_area_va')),
                'Contrib_Drainage_Area': to_float(meta.get('contrib_drain_area_va')),
                'Elevation_m':           to_float(meta.get('alt_va')),
                'Datum':                 meta.get('vertical_datum')
            })
            print(f"Fetched metadata for {st} in {time.time()-t0:.1f}s")

        return df, station_info
    
    def fetch_hydrometric_data_ca(
        self,
        station_numbers: list[str],
        start_date: str,
        end_date: str,
        limit: int = 1000
    ) -> tuple[pd.DataFrame, list[dict]]:
        """
        Fetch daily‐mean discharge and full station metadata for Canadian hydrometric stations.

        Parameters
        ----------
        station_numbers : list of str
            Environment Canada station IDs (e.g. ['05HG001', '05AG006']).
        start_date : str
            Start date in 'YYYY-MM-DD' format.
        end_date : str
            End date in 'YYYY-MM-DD' format.
        limit : int, optional
            API page size (default=1000).

        Returns
        -------
        df : pandas.DataFrame
            DataFrame indexed by Date, with one column per station containing daily mean discharge.
        metadata : list of dict
            List of station metadata dicts with keys:
              Station_Number, Station_Name, CONTRIBUTOR_EN, PROV_TERR_STATE_LOC,
              DRAINAGE_AREA_GROSS, DRAINAGE_AREA_EFFECT, REAL_TIME, RHBN,
              STATUS_EN, VERTICAL_DATUM, Latitude, Longitude
        """
        # 1) build empty daily‐indexed DataFrame
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data = {'Date': dates}
        idx_map = {dt.strftime('%Y-%m-%d'): i for i, dt in enumerate(dates)}
        for st in station_numbers:
            data[st] = [None] * len(dates)
        df = pd.DataFrame(data)

        # 2) fetch daily‐mean discharge
        for st in station_numbers:
            offset = 0
            feats_all = []
            t0 = time.time()
            while True:
                url = "https://api.weather.gc.ca/collections/hydrometric-daily-mean/items"
                params = {
                    'STATION_NUMBER': st,
                    'datetime':       f"{start_date}/{end_date}",
                    'limit':          limit,
                    'offset':         offset,
                    'f':              'json'
                }
                r = requests.get(url, params=params)
                r.raise_for_status()
                feats = r.json().get('features', [])
                if not feats:
                    break
                feats_all.extend(feats)
                offset += limit
                if len(feats) < limit:
                    break

            for feat in feats_all:
                p = feat['properties']
                date_str = p['DATE']
                disc = p.get('DISCHARGE')
                if disc is None:
                    continue
                key = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
                if key in idx_map:
                    df.at[idx_map[key], st] = float(disc)
            print(f"Fetched daily‐mean for {st} in {time.time()-t0:.1f}s")

        # 3) fetch full station metadata
        metadata = []
        for st in station_numbers:
            t0 = time.time()
            url = "https://api.weather.gc.ca/collections/hydrometric-stations/items"
            params = {'STATION_NUMBER': st, 'f': 'json', 'limit': 1}
            r = requests.get(url, params=params)
            r.raise_for_status()
            feats = r.json().get('features', [])
            if feats:
                p = feats[0]['properties']
                lon, lat = feats[0]['geometry']['coordinates']
                metadata.append({
                    'Station_Number':       p.get('STATION_NUMBER'),
                    'Station_Name':         p.get('STATION_NAME'),
                    'CONTRIBUTOR_EN':       p.get('CONTRIBUTOR_EN'),
                    'PROV_TERR_STATE_LOC':  p.get('PROV_TERR_STATE_LOC'),
                    'Drainage_Area':  p.get('DRAINAGE_AREA_GROSS'),
                    'DRAINAGE_AREA_EFFECT': p.get('DRAINAGE_AREA_EFFECT'),
                    'REAL_TIME':            p.get('REAL_TIME'),
                    'RHBN':                 p.get('RHBN'),
                    'STATUS_EN':            p.get('STATUS_EN'),
                    'VERTICAL_DATUM':       p.get('VERTICAL_DATUM'),
                    'Latitude':             lat,
                    'Longitude':            lon
                })
            else:
                metadata.append({'Station_Number': st})
            print(f"Fetched metadata for {st} in {time.time()-t0:.1f}s")

        return df.set_index('Date'), metadata

    def fetch_hydrometric_realtime_full_range(
        self,
        station_numbers: list[str],
        start: str,
        end: str,
        window_days: int = 1,
        freq_hours: Optional[int] = None,
        limit: int = 1000
    ) -> tuple[pd.DataFrame, list[dict]]:
        """
        Fetches provisional real-time discharge by slicing [start,end] into
        `window_days`-day windows. If `freq_hours` is given, the result is
        resampled to that interval; otherwise you get the native timestamps.
        """
        base_url = "https://api.weather.gc.ca/collections/hydrometric-realtime/items"
        headers = {"Accept": "application/geo+json"}
        iso_fmt = "%Y-%m-%dT%H:%M:%SZ"

        start_dt = datetime.strptime(start, iso_fmt).replace(tzinfo=timezone.utc)
        end_dt   = datetime.strptime(end,   iso_fmt).replace(tzinfo=timezone.utc)

        records = {st: [] for st in station_numbers}
        meta    = {}

        win = start_dt
        while win < end_dt:
            win_end = min(win + timedelta(days=window_days), end_dt)
            t0 = time.time()
            for st in station_numbers:
                params = {
                    "STATION_NUMBER": st,
                    "datetime":       f"{win.strftime(iso_fmt)}/{win_end.strftime(iso_fmt)}",
                    "limit":          limit,
                    "offset":         0,
                    "f":              "json"
                }
                resp = requests.get(base_url, headers=headers, params=params)
                feats = resp.json().get("features", [])
                for f in feats:
                    p = f["properties"]
                    dt = p.get("DATETIME")
                    q  = p.get("DISCHARGE")
                    if dt and q is not None:
                        ts = datetime.strptime(dt, iso_fmt).replace(tzinfo=timezone.utc)
                        records[st].append((ts, q))
                if st not in meta and feats:
                    p0   = feats[0]["properties"]
                    geom = feats[0]["geometry"]
                    meta[st] = {
                        "Station_Number": p0["STATION_NUMBER"],
                        "Station_Name":   p0["STATION_NAME"],
                        "Latitude":       geom["coordinates"][1],
                        "Longitude":      geom["coordinates"][0],
                        "Drainage_Area":  p0.get("DRAINAGE_AREA_GROSS")
                    }
            print(f"Window {win.date()}–{win_end.date()} in {time.time()-t0:.1f}s")
            win = win_end

        # assemble
        df_all = pd.DataFrame()
        for st, recs in records.items():
            if not recs:
                continue
            df = (pd.DataFrame(recs, columns=["DateTime", st])
                    .drop_duplicates("DateTime")
                    .set_index("DateTime"))
            if freq_hours is not None:
                df = df.resample(f"{freq_hours}h").mean()
            df_all = df if df_all.empty else df_all.join(df, how="outer")

        df_all.index.name = "DateTime"
        df_all = df_all.sort_index().sort_index(axis=1)
        meta_list = list(meta.values())
        for st in station_numbers:
            if st not in meta:
                meta_list.append({
                    "Station_Number": st,
                    "Station_Name":   "Unknown",
                    "Latitude":       None,
                    "Longitude":      None,
                    "Drainage_Area":  None
                })
        return df_all, meta_list
       
    def write_flow_data_to_file_obstxt(
        self,
        file_path: str,
        flow_data: pd.DataFrame,
        site_details: list
    ):
        """
        Write a pandas DataFrame of observed streamflow to a space-delimited text file.
    
        Parameters:
        -----------
        file_path : str
            Path for the output .txt file.
        flow_data : pd.DataFrame
            Time series data. May include a 'Date' column (case-insensitive)
            or have a DatetimeIndex.
        site_details : list of dict
            One dict per data column, each with keys:
            'Station_Number', 'Latitude', 'Longitude', 'Drainage_Area', 'Station_Name'.
        """
    
        # 1) Replace NaNs with EnSim’s missing-value code
        flow_data = flow_data.fillna(-1.000)
    
        # 2) Detect any column literally named "Date" (case-insensitive)
        date_cols = [c for c in flow_data.columns if c.lower() == 'date']
    
        # 3) Build the list of actual data columns:
        #    - If a Date column exists, drop it
        #    - Otherwise, treat every column as data
        if date_cols:
            data_columns = [c for c in flow_data.columns if c.lower() != 'date']
            # ensure the Date column is datetime for min/max
            flow_data[date_cols[0]] = pd.to_datetime(flow_data[date_cols[0]])
        else:
            data_columns = flow_data.columns.tolist()
    
        # 4) Sanity-check: number of data columns must match site_details length
        num_stations = len(data_columns)
        if len(site_details) != num_stations:
            raise ValueError(
                f"Expected {num_stations} site_details entries, but got {len(site_details)}."
            )
    
        # 5) Determine start/end dates:
        #    Priority 1: 'Date' column
        #    Priority 2: DatetimeIndex
        #    Fallback : today
        if date_cols:
            start_date = flow_data[date_cols[0]].min()
            end_date   = flow_data[date_cols[0]].max()
        elif isinstance(flow_data.index, pd.DatetimeIndex):
            start_date = flow_data.index.min()
            end_date   = flow_data.index.max()
        else:
            # no date info available
            start_date = end_date = datetime.now()
    
        # 6) Write header lines
        num_days = flow_data.shape[0]
        start_year = start_date.year
        start_day_of_year = start_date.timetuple().tm_yday
    
        with open(file_path, "w") as file_conn:
            # a) Title line with date span
            file_conn.write(
                f"Observedstreamflow\t"
                f"{start_date.strftime('%Y/%m/%d')}\t"
                f"{end_date.strftime('%Y/%m/%d')}\n"
            )
            # b) Metadata: stations, days, timestep (24), start year & DOY
            file_conn.write(
                f"{num_stations}  {num_days}  {num_days}  24  "
                f"{start_year}  {start_day_of_year} 00\n"
            )
    
            # 7) Station metadata block
            for station_id in data_columns:
                info = next(
                    (s for s in site_details if s["Station_Number"] == station_id),
                    None
                )
                if not info:
                    continue  # skip if no matching site_details
                lat = info['Latitude']
                lon = info['Longitude']
                da  = info.get('Drainage_Area') or -1.0
                name = info.get('Station_Name', "")
    
                # Write: lat*60, lon*60 (integers), station ID, lat, lon, drainage area, name
                file_conn.write(
                    f"{int(lat * 60):4d} "
                    f"{int(lon * 60):4d} "
                    f"{station_id:12s} "
                    f"{lat:12.6f} "
                    f"{lon:12.6f} "
                    f"{float(da):12.3f} "
                    f"{name}\n"
                )
    
            # 8) Data lines: one row per time step, values only
            for idx in range(num_days):
                # extract the flow values in column order
                row = flow_data.iloc[idx]
                values = [row[c] for c in data_columns]
                # format each value to width=12, 4 decimals
                line = " ".join(f"{v:12.4f}" for v in values)
                # same date grab/format/append
                if date_cols:
                    date_val = flow_data[date_cols[0]].iloc[idx]
                else:
                    date_val = flow_data.index[idx]
                date_str = date_val.strftime("%Y/%m/%d")
                
                file_conn.write(f"{line}  {date_str}\n")
                #file_conn.write(f"{line}\n")

    def write_flow_data_to_file_ensim(
        self,
        file_path: str,
        flow_data: pd.DataFrame,
        site_details: list,
        column_width: int = 12,
        initial_spacing: int = 28
    ):
        """
        Write a pandas DataFrame of streamflow time series to an EnSim‐formatted ASCII file.
    
        Parameters:
        -----------
        file_path : str
            Path to the output file.
        flow_data : pd.DataFrame
            Time series data. May include a 'Date' column (case‐insensitive)
            or have a DatetimeIndex.
        site_details : list of dict
            One dict per data column, each with 'Latitude' and 'Longitude' keys.
        column_width : int
            Fixed width for each numeric field.
        initial_spacing : int
            Number of spaces before the first data column on each line.
        """
    
        # 1) Replace all NaNs with EnSim’s missing‐value code (-1.000)
        flow_data = flow_data.fillna(-1.000)
    
        # 2) Detect any column named exactly “Date” (case‐insensitive)
        date_cols = [c for c in flow_data.columns if c.lower() == 'date']
    
        # 3) Build the list of actual data columns:
        #    - If a Date column exists, drop it
        #    - Otherwise, treat every column as data
        if date_cols:
            data_columns = [c for c in flow_data.columns if c.lower() != 'date']
        else:
            data_columns = flow_data.columns.tolist()
    
        # 4) Sanity‐check: number of data columns must match site_details length
        num_columns = len(data_columns)
        if len(site_details) != num_columns:
            raise ValueError(
                f"Expected {num_columns} site_details entries, but got {len(site_details)}."
            )
    
        # 5) Determine the StartTime for the header:
        #    - Priority 1: first value in the Date column (if present)
        #    - Priority 2: first value of a DatetimeIndex (if no Date column)
        #    - Fallback : current date
        if date_cols:
            first_date = flow_data[date_cols[0]].iloc[0]
        elif isinstance(flow_data.index, pd.DatetimeIndex):
            first_date = flow_data.index[0]
        else:
            first_date = datetime.now()
    
        # Format as “YYYY/MM/DD 00:00:00.00000”
        start_time_str = first_date.strftime("%Y/%m/%d") + " 00:00:00.00000"
    
        # 6) Build the EnSim header block
        header = [
            "########################################",
            ":FileType               tb0  ASCII  EnSim 1.0",
            "#",
            "# DataType               Time Series",
            "#",
            ":Application            EnSimHydrologic",
            ":Version                2.1.23",
            ":WrittenBy              PythonScript",
            f":CreationDate           {datetime.now():%Y-%m-%d}",
            "#",
            "#---------------------------------------",
            ":SourceFile             flow_data",
            "#",
            ":Name                   streamflow",
            "#",
            ":Projection             LATLONG",
            ":Ellipsoid              WGS84",
            "#",
            f":StartTime              {start_time_str}",
            "#",
            ":AttributeUnits         1.0000000",
            ":DeltaT                 24",
            ":RoutingDeltaT          1",
            "#",
            ":ColumnMetaData",
            # ColumnUnits: every column in cubic metres per second
            "   :ColumnUnits   " +
                " ".join("m3/s".rjust(column_width) for _ in range(num_columns)),
            # ColumnType: every column is a floating‐point value
            "   :ColumnType    " +
                " ".join("float".rjust(column_width) for _ in range(num_columns)),
            # ColumnName: the actual data column labels
            "   :ColumnName    " +
                " ".join(name.rjust(column_width) for name in data_columns),
            # ColumnLocationX: longitudes from site_details
            "   :ColumnLocationX  " +
                " ".join(f"{s['Longitude']:.5f}".rjust(column_width)
                         for s in site_details),
            # ColumnLocationY: latitudes from site_details
            "   :ColumnLocationY  " +
                " ".join(f"{s['Latitude']:.5f}".rjust(column_width)
                         for s in site_details),
            # Default coefficients (coeff1–coeff4) set to zero
            "   :coeff1         " +
                " ".join("0.0000E+00".rjust(column_width)
                         for _ in range(num_columns)),
            "   :coeff2         " +
                " ".join("0.0000E+00".rjust(column_width)
                         for _ in range(num_columns)),
            "   :coeff3         " +
                " ".join("0.0000E+00".rjust(column_width)
                         for _ in range(num_columns)),
            "   :coeff4         " +
                " ".join("0.0000E+00".rjust(column_width)
                         for _ in range(num_columns)),
            # Value1: default multiplier “1” for each column
            "   :Value1         " +
                " ".join("1".rjust(column_width)
                         for _ in range(num_columns)),
            ":EndColumnMetaData",
            ":endHeader"
        ]
    
        # 7) Open the output file and write header + data lines
        with open(file_path, "w") as f:
            # 7a) Write the header block
            f.write("\n".join(header) + "\n")
            # 7b) Write one line per time step
            for _, row in flow_data.iterrows():
                # Extract values for each data column in order
                values = [row[col] for col in data_columns]
                # Format each value to fixed width, 4 decimal places
                line = " ".join(f"{val:>{column_width}.4f}" for val in values)
                # grab the date for this row
                if date_cols:
                    date_val = row[date_cols[0]]
                else:
                    date_val = row.name           # assuming a DatetimeIndex
                # format it
                date_str = date_val.strftime("%Y/%m/%d")
                # 3append it
                line = f"{line}  {date_str}"
                
                # Write the indented data line
                f.write(" " * initial_spacing + line + "\n")
