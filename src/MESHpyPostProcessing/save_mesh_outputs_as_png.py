import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import netCDF4 as nc
from datetime import timedelta
import xarray as xr
import matplotlib

def save_mesh_outputs_as_png(
    shapefile_path,
    netcdf_dir,
    ddb_path,
    varnames,
    filenames,
    cbar_labels,
    outdir,
    indices_to_save,
    mode='monthly',
    domain_name='Basin',
    cmap='gnuplot2_r',
    comid_field='COMID'  # <-- New optional argument
):
    """
    Generate and save static PNG plots of MESH model output variables for specific time slices.

    This function overlays MESH model output (e.g., discharge, snow, temperature) from NetCDF files 
    onto a shapefile representing subbasin polygons. For each variable and selected time index, a PNG 
    figure is generated with consistent colorbar scales and custom titles based on domain, variable, 
    and time.

    Parameters
    ----------
    shapefile_path : str
        Path to the shapefile (.shp) representing the subbasins with a 'COMID' field.
    netcdf_dir : str
        Directory containing the NetCDF output files.
    ddb_path : str
        Path to the NetCDF drainage database containing the 'subbasin' variable used for merging.
    varnames : list of str
        List of variable names to extract from each NetCDF file (e.g., ['QO', 'SNO']).
    filenames : list of str
        List of NetCDF filenames corresponding to each variable in `varnames`.
    cbar_labels : list of str
        List of labels for the colorbars corresponding to each variable.
    outdir : str
        Directory where output PNG figures will be saved.
    indices_to_save : list of int
        List of time indices to extract and plot (e.g., [0, 1, 5]).
    mode : {'daily', 'monthly', 'yearly', 'hourly'}, optional
        Time resolution of the data for labeling the figures. Default is 'monthly'.
    domain_name : str, optional
        Name of the domain used in the figure title. Default is 'Basin'.
    cmap : str, optional
        Matplotlib colormap to use for the plots. Default is 'gnuplot2_r'.

    Returns
    -------
    None
        Saves PNG image files to the specified output directory.

    Raises
    ------
    ValueError
        If an unsupported mode is provided for the `mode` parameter.

    Notes
    -----
    - Assumes that each NetCDF file contains a 'time' dimension and that values begin from index 1 (skipping index 0).
    - Automatically adjusts date labeling based on the selected time `mode`.
    - Supports automatic detection of layer (e.g., 'Layer1', 'Layer2') from filenames using 'IG1', 'IG2', etc.

    Example
    -------
    >>> save_mesh_outputs_as_png(
    ...     shapefile_path='shapes/sras_subbasins.shp',
    ...     netcdf_dir='outputs/monthly',
    ...     ddb_path='outputs/MESH_drainage_database.nc',
    ...     varnames=['QO', 'SNO'],
    ...     filenames=['QO_Y_GRD.nc', 'SNO_Y_GRD.nc'],
    ...     cbar_labels=['Discharge [m³/s]', 'Snow [mm]'],
    ...     outdir='outputs/pngs',
    ...     indices_to_save=[0, 3, 6],
    ...     mode='monthly',
    ...     domain_name='SrAs',
    ...     cmap='viridis'
    ... )
    """
    font = {'family': 'DejaVu Serif', 'weight': 'bold', 'size': 24}
    matplotlib.rc('font', **font)

    os.makedirs(outdir, exist_ok=True)

    db = xr.open_dataset(ddb_path)
    segid = db['subbasin'].values
    db.close()

    df = pd.DataFrame({'ID': segid})
    shp = gpd.read_file(shapefile_path).sort_values(by=comid_field).reset_index(drop=True)

    example_file = os.path.join(netcdf_dir, filenames[0])
    with nc.Dataset(example_file) as ds:
        time_var = ds.variables['time']
        time_units = time_var.units.replace('years', 'days')  # fallback fix
        times = time_var[:] * 365 if 'years' in time_var.units else time_var[:]
        calendar = getattr(time_var, 'calendar', 'standard')
        dates = nc.num2date(times, units=time_units, calendar=calendar)
        starting_date = dates[0]

    global_min_max = {}
    for i, fname in enumerate(filenames):
        with nc.Dataset(os.path.join(netcdf_dir, fname)) as ds:
            data = ds.variables[varnames[i]][:]
            global_min_max[varnames[i]] = (np.nanmin(data), np.nanmax(data))

    for i in range(len(varnames)):
        for idx in indices_to_save:
            fig, ax = plt.subplots(figsize=(20, 20))
            with nc.Dataset(os.path.join(netcdf_dir, filenames[i])) as ds:
                values = ds.variables[varnames[i]][idx, :]

            merge_df = shp.copy()
            df['value'] = values
            merged = merge_df.merge(df, left_on=comid_field, right_on='ID', how='left')

            mn, mx = global_min_max[varnames[i]]

            if 'IG1' in filenames[i]: layer = 'Layer1'
            elif 'IG2' in filenames[i]: layer = 'Layer2'
            elif 'IG3' in filenames[i]: layer = 'Layer3'
            else: layer = None

            # Handle time label
            if mode == 'yearly':
                date = starting_date + timedelta(days=365 * idx)
                label = date.strftime('%Y')
            elif mode == 'monthly':
                date = starting_date + timedelta(days=30 * idx)
                label = date.strftime('%Y-%m')
            elif mode == 'daily':
                date = starting_date + timedelta(days=idx)
                label = date.strftime('%Y-%m-%d')
            elif mode == 'hourly':
                date = starting_date + timedelta(hours=idx)
                label = date.strftime('%Y-%m-%d_%H:%M')
            else:
                raise ValueError("Invalid mode. Choose from 'daily', 'monthly', 'yearly', or 'hourly'.")

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
            filename = f"{varnames[i]}_{mode}_frame_{idx:03d}_{label.replace(':','-')}.png"
            fig.savefig(os.path.join(outdir, filename), dpi=300)
            plt.close(fig)
