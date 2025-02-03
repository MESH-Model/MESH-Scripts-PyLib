import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import netCDF4 as nc
import matplotlib.colors as mcolors
import math
import numpy as np
"""
Variable Visualization from Vector and NetCDF Data
==================================================

This module provides a function to visualize spatial variables from a NetCDF file and overlay them on a shapefile.
It supports single-variable plots, land use-based grouped visualizations, and soil layer-specific representations.

Example Usage
-------------
>>> from plt_var_vector_setup import plt_var_from_vector_ddb_netcdf
>>> plt_var_from_vector_ddb_netcdf(
...     output_basin_path='basin.shp',
...     ddbnetcdf_path='data.nc',
...     variable_name='SoilMoisture',
...     save_path='output_plot.png'
... )

>>> plt_var_from_vector_ddb_netcdf(
...     output_basin_path='basin.shp',
...     ddbnetcdf_path='data.nc',
...     variable_name='LandCover',
...     landuse_classes=['Forest', 'Grassland', 'Urban'],
...     save_path='landcover_plot.png'
... )

Function Details
----------------
- plt_var_from_vector_ddb_netcdf: Plots a variable from a NetCDF file onto a spatial representation of a watershed.

Parameters
----------
- output_basin_path : str
    Path to the input basin shapefile.
- ddbnetcdf_path : str
    Path to the NetCDF file containing spatial data.
- variable_name : str
    Name of the variable to be visualized from the NetCDF file.
- save_path : str, optional (default='plot.png')
    Path where the output plot should be saved.
- text_location : tuple, optional (default=(0.55, 0.95))
    Location for the text annotation in percentage form.
- font_size : int, optional (default=10)
    Font size for labels and titles.
- cmap : str, optional (default='viridis')
    Colormap to be used for plotting the data.
- cbar_location : list, optional (default=[0.96, 0.15, 0.02, 0.7])
    Positioning of the color bar.
- subplot_adjustments : dict, optional
    Custom subplot adjustments if needed.
- subbasin_var : str, optional (default='subbasin')
    NetCDF variable corresponding to subbasin identifiers.
- comid_var : str, optional (default='COMID')
    Column name in the shapefile corresponding to subbasin identifiers.
- landuse_classes : list, optional
    List of land use classifications if applicable.
- grudim : str, optional (default='NGRU')
    NetCDF dimension representing different land use groups.
- grunames_var : str, optional (default='LandUse')
    NetCDF variable containing land use group names.
- soldim : str, optional (default='nsol')
    NetCDF dimension representing different soil layers.
"""
def plt_var_from_vector_ddb_netcdf(
    output_basin_path, 
    ddbnetcdf_path, 
    variable_name,
    save_path='plot.png',
    text_location=(0.55, 0.95), 
    font_size=10,
    cmap='viridis',  # Set the default colormap to 'viridis'
    cbar_location=[0.96, 0.15, 0.02, 0.7],  # Set default colorbar location
    subplot_adjustments=None,  # Optional: Custom subplot adjustments
    subbasin_var='subbasin',  # Default to 'subbasin'
    comid_var='COMID',  # Default to 'COMID'
    landuse_classes=None,  # Optional land use classes as a numpy array or list
    grudim='NGRU',    # from netcdf ddb
    grunames_var='LandUse',  # from netcdf ddb
    soldim='nsol'    # from netcdf parameter file
):
    # Load and dissolve the shapefile to get a single boundary sub_agg_gdf
    sub_agg_gdf = gpd.read_file(output_basin_path).to_crs(epsg=4326)
    dissolved_basin = sub_agg_gdf.dissolve().boundary

    # Load NetCDF data
    with nc.Dataset(ddbnetcdf_path) as dataset:
        variable_data = dataset.variables[variable_name][:]
        subbasin_ids = dataset.variables[subbasin_var][:].astype(int)
        variable_units = dataset.variables[variable_name].units
        
        # Extract latitude and longitude data
        latitudes = dataset.variables['lat'][:]
        longitudes = dataset.variables['lon'][:]
        
        # Check the dimensions of the variable
        dims = dataset.variables[variable_name].dimensions

        if len(dims) == 1:  # Case where the variable only depends on subbasin
            df = pd.DataFrame({
                variable_name: variable_data, 
                'lat': latitudes, 
                'lon': longitudes
            }, index=subbasin_ids)

            # Check for duplicate columns before merging
            duplicate_columns = set(df.columns).intersection(set(sub_agg_gdf.columns))
            if duplicate_columns:
                raise ValueError(f"Duplicate columns found during merge: {duplicate_columns}")

            sub_agg_ddb_merged_gdf = sub_agg_gdf.merge(df, left_on=comid_var, right_index=True, how='left')

            vmin, vmax = sub_agg_ddb_merged_gdf[variable_name].min(), sub_agg_ddb_merged_gdf[variable_name].max()

            # Plot the single variable with lat/lon as x and y axes
            fig, ax = plt.subplots(figsize=(8, 6))
            sub_agg_ddb_merged_gdf.plot(column=variable_name, ax=ax, cmap=cmap, legend=False, vmin=vmin, vmax=vmax)
            ax.set_title(variable_name, fontsize=font_size)
            ax.set_xlabel('Longitude', fontsize=font_size)
            ax.set_ylabel('Latitude', fontsize=font_size)
            dissolved_basin.plot(ax=ax, edgecolor='black', linewidth=1, facecolor='none')

        elif len(dims) == 2 and dims[1] == grudim:  # Case where the variable depends on subbasin and NGRU
            print ("len(dims) == 2 and dims[1] == grudim")
            landuse_classes = np.array(landuse_classes) if landuse_classes else dataset.variables[grunames_var][:]
            df = pd.DataFrame({landuse: variable_data[:, i] for i, landuse in enumerate(landuse_classes)}, index=subbasin_ids)

            # Check for duplicate columns before merging
            duplicate_columns = set(df.columns).intersection(set(sub_agg_gdf.columns))
            if duplicate_columns:
                raise ValueError(f"Duplicate columns found during merge: {duplicate_columns}")

            sub_agg_ddb_merged_gdf = sub_agg_gdf.merge(df, left_on=comid_var, right_index=True, how='left')

            percentage_pairs = [(landuse, round(sub_agg_ddb_merged_gdf[landuse].mean() * 100, 2)) for landuse in landuse_classes]
            sorted_landuse_columns, sorted_percentages = zip(*sorted(percentage_pairs, key=lambda x: x[1], reverse=True))

            num_plots = len(sorted_landuse_columns)
            num_rows = math.floor(math.sqrt(num_plots))
            num_cols = math.ceil(num_plots / num_rows) if num_rows > 0 else 1  # Ensure num_cols is defined even if num_rows is 0
            fig, axes = plt.subplots(num_rows, num_cols, figsize=(2 * num_cols, 2 * num_rows), sharex=True, sharey=True)

            cmap = plt.cm.get_cmap(cmap).copy()
            cmap.set_under('white', alpha=0)
            
            # Function to split title into two lines
            def split_title(title):
                words = title.split()
                split_point = len(words) // 2
                return ' '.join(words[:split_point]) + '\n' + ' '.join(words[split_point:])

            for i, (col, percent) in enumerate(zip(sorted_landuse_columns, sorted_percentages)):
                ax = axes.flatten()[i]
                sub_agg_ddb_merged_gdf.plot(column=col, ax=ax, cmap=cmap, vmin=0.01, vmax=1)
                dissolved_basin.plot(ax=ax, edgecolor='black', linewidth=1, facecolor='none')
                # Convert title to two lines
                title = split_title(col)
                ax.set_title(title, fontsize=font_size, ha='center')
                #ax.set_title(col, fontsize=font_size, ha='center')
                ax.text(text_location[0], text_location[1], f"{percent}%", transform=ax.transAxes, fontsize=font_size,
                        verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.5))
                ax.set_xticks([])
                ax.set_yticks([])

            for i in range(num_plots, axes.flatten().shape[0]):
                axes.flatten()[i].set_visible(False)

        elif len(dims) == 2 and dims[1] == soldim:  # Case where the variable depends on subbasin and NSOL
            print ("len(dims) == 2 and dims[1] ==  soldim")
            nsol = dataset.dimensions['nsol'].size
            soil_layer_classes = [f'{variable_name} Layer {i+1}' for i in range(nsol)]
            df = pd.DataFrame({soil_layer: variable_data[:, i] for i, soil_layer in enumerate(soil_layer_classes)}, index=subbasin_ids)

            # Check for duplicate columns before merging
            duplicate_columns = set(df.columns).intersection(set(sub_agg_gdf.columns))
            if duplicate_columns:
                raise ValueError(f"Duplicate columns found during merge: {duplicate_columns}")

            sub_agg_ddb_merged_gdf = sub_agg_gdf.merge(df, left_on=comid_var, right_index=True, how='left')

            num_plots = len(soil_layer_classes)
            num_rows = math.floor(math.sqrt(num_plots))
            num_cols = math.ceil(num_plots / num_rows) if num_rows > 0 else 1  # Ensure num_cols is defined even if num_rows is 0
            fig, axes = plt.subplots(num_rows, num_cols, figsize=(3 * num_cols, 3 * num_rows), sharex=True, sharey=True)

            cmap = plt.cm.get_cmap(cmap).copy()
            cmap.set_under('white', alpha=0)

            for i, col in enumerate(soil_layer_classes):
                ax = axes.flatten()[i]
                sub_agg_ddb_merged_gdf.plot(column=col, ax=ax, cmap=cmap, vmin=0.01, vmax=100)
                dissolved_basin.plot(ax=ax, edgecolor='black', linewidth=1)
                ax.set_title(col, fontsize=font_size, ha='center')
                ax.set_xticks([])
                ax.set_yticks([])
                percentage = variable_data[:, i].mean()
                ax.text(text_location[0], text_location[1], f"{percentage:.2f}%", transform=ax.transAxes, fontsize=font_size,
                        verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.5))

            for i in range(num_plots, axes.flatten().shape[0]):
                axes.flatten()[i].set_visible(False)

        else:
            raise ValueError(f"Unsupported variable dimensions for plotting: {dims}")

    if subplot_adjustments:
        fig.subplots_adjust(**subplot_adjustments)

    # Set default values for vmin and vmax
    if len(dims) == 1:
        vmin, vmax = sub_agg_ddb_merged_gdf[variable_name].min(), sub_agg_ddb_merged_gdf[variable_name].max()
    else:
        vmin = 0.01
        vmax = 1 if len(dims) == 2 and dims[1] == grudim else 100  # Set vmax based on the condition

    # Colorbar setup
    cbar_ax = fig.add_axes(cbar_location)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar.ax.tick_params(labelsize=10)
    cbar.set_label(f'{variable_name} ({variable_units})', fontsize=font_size)

    plt.savefig(save_path)
    plt.show()

