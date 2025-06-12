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
>>> from MESHpyPreProcessing.gen_streamflow_file import GenStreamflowFile
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
                    'DRAINAGE_AREA_GROSS':  p.get('DRAINAGE_AREA_GROSS'),
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
        station_numbers,
        start: str,
        end: str,
        window_days: int = 1,
        freq_hours: int = 1,
        limit: int = 1000
    ):
        """
        Fetches hourly provisional (real-time) discharge by slicing [start,end] into
        `window_days`-day windows and resampling to `freq_hours`.
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
                    .set_index("DateTime")
                    .resample(f"{freq_hours}H")
                    .mean())
            df_all = df if df_all.empty else df_all.join(df, how="outer")

        df_all.index.name = "DateTime"
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
        
    def write_flow_data_to_file_obstxt(self, file_path, flow_data, site_details):
        flow_data = flow_data.fillna(-1.000)
        flow_data['Date'] = pd.to_datetime(flow_data['Date'])

        with open(file_path, "w") as file_conn:
            start_date = flow_data['Date'].min()
            end_date = flow_data['Date'].max()
            file_conn.write(f"Observedstreamflow\t{start_date.strftime('%Y/%m/%d')}\t{end_date.strftime('%Y/%m/%d')}\n")
            num_stations = flow_data.shape[1] - 1
            num_days = flow_data.shape[0]
            start_year = start_date.strftime('%Y')
            start_day_of_year = start_date.timetuple().tm_yday
            file_conn.write(f"{num_stations}  {num_days}  {num_days}  24 {start_year}  {start_day_of_year} 00\n")
            
            for station_id in flow_data.columns[1:]:
                station_info = next((item for item in site_details if item["Station_Number"] == station_id), None)
                if station_info:
                    lat = station_info['Latitude']
                    lon = station_info['Longitude']
                    drainage_area = station_info['Drainage_Area']
                    if drainage_area is None:
                        drainage_area = -1.0
                    station_name = station_info['Station_Name']
                    file_conn.write(f"{int(lat * 60):4d} {int(lon * 60):4d} {station_id:12s} {lat:12.6f} {lon:12.6f} {float(drainage_area):12.3f} {station_name}\n")
            
            for i in range(num_days):
                flow_values = flow_data.iloc[i, 1:].values
                formatted_flow_values = " ".join(f"{x:12.4f}" for x in flow_values)
                file_conn.write(f"{formatted_flow_values}\n")

    def write_flow_data_to_file_ensim(self, file_path, flow_data, site_details, column_width=12, initial_spacing=28):
        flow_data = flow_data.fillna(-1.000)
        
        num_columns = flow_data.shape[1] - 1  # Exclude date column

        # Ensure site_details length matches the number of data columns
        if len(site_details) != num_columns:
            raise ValueError("The number of site details entries must match the number of data columns in flow_data")

        # Header with metadata
        header = [
            "########################################",
            ":FileType tb0  ASCII  EnSim 1.0",
            "#",
            "# DataType               Time Series",
            "#",
            ":Application             EnSimHydrologic",
            ":Version                 2.1.23",
            ":WrittenBy          PythonScript",
            f":CreationDate       {datetime.now().strftime('%Y-%m-%d')}",
            "#",
            "#---------------------------------------",
            ":SourceFile                   flow_data",
            "#",
            ":Name               streamflow",
            "#",
            ":Projection         LATLONG",
            ":Ellipsoid          WGS84",
            "#",
            f":StartTime          {flow_data['Date'].iloc[0].strftime('%Y/%m/%d')} 00:00:00.00000",
            "#",
            ":AttributeUnits            1.0000000",
            ":DeltaT               24",
            ":RoutingDeltaT         1",
            "#",
            ":ColumnMetaData",
            f"   :ColumnUnits             {' '.join(['m3/s'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :ColumnType              {' '.join(['float'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :ColumnName              {' '.join(name.rjust(column_width) for name in flow_data.columns[1:])}",
            "   :ColumnLocationX         " + ' '.join([f"{site['Longitude']:.5f}".rjust(column_width) for site in site_details]),
            "   :ColumnLocationY         " + ' '.join([f"{site['Latitude']:.5f}".rjust(column_width) for site in site_details]),
            f"   :coeff1                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :coeff2                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :coeff3                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :coeff4                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :Value1                  {' '.join(['1'.rjust(column_width) for _ in range(num_columns)])}",
            ":EndColumnMetaData",
            ":endHeader"
        ]

        # Write header and flow data to file
        with open(file_path, "w") as file_conn:
            file_conn.write("\n".join(header) + "\n")
            
            for _, row in flow_data.iterrows():
                flows = row[1:].values  # Exclude date
                flow_string = " ".join(f"{flow:>{column_width}.4f}" for flow in flows)  # Right-aligned values
                file_conn.write(f"{' ' * initial_spacing}{flow_string}\n")

 
    
    def write_flow_data_to_file_obstxt(self, file_path, flow_data, site_details):
        flow_data = flow_data.fillna(-1.000)
        num_columns = flow_data.shape[1] - 1  # Exclude date column

        # Ensure site_details length matches the number of data columns
        if len(site_details) != num_columns:
            raise ValueError("The number of site details entries must match the number of data columns in flow_data")

        flow_data['Date'] = pd.to_datetime(flow_data['Date'])

        with open(file_path, "w") as file_conn:
            start_date = flow_data['Date'].min()
            end_date = flow_data['Date'].max()
            file_conn.write(f"Observedstreamflow\t{start_date.strftime('%Y/%m/%d')}\t{end_date.strftime('%Y/%m/%d')}\n")
            num_stations = flow_data.shape[1] - 1
            num_days = flow_data.shape[0]
            start_year = start_date.strftime('%Y')
            start_day_of_year = start_date.timetuple().tm_yday
            file_conn.write(f"{num_stations}  {num_days}  {num_days}  24 {start_year}  {start_day_of_year} 00\n")
            
            for station_id in flow_data.columns[1:]:
                station_info = next((item for item in site_details if item["Station_Number"] == station_id), None)
                if station_info:
                    lat = station_info['Latitude']
                    lon = station_info['Longitude']
                    drainage_area = station_info['Drainage_Area']
                    if drainage_area is None:
                        drainage_area = -1.0
                    station_name = station_info['Station_Name']
                    file_conn.write(f"{int(lat * 60):4d} {int(lon * 60):4d} {station_id:12s} {lat:12.6f} {lon:12.6f} {float(drainage_area):12.3f} {station_name}\n")
            
            for i in range(num_days):
                flow_values = flow_data.iloc[i, 1:].values
                formatted_flow_values = " ".join(f"{x:12.4f}" for x in flow_values)
                file_conn.write(f"{formatted_flow_values}\n")

    def write_flow_data_to_file_ensim(self, file_path, flow_data, site_details, column_width=12, initial_spacing=28):
        flow_data = flow_data.fillna(-1.000)
        
        num_columns = flow_data.shape[1] - 1  # Exclude date column

        # Ensure site_details length matches the number of data columns
        if len(site_details) != num_columns:
            raise ValueError("The number of site details entries must match the number of data columns in flow_data")

        # Header with metadata
        header = [
            "########################################",
            ":FileType tb0  ASCII  EnSim 1.0",
            "#",
            "# DataType               Time Series",
            "#",
            ":Application             EnSimHydrologic",
            ":Version                 2.1.23",
            ":WrittenBy          PythonScript",
            f":CreationDate       {datetime.now().strftime('%Y-%m-%d')}",
            "#",
            "#---------------------------------------",
            ":SourceFile                   flow_data",
            "#",
            ":Name               streamflow",
            "#",
            ":Projection         LATLONG",
            ":Ellipsoid          WGS84",
            "#",
            f":StartTime          {flow_data['Date'].iloc[0].strftime('%Y/%m/%d')} 00:00:00.00000",
            "#",
            ":AttributeUnits            1.0000000",
            ":DeltaT               24",
            ":RoutingDeltaT         1",
            "#",
            ":ColumnMetaData",
            f"   :ColumnUnits             {' '.join(['m3/s'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :ColumnType              {' '.join(['float'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :ColumnName              {' '.join(name.rjust(column_width) for name in flow_data.columns[1:])}",
            "   :ColumnLocationX         " + ' '.join([f"{site['Longitude']:.5f}".rjust(column_width) for site in site_details]),
            "   :ColumnLocationY         " + ' '.join([f"{site['Latitude']:.5f}".rjust(column_width) for site in site_details]),
            f"   :coeff1                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :coeff2                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :coeff3                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :coeff4                  {' '.join(['0.0000E+00'.rjust(column_width) for _ in range(num_columns)])}",
            f"   :Value1                  {' '.join(['1'.rjust(column_width) for _ in range(num_columns)])}",
            ":EndColumnMetaData",
            ":endHeader"
        ]

        # Write header and flow data to file
        with open(file_path, "w") as file_conn:
            file_conn.write("\n".join(header) + "\n")
            
            for _, row in flow_data.iterrows():
                flows = row[1:].values  # Exclude date
                flow_string = " ".join(f"{flow:>{column_width}.4f}" for flow in flows)  # Right-aligned values
                file_conn.write(f"{' ' * initial_spacing}{flow_string}\n")
