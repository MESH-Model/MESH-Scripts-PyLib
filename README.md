# MESH-Scripts-PyLib

A Python library for preprocessing hydrometric and soil data, performing spatial analysis, and generating NetCDF files for use in hydrological modeling. The package includes utilities for streamflow file preparation, soil data processing, spatial analysis, and NetCDF file generation.

## Table of Contents

- [Installation](#installation)
- [Overview](#overview)
- [Streamflow File Preparation (`gen_streamflow_file.py`)](#streamflow-file-preparation)
- [Soil Data Processing (`gsde_soil.py`)](#soil-data-processing)
- [Spatial Analysis (`gdf_edit.py`)](#spatial-analysis)
- [NetCDF File Generation (`NetCDFWriter.py`)](#netcdf-file-generation)
- [Contributing](#contributing)

## Installation

You can install the package using pip directly from GitHub:

```bash
pip install git+https://github.com/MESH-Model/MESH-Scripts-PyLib.git
```

## Overview

This library provides several utilities that streamline data preprocessing for hydrological models like MESH. The key functionalities include:

- Extraction and processing of streamflow data from Canadian and US hydrometric sources.
- Soil data loading, merging, and cleaning from CSV files.
- Flagging non-contributing areas in spatial analysis using GeoDataFrames.
- Writing processed soil data to NetCDF format.

## Streamflow File Preparation

`gen_streamflow_file.py` contains a class `GenStreamflowFile` that handles fetching and combining streamflow data from USGS and Environment Canada and generating output in the OBSTXT and ENSIM formats.

Example Usage\
`from MESHpyPreProcessing.gen_streamflow_file import GenStreamflowFile`
- Initialize the class\
`gen_flow = GenStreamflowFile()`
- Define station IDs for Canada and the US\
`station_ca = ["05GG001", "05AC012"]`\
`station_us = ["06132200", "05020500"]`
- Set the date range\
`start_date = "1980-03-01"`\
`end_date = "2018-01-10"`
- Fetch hydrometric data\
`combined_data_ca, station_info_ca = gen_flow.fetch_hydrometric_data_ca(station_ca, start_date, end_date)`\
`combined_data_us, station_info_us = gen_flow.extract_flow_data_us(station_us, start_date, end_date)`
- Combine the data\
`combined_data = pd.merge(combined_data_ca, combined_data_us, on='Date', how='outer')`
- Write to files in OBSTXT and ENSIM formats\
`gen_flow.write_flow_data_to_file_obstxt('MESH_input_streamflow.txt', combined_data, station_info_ca + station_info_us)`\
`gen_flow.write_flow_data_to_file_ensim('MESH_input_streamflow.tb0', combined_data, station_info_ca + station_info_us)`

Functions:
- `fetch_hydrometric_data_ca`: Fetches flow data from Canadian stations.
- `extract_flow_data_us`: Fetches flow data from US stations.
- `write_flow_data_to_file_obstxt`: Writes the data in OBSTXT format.
- `write_flow_data_to_file_ensim`: Writes the data in ENSIM format.

## Soil Data Processing

`gsde_soil.py` contains the `GSDESoil` class, which processes soil data from CSV files, merges it with a shapefile, and calculates soil property weights.

Example Usage\
`from MESHpyPreProcessing.gsde_soil import GSDESoil`
- Initialize the GSDESoil class\
`soil_processor = GSDESoil(directory='path/to/data', input_basin='path/to/shapefile.shp', output_shapefile='path/to/output.shp')`\
- Load and merge soil data\
`file_names = ['file1.csv', 'file2.csv']`\
`soil_processor.load_data(file_names)`
- Fill and clean data\
`soil_processor.fill_and_clean_data()`
- Calculate soil property weights and mesh values\
`gsde_intervals = [(0, 10), (10, 30), (30, 60)]`\
`mesh_intervals = [(0, 20), (20, 50)]`\
`soil_processor.calculate_weights(gsde_intervals, mesh_intervals)`\
`column_names = {'OC': ['OC1', 'OC2'], 'Sand': ['Sand1', 'Sand2']}`\
`soil_processor.calculate_mesh_values(column_names)`
- Merge data with shapefile and save the result\
`soil_processor.merge_and_save_shapefile()`

Functions:
- `load_data`: Loads and merges CSV files.
- `fill_and_clean_data`: Cleans the data by removing invalid values and filling missing ones.
- `calculate_weights`: Calculates weights for different soil intervals.
- `calculate_mesh_values`: Applies the weights to calculate mesh values for soil properties.
- `merge_and_save_shapefile`: Merges the soil data with the shapefile and saves the result.

## Spatial Analysis

`gdf_edit.py` provides functions to flag non-contributing areas (NCAs) or lakes and reservoirs in GeoDataFrames based on intersection thresholds, with customizable options for column names, default values, and initialization values.

### Example Usage

### 1. Using Shapefiles

```python
from MESHpyPreProcessing.gdf_edit import flag_ncaalg_from_files

# Flag areas based on intersection thresholds with default settings
flagged_gdf = flag_ncaalg_from_files(
    'path/to/shapefile1.shp', 
    'path/to/shapefile2.shp', 
    threshold=0.1, 
    output_path='output.shp'
)

# Flag areas using specific value column from gdf2 and custom initialization value
flagged_gdf = flag_ncaalg_from_files(
    'path/to/shapefile1.shp', 
    'path/to/shapefile2.shp', 
    threshold=0.1, 
    output_path='output.shp', 
    ncontr_col="custom_flag_column",   # Custom column in gdf1 to store flags
    value_column="NON_ID",             # Column in gdf2 with values to assign
    initial_value=0,                   # Initial value for gdf1's flag column
    default_value=5                    # Default value if no value_column specified
)
```
### 2. Using GeoDataFrames Directly
```python
from MESHpyPreProcessing.gdf_edit import flag_ncaalg

# Load GeoDataFrames
import geopandas as gpd
gdf1 = gpd.read_file('path/to/shapefile1.shp')
gdf2 = gpd.read_file('path/to/shapefile2.shp')

# Flag areas with default settings (constant value of 2)
flagged_gdf = flag_ncaalg(gdf1, gdf2, threshold=0.1)

# Flag using specific value column from gdf2 and custom initialization value
flagged_gdf = flag_ncaalg(
    gdf1, 
    gdf2, 
    threshold=0.1, 
    ncontr_col="custom_flag_column",   # Custom column in gdf1 to store flags
    value_column="NON_ID",             # Column in gdf2 with values to assign
    initial_value=0,                   # Initial value for gdf1's flag column
    default_value=5                    # Default value if no value_column specified
)
```

## NetCDF File Generation

NetCDFWriter.py contains a class NetCDFWriter that creates NetCDF files with processed soil data merged from shapefiles and NetCDF drainage databases.

Example Usage\
`from MESHpyPreProcessing.NetCDFWriter import NetCDFWriter`
- Initialize the NetCDFWriter class\
`writer = NetCDFWriter(nc_filename='output.nc', shapefile_path='path/to/shapefile.shp', input_ddb_path='path/to/input_ddb.nc')`
- Read the shapefile and set coordinates from the NetCDF drainage database\
`writer.read_shapefile()`\
`writer.set_coordinates()`
- Set the number of soil layers\
`writer.set_num_soil_layers(3)`
- Define properties and variable information\
`properties = {
    'layer_dependent': ['OC', 'Sand'],
    'layer_independent': ['Drainage_Area']
}`\
`variable_info = {
    'OC': ('OrganicCarbon', 'f4', 'kg/m^2'),
    'Sand': ('SandContent', 'f4', '%'),
    'Drainage_Area': ('DrainageArea', 'f4', 'km^2')
}`
- Write data to NetCDF
`writer.write_netcdf(properties, variable_info)`

Functions:
- `read_shapefile`: Reads the shapefile and prepares the GeoDataFrame.
- `set_coordinates`: Extracts longitude and latitude from the NetCDF drainage database.
- `set_num_soil_layers`: Sets the number of soil layers for the NetCDF file.
- `write_netcdf`: Writes processed data to a NetCDF file.

## Contributing
If you'd like to contribute to this project, feel free to fork the repository and submit a pull request with your improvements.
