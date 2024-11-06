# MESH-Scripts-PyLib

A Python library for preprocessing hydrometric and soil data, performing spatial analysis, and generating NetCDF files for use in hydrological modeling. The package includes utilities for streamflow file preparation, soil data processing, spatial analysis, and NetCDF file generation.

## Table of Contents
### Installation and Overview
- [Installation](#installation)
- [Overview](#overview)
### PreProcessing
- [Streamflow File Preparation (`gen_streamflow_file.py`)](#streamflow-file-preparation)
- [Soil Data Processing (`gsde_soil.py`)](#soil-data-processing)
- [Spatial Analysis (`gdf_edit.py`)](#spatial-analysis)
- [Basin and River Network Aggregation (`merit_basin_aggregation`)](#basin-and-river-network-aggregation)
- [NetCDF File Generation (`NetCDFWriter.py`)](#netcdf-file-generation)
### PostProcessing
- [Plot Variable from Vector setup (`plt_var_vector_setup.py`)](#plot-variable-from-vector-setup)
- [Contributing](#contributing)

## Installation and Overview

You can install the package using pip directly from GitHub:

```bash
pip install git+https://github.com/MESH-Model/MESH-Scripts-PyLib.git
```

This library provides several utilities that streamline data preprocessing for hydrological models like MESH. The key functionalities include:

- Extraction and processing of streamflow data from Canadian and US hydrometric sources.
- Soil data loading, merging, and cleaning from CSV files.
- Flagging non-contributing areas in spatial analysis using GeoDataFrames.
- Aggregation of basin and river networks with custom thresholds.
- Writing processed soil data to NetCDF format.

## Streamflow File Preparation

`gen_streamflow_file.py` contains a class `GenStreamflowFile` that handles fetching and combining streamflow data from USGS and Environment Canada and generating output in the OBSTXT and ENSIM formats.

Example Usage  (Please check MESH_streamflowFile_example.ipynb for step by step example) 
```python
from MESHpyPreProcessing.gen_streamflow_file import GenStreamflowFile
#Initialize the class
gen_flow = GenStreamflowFile()
# Define station IDs for Canada and the US
station_ca = ["05GG001", "05AC012"]
station_us = ["06132200", "05020500"]
# Set the date range
start_date = "1980-03-01"
end_date = "2018-01-10"
# Fetch hydrometric data
combined_data_ca, station_info_ca = gen_flow.fetch_hydrometric_data_ca(station_ca, start_date, end_date)
combined_data_us, station_info_us = gen_flow.extract_flow_data_us(station_us, start_date, end_date)
# Combine the data
combined_data = pd.merge(combined_data_ca, combined_data_us, on='Date', how='outer')
# Write to files in OBSTXT and ENSIM formats
gen_flow.write_flow_data_to_file_obstxt('MESH_input_streamflow.txt', combined_data, station_info_ca + station_info_us)
gen_flow.write_flow_data_to_file_ensim('MESH_input_streamflow.tb0', combined_data, station_info_ca + station_info_us, column_width=12, initial_spacing=28)
```

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
`soil_processor = GSDESoil(directory='path/to/data', input_basin='path/to/shapefile.shp', output_shapefile='path/to/output.shp')`
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
## Basin and River Network Aggregation
The merit_basin_aggregation function aggregates basin and river network shapefiles. This function uses parameters like minimum sub-area, slope, and river length to iteratively aggregate small sub-basins.
### Parameters
- **input_basin**: Basin `GeoDataFrame` with COMID identifiers.
- **input_river**: River network `GeoDataFrame` with slope and length attributes.
- **min_subarea**: Minimum area for sub-basins.
- **min_slope**: Minimum allowable river slope.
- **min_length**: Minimum river length.
This function iterates through sub-basins, merging those below the minimum sub-area threshold until no further aggregation is possible. It also computes and adjusts slopes, river lengths, and weighted slopes for simplified river networks.

### Example usage
```python
from MESHpyPreProcessing.merit_basin_aggregation import merit_basin_aggregation
import geopandas as gpd
import os

# Define paths and parameters
input_basin_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/SrsAboine-geofabric/sras_subbasins_MAF_noAgg.shp"
input_river_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/SrsAboine-geofabric/sras_rivers_MAF_noAgg.shp"
min_subarea = 50
min_slope = 0.0000001
min_length = 1.0
output_basin_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/sras_subbasins_MAF_Agg.shp"
output_river_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/sras_rivers_MAF_Agg.shp"

# Load input data
input_basin = gpd.read_file(input_basin_path)
input_river = gpd.read_file(input_river_path)

# Perform aggregation
agg_basin, agg_river = merit_basin_aggregation(input_basin, input_river, min_subarea, min_slope, min_length)

# Save aggregated data
agg_basin.to_file(output_basin_path)
agg_river.to_file(output_river_path)
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

## Plot Variable from Vector setup
`plt_var_from_vector_ddb_netcdf`, designed to plot spatial data from a vector drainage database in NetCDF format. 
The function generates a map showing specific variables within a watershed basin or across various land use classes, 
with options for custom color maps, subplot adjustments, and other visual enhancements.
### Example Usage

### 1. Plotting drainage database variables

Plots a specified variable from a NetCDF file, supporting variables dependent on subbasin or both subbasin and grouped response units (NGRU).

### Parameters
- **output_basin_path (str)**: Path to the shapefile containing the basin data.
- **ddbnetcdf_path (str)**: Path to the NetCDF file containing the drainage database.
- **variable_name (str)**: Name of the variable to plot from the NetCDF file (e.g., 'GRU').
- **save_path (str)**: Path where the plot will be saved (e.g., 'output/plot.png').
- **text_location (tuple)**: Coordinates for percentage text in subplots, default is `(0.55, 0.95)`.
- **font_size (int)**: Font size for text elements, default is `10`.
- **cmap (str or Colormap)**: Colormap for plotting (e.g., 'gnuplot2_r'), default is 'viridis'.
- **cbar_location (list)**: List specifying the colorbar position `[left, bottom, width, height]`.
- **subplot_adjustments (dict)**: Dictionary for subplot adjustments like spacing.
- **subbasin_var (str)**: Subbasin identifier in the NetCDF, default is `'subbasin'`.
- **comid_var (str)**: COMID identifier in the shapefile for merging, default is `'COMID'`.
- **landuse_classes (list or None)**: Optional; custom list of land use classes. If not provided, it defaults to the variable 'LandUse' from the NetCDF file.
- **grudim (str)**: Specifies the GRU dimension variable in the NetCDF (e.g., `'NGRU'`).
- **grunames_var (str)**: Specifies the land use names variable in the NetCDF (e.g., `'LandUse'`).

## Example Usage

Below is an example of how to configure and use `plt_var_from_vector_ddb_netcdf` for a specific project setup.

```python
from MESHpyPostProcessing.plt_var_vector_setup import plt_var_from_vector_ddb_netcdf
import os

# Define base directory paths
base_scratch_dir = '/scratch/fuaday/sras-agg-model_1'
output_basin_path = os.path.join(base_scratch_dir, 'geofabric-outputs/sras_subbasins_MAF_Agg.shp')
ddbnetcdf_path = os.path.join(base_scratch_dir, 'MESH-sras-agg/MESH_drainage_database.nc')

# Specify custom land use classes (optional)
lclass = [
    'Temperate or sub-polar needleleaf forest', 'Sub-polar taiga needleleaf forest',
    'Temperate or sub-polar broadleaf deciduous forest', 'Mixed forest',
    'Temperate or sub-polar shrubland', 'Temperate or sub-polar grassland',
    'Sub-polar or polar grassland-lichen-moss', 'Wetland', 'Cropland',
    'Barren lands', 'Urban', 'Water', 'Dump'
]

# Variable name to plot
variable_name = 'GRU'

# Path to save the plot
save_path = os.path.join(base_scratch_dir, f'geofabric-outputs/{variable_name}.png')

# Plotting function
plt_var_from_vector_ddb_netcdf(
    output_basin_path=output_basin_path, 
    ddbnetcdf_path=ddbnetcdf_path, 
    variable_name=variable_name, 
    save_path=save_path,
    text_location=(0.55, 0.95),
    font_size=10,
    cmap='gnuplot2_r',  # Custom colormap
    cbar_location=[0.91, 0.15, 0.02, 0.7],  # Adjusted colorbar position
    subplot_adjustments={'left': 0.1, 'right': 0.9, 'bottom': 0.1, 'top': 0.9, 'wspace': 0.1, 'hspace': 0.2},
    subbasin_var='subbasin',  # Subbasin identifier
    comid_var='COMID',  # Shapefile COMID for merging
    landuse_classes=lclass,  # Optional custom land use classes
    grudim='NGRU',  # GRU dimension from NetCDF
    grunames_var='LandUse'  # GRU names variable from NetCDF
)
```
## Contributing
If you'd like to contribute to this project, feel free to fork the repository and submit a pull request with your improvements.
