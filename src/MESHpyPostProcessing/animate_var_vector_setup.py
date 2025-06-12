"""
Temporal Animation of MESH Variables from Vector and NetCDF Data
=================================================================

This module generates animated GIFs of spatially-distributed MESH model outputs (e.g., Discharge, Snow, Precipitation)
over time using shapefiles and corresponding NetCDF files. It supports daily, monthly, and yearly animations.

The function processes time-aware variables stored in NetCDF files and overlays them on subbasin polygons, producing
frame-by-frame maps and exporting the animation as a `.gif` file using Matplotlib and Pillow.

-----------------------------------------------
Function: animate_mesh_outputs_to_gif
-----------------------------------------------

Description:
-------------
Generates animated visualizations for MESH model state or flux variables across subbasins, overlaying spatial values
on a shapefile with optional layer suffixes and colorbars. Output is saved as an animated `.gif`.

Parameters:
------------
- shapefile_path : str
    Path to the subbasin shapefile (must include a COMID field).
- netcdf_dir : str
    Directory containing NetCDF variable files (e.g., QO_M_GRD.nc, SNO_M_GRD.nc).
- ddb_path : str
    Path to the MESH drainage database NetCDF file used to extract subbasin IDs.
- varnames : list of str
    List of variable names to animate (e.g., ['QO', 'SNO', 'PREC']).
- filenames : list of str
    List of NetCDF filenames corresponding to each variable (same order as `varnames`).
- cbar_labels : list of str
    List of colorbar labels for each variable (e.g., ['Discharge [m³/s]', 'Snow Mass [mm]', 'Precipitation [mm]']).
- outdir : str
    Output directory to save the generated `.gif` files.
- mode : str, optional (default='monthly')
    Time mode for animation. Options: 'daily', 'monthly', or 'yearly'.
- domain_name : str, optional (default='Basin')
    Prefix to use in animated titles and output filenames.
- cmap : str, optional (default='gnuplot2_r')
    Matplotlib colormap to use for the animation.

Input Format:
--------------
1. Subbasin shapefile (.shp) with a `COMID` field
2. Drainage database (.nc) with `subbasin` variable
3. NetCDF model output files with time and subbasin dimensions

Output:
--------
- `.gif` animations for each variable saved in `outdir`
- Each frame shows spatial distribution for a time step
- Colorbars, labels, and layer info auto-handled

Example Usage:
---------------

>>> from MESHpyPostProcessing.animate_var_vector_setup import animate_mesh_outputs_to_gif


>>> animate_mesh_outputs_to_gif(
...     shapefile_path='D:/HydrologicalModels/MESH/Baseline/sras-agg-model_1/sras_MESH_PostProcessing/GIS/sras_subbasins_MAF_Agg.shp',
...     netcdf_dir='D:/HydrologicalModels/MESH/Baseline/sras-agg-model_1/sras_MESH_PostProcessing/BASINAVG4',
...     ddb_path='D:/HydrologicalModels/MESH/Baseline/sras-agg-model_1/MESH-sras-agg/MESH_drainage_database.nc',
...     varnames=['QO', 'SNO', 'PREC'],
...     filenames=['QO_Y_GRD.nc', 'SNO_Y_GRD.nc', 'PREC_Y_GRD.nc'],
...     cbar_labels=['Discharge [m³/s]', 'Snow Mass [mm]', 'Precipitation [mm]'],
...     outdir='D:/Coding/GitHub/Repos/MESH-Scripts-PyLib/MESHpyPostProcessing/ExampleFiles/Outputs',
...     mode='Yearly',
...     domain_name='SrAs'
... )

>>> # This will create animated GIFs for each variable in the specified output directory.
>>> # The GIFs will be named as follows:    

>>> # QO_yearly_animation.gif
>>> # SNO_yearly_animation.gif
>>> # PREC_yearly_animation.gif

.. image:: Figures/SNO_yearly_animation.gif
   :width: 600
   :alt: SNOW Output Animation
   :align: center

.. image:: Figures/PREC_yearly_animation.gif
   :width: 600
   :alt: Precipitation Output Animation
   :align: center   

Dependencies:
-------------
- geopandas
- matplotlib
- netCDF4
- pandas
- numpy
- xarray
- Pillow (via matplotlib.animation.PillowWriter)
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import netCDF4 as nc
from matplotlib.animation import FuncAnimation, PillowWriter
from datetime import timedelta
import xarray as xr
import matplotlib

def animate_mesh_outputs_to_gif(
    shapefile_path,
    netcdf_dir,
    ddb_path,
    varnames,
    filenames,
    cbar_labels,
    outdir,
    mode='monthly',
    domain_name='Basin',
    cmap='gnuplot2_r',
    comid_field='COMID'  # <-- New optional argument
):
    font = {'family': 'DejaVu Serif', 'weight': 'bold', 'size': 24}
    matplotlib.rc('font', **font)

    os.makedirs(outdir, exist_ok=True)

    db = xr.open_dataset(ddb_path)
    segid = db['subbasin'].values
    db.close()

    df = pd.DataFrame({'ID': segid})
    shp = gpd.read_file(shapefile_path).sort_values(by=comid_field).reset_index(drop=True)

    # Read one file to get time dimension
    example_file = os.path.join(netcdf_dir, filenames[0])
    with nc.Dataset(example_file) as ds:
        time_var = ds.variables['time']
        time_units = time_var.units
        times = time_var[:] * 365 if 'years' in time_units else time_var[:]
        time_units = time_units.replace('years', 'days')  # fix units if needed
        calendar = getattr(time_var, 'calendar', 'standard')
        dates = nc.num2date(times, units=time_units, calendar=calendar)
        starting_date = dates[0]
        date_range_length = len(dates)

    # Determine global min/max for each variable
    global_min_max = {}
    for i, fname in enumerate(filenames):
        with nc.Dataset(os.path.join(netcdf_dir, fname)) as ds:
            data = ds.variables[varnames[i]][:]
            global_min_max[varnames[i]] = (np.nanmin(data), np.nanmax(data))

    # Internal animation logic
    def animate_variable(i):
        def animate_frame(date_index):
            ax.clear()
            with nc.Dataset(os.path.join(netcdf_dir, filenames[i])) as ds:
                values = ds.variables[varnames[i]][date_index, :]

            merge_df = shp.copy()
            df['value'] = values
            merged = merge_df.merge(df, left_on=comid_field, right_on='ID', how='left')

            mn, mx = global_min_max[varnames[i]]

            if 'IG1' in filenames[i]: layer = 'Layer1'
            elif 'IG2' in filenames[i]: layer = 'Layer2'
            elif 'IG3' in filenames[i]: layer = 'Layer3'
            else: layer = None

            if mode == 'yearly':
                date = starting_date + timedelta(days=365 * date_index)
                label = date.strftime('%Y')
            elif mode == 'monthly':
                date = starting_date + timedelta(days=30 * date_index)
                label = date.strftime('%Y-%m')
            elif mode == 'daily':
                date = starting_date + timedelta(days=date_index)
                label = date.strftime('%Y-%m-%d')
            else:
                raise ValueError("Invalid mode. Choose from 'daily', 'monthly', 'yearly'.")

            title = f'{domain_name}_MESH_{varnames[i]}{"_" + layer if layer else ""}_{label}'
            ax.set_title(title)
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')

            norm = colors.Normalize(vmin=mn, vmax=mx) if mn != mx else None
            cmap_used = plt.cm.get_cmap(cmap)
            sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap_used)

            merged.plot(column='value', cmap=cmap, edgecolor='k', linewidth=0.1, ax=ax, vmin=mn, vmax=mx)

            cbar_ax = fig.add_axes([0.82, 0.2, 0.02, 0.6])
            fig.colorbar(sm, cax=cbar_ax, orientation='vertical', extend='max')
            cbar_ax.set_ylabel(cbar_labels[i])

            fig.subplots_adjust(left=0.05, right=0.80, top=0.95, bottom=0.05)

        fig, ax = plt.subplots(figsize=(20, 20))
        anim = FuncAnimation(fig, animate_frame, frames=date_range_length, repeat=False)
        output_path = os.path.join(outdir, f'{varnames[i]}_{mode}_animation.gif')
        anim.save(output_path, writer=PillowWriter(fps=2))
        plt.close(fig)

    # Generate animations
    for i in range(len(varnames)):
        animate_variable(i)
