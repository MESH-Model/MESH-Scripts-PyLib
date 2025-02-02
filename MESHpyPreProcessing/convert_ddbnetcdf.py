"""
NetCDF to CSV/Shapefile Converter
================================

This script contains a function `convert_netcdf` that converts a NetCDF file into either a CSV file or a Shapefile.

Example Usage:
--------------
>>> from convert_ddbnetcdf import convert_netcdf
>>> convert_netcdf(netcdf_file='input.nc', output_file='output.csv', conversion_type='csv')
>>> convert_netcdf(netcdf_file='input.nc', output_file='output.shp', conversion_type='shapefile')

Functions:
----------
- convert_netcdf: Converts a NetCDF file into either a CSV or a Shapefile.

Parameters:
-----------
- netcdf_file (str): Path to the input NetCDF file.
- output_file (str): Path to the output file (CSV or Shapefile).
- conversion_type (str): Conversion type, either "csv" or "shapefile".
"""

import netCDF4
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

def convert_netcdf(netcdf_file, output_file, conversion_type="csv"):
    """
    Converts a NetCDF file to either a CSV or a Shapefile.

    Parameters:
    -----------
    netcdf_file : str
        Path to the input NetCDF file.
    output_file : str
        Path to the output file (CSV or Shapefile).
    conversion_type : str, optional
        Type of conversion ("csv" or "shapefile"), default is "csv".

    Returns:
    --------
    None
    """
    # Open the NetCDF file
    nc = netCDF4.Dataset(netcdf_file, mode="r")

    # Identify the primary dimension (subbasin) for alignment
    main_dim = "subbasin"
    main_dim_size = len(nc.dimensions[main_dim])

    # Initialize a dictionary to store extracted data
    data_dict = {}

    # Extract latitude and longitude for spatial data
    lat = nc.variables["lat"][:]
    lon = nc.variables["lon"][:]

    # Replace missing values (_FillValue) with NaN for lat/lon
    if "_FillValue" in nc.variables["lat"].ncattrs():
        fill_value = nc.variables["lat"].getncattr("_FillValue")
        lat = np.where(lat == fill_value, np.nan, lat)
    if "_FillValue" in nc.variables["lon"].ncattrs():
        fill_value = nc.variables["lon"].getncattr("_FillValue")
        lon = np.where(lon == fill_value, np.nan, lon)

    # Ensure latitude and longitude match the primary dimension size
    if len(lat) != main_dim_size or len(lon) != main_dim_size:
        raise ValueError("Latitude and longitude dimensions do not match the primary dimension.")

    # Add lat/lon to data dictionary for shapefile conversion
    if conversion_type == "shapefile":
        data_dict["lat"] = lat
        data_dict["lon"] = lon

    # Extract and process variables
    for var_name, variable in nc.variables.items():
        if var_name in data_dict or var_name == "crs":  # Skip redundant or CRS variables
            continue
        try:
            data = variable[:]
            if "_FillValue" in variable.ncattrs():
                fill_value = variable.getncattr("_FillValue")
                data = np.where(data == fill_value, np.nan, data)

            # Handle 1D variables
            if data.ndim == 1 and data.shape[0] == main_dim_size:
                data_dict[var_name] = data
            # Handle 2D variables (e.g., GRU with dimensions [subbasin, NGRU])
            elif data.ndim == 2 and data.shape[0] == main_dim_size:
                for i in range(data.shape[1]):
                    column_name = f"{var_name}_{i+1}"
                    data_dict[column_name] = data[:, i]
        except Exception as e:
            print(f"Skipping variable '{var_name}' due to mismatch or error: {e}")

    # Close the NetCDF file
    nc.close()

    # Convert extracted data to CSV or Shapefile
    if conversion_type == "csv":
        df = pd.DataFrame(data_dict)
        df.to_csv(output_file, index=False)
        print(f"NetCDF file successfully converted to CSV: {output_file}")
    elif conversion_type == "shapefile":
        df = pd.DataFrame(data_dict)
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
            crs="EPSG:4326"
        )
        gdf.to_file(output_file)
        print(f"NetCDF file successfully converted to a shapefile: {output_file}")
    else:
        raise ValueError("Unsupported conversion type. Use 'csv' or 'shapefile'.")
