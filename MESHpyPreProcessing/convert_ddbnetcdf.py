import netCDF4
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import numpy as np


def convert_netcdf(netcdf_file, output_file, conversion_type="csv"):
    """
    Converts a NetCDF file to CSV or Shapefile.
    
    Parameters:
        netcdf_file (str): Path to the input NetCDF file.
        output_file (str): Path to the output file (CSV or Shapefile).
        conversion_type (str): Conversion type ("csv" or "shapefile").
        
    Returns:
        None
    """
    # Open the NetCDF file
    nc = netCDF4.Dataset(netcdf_file, mode="r")

    # Identify the primary dimension (subbasin) for alignment
    main_dim = "subbasin"
    main_dim_size = len(nc.dimensions[main_dim])

    # Initialize a dictionary to store data
    data_dict = {}

    # Extract latitude and longitude for shapefile conversion
    lat = nc.variables["lat"][:]
    lon = nc.variables["lon"][:]

    # Replace missing values (_FillValue) with NaN for lat/lon
    if "_FillValue" in nc.variables["lat"].ncattrs():
        fill_value = nc.variables["lat"].getncattr("_FillValue")
        lat = np.where(lat == fill_value, np.nan, lat)

    if "_FillValue" in nc.variables["lon"].ncattrs():
        fill_value = nc.variables["lon"].getncattr("_FillValue")
        lon = np.where(lon == fill_value, np.nan, lon)

    # Ensure latitude and longitude are valid
    if len(lat) != main_dim_size or len(lon) != main_dim_size:
        raise ValueError("Latitude and longitude dimensions do not match the primary dimension.")

    # Add latitude and longitude if creating a shapefile
    if conversion_type == "shapefile":
        data_dict["lat"] = lat
        data_dict["lon"] = lon

    # Process remaining variables from the NetCDF file
    for var_name, variable in nc.variables.items():
        if var_name in data_dict or var_name == "crs":  # Skip if already added or not a data variable
            continue

        try:
            # Read data, replacing _FillValue with NaN if specified
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

    # Convert data to the desired format
    if conversion_type == "csv":
        # Create a DataFrame and save to CSV
        df = pd.DataFrame(data_dict)
        df.to_csv(output_file, index=False)
        print(f"NetCDF file has been successfully converted to CSV: {output_file}")

    elif conversion_type == "shapefile":
        # Create a DataFrame
        df = pd.DataFrame(data_dict)
        # Create a GeoDataFrame with Point geometries
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
            crs="EPSG:4326"  # Set the CRS to WGS84
        )
        # Save the GeoDataFrame to a shapefile
        gdf.to_file(output_file)
        print(f"NetCDF file has been successfully converted to a point shapefile: {output_file}")

    else:
        raise ValueError("Unsupported conversion type. Use 'csv' or 'shapefile'.")
