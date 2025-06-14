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

    def fetch_hydrometric_data_ca(self, station_numbers, start_date, end_date, limit=1000):
        dates = self.create_date_range(start_date, end_date)
        data_dict = {'Date': dates}
        date_index_dict = {str(date.date()): idx for idx, date in enumerate(dates)}
        station_info = []
        print(len(station_numbers))

        # Initialize the data dictionary with -1 values for each station
        for station_number in station_numbers:
            data_dict[station_number] = [-1] * len(dates)  # Fill with -1 by default
            
            offset = 0
            full_data = []
            start_time_station = time.time()
            
            while True:
                url = f"https://api.weather.gc.ca/collections/hydrometric-daily-mean/items"
                params = {
                    'STATION_NUMBER': station_number,
                    'datetime': f"{start_date}/{end_date}",
                    'limit': limit,
                    'offset': offset,
                    'f': 'json'
                }

                response = requests.get(url, params=params)
                response_data = response.json()

                if 'features' in response_data and response_data['features']:
                    full_data.extend(response_data['features'])
                    offset += limit
                    if len(response_data['features']) < limit:
                        break
                else:
                    break
            
            if full_data:
                data_list = [
                    {
                        'Date': feature['properties']['DATE'],
                        'value': feature['properties']['DISCHARGE'] if feature['properties']['DISCHARGE'] is not None else -1
                    }
                    for feature in full_data
                ]
                
                flow_data = pd.DataFrame(data_list)
                flow_data['value'] = pd.to_numeric(flow_data['value'], errors='coerce')
                flow_data['Date'] = pd.to_datetime(flow_data['Date']).dt.date.astype(str)

                for date, flow in zip(flow_data['Date'], flow_data['value']):
                    if date in date_index_dict:
                        date_index = date_index_dict[date]
                        data_dict[station_number][date_index] = flow

                first_feature = full_data[0]['properties']
                #print("Properties:", first_feature)
                geometry = full_data[0]['geometry']
                #print("Geometry:", geometry)
                station_info.append({
                    'Station_Number': first_feature['STATION_NUMBER'],
                    'Station_Name': first_feature['STATION_NAME'],
                    'Latitude': geometry['coordinates'][1],
                    'Longitude': geometry['coordinates'][0],
                    'Drainage_Area': first_feature.get('DRAINAGE_AREA_GROSS', None)
                })
            else:
                print(f"Flow data not found for station: {station_number}")
                # Append placeholder station info if data not found
                station_info.append({
                    'Station_Number': station_number,
                    'Station_Name': "Unknown",
                    'Latitude': -1,
                    'Longitude': -1,
                    'Drainage_Area': None
                })

            end_time_station = time.time()
            print(f"Time taken to retrieve data for station {station_number}: {end_time_station - start_time_station} seconds")

        combined_df = pd.DataFrame(data_dict)
        return combined_df, station_info

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
