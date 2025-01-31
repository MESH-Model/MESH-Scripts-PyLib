"""
Basin and River Network Aggregation
===================================

The `merit_basin_aggregation` function aggregates basin and river network shapefiles.
This function uses parameters like minimum sub-area, slope, and river length to iteratively
aggregate small sub-basins.

Parameters:
------------
- `input_basin`: Basin GeoDataFrame with COMID identifiers.
- `input_river`: River network GeoDataFrame with slope and length attributes.
- `min_subarea`: Minimum area for sub-basins.
- `min_slope`: Minimum allowable river slope.
- `min_length`: Minimum river length.

This function iterates through sub-basins, merging those below the minimum sub-area
threshold until no further aggregation is possible. It also computes and adjusts slopes,
river lengths, and weighted slopes for simplified river networks.

Example usage:
--------------

>>> from MESHpyPreProcessing.Aggregation_vector import merit_basin_aggregation
>>> import geopandas as gpd
>>> import os

>>> # Define paths and parameters
>>> input_basin_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/SrsAboine-geofabric/sras_subbasins_MAF_noAgg.shp"
>>> input_river_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/SrsAboine-geofabric/sras_rivers_MAF_noAgg.shp"
>>> min_subarea = 50
>>> min_slope = 0.0000001
>>> min_length = 1.0
>>> output_basin_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/sras_subbasins_MAF_Agg.shp"
>>> output_river_path = "/home/fuaday/github-repos/Souris_Assiniboine_MAF/1-geofabric/sras_rivers_MAF_Agg.shp"

>>> # Load input data
>>> input_basin = gpd.read_file(input_basin_path)
>>> input_river = gpd.read_file(input_river_path)

>>> # Perform aggregation
>>> agg_basin, agg_river = merit_basin_aggregation(input_basin, input_river, min_subarea, min_slope, min_length)

>>> # Save aggregated data
>>> agg_basin.to_file(output_basin_path)
>>> agg_river.to_file(output_river_path)
"""
import pandas as pd
import geopandas as gpd
import numpy as np
import os
 
def merit_basin_aggregation(input_basin, input_river, min_subarea, min_slope, min_length):
#    input_basin = input_basin.make_valid()
#    input_river = input_river.make_valid()
    input_river['slope'] = input_river['slope'].clip(lower=min_slope)
    input_river.loc[input_river['slope'] >= 1.0, 'slope'] = min_slope
    input_river['lengthkm'] = input_river['lengthkm'].clip(lower=min_length)
    input_basin = input_basin.merge(input_river[['COMID', 'NextDownID', 'uparea']].copy(), on='COMID', how='left')
    input_basin['agg'] = input_basin['COMID']
    input_basin['aggdown'] = input_basin['NextDownID']
    agg_basin = input_basin[['agg', 'aggdown', 'unitarea', 'uparea']].copy()
    agg_basin = agg_basin[~((agg_basin['aggdown'] <= 0) & (agg_basin['uparea'] < min_subarea))]
    NoSubbasin = len(input_basin)
    while True:
        # Aggregated the headwaters sub-basins
        small_subbasin = agg_basin[~agg_basin['agg'].isin(agg_basin['aggdown']) & (agg_basin['unitarea'] < min_subarea)].sort_values(by='uparea', ascending=False)
        if not small_subbasin.empty:
            small_subbasin = small_subbasin.rename(columns={'agg': 'aggold', 'aggdown': 'agg'})
            xx = small_subbasin.merge(agg_basin[['agg', 'aggdown']], on='agg', how='left')
            for i in range(len(xx)):
                input_basin.loc[input_basin['agg'] == xx['aggold'].iloc[i], 'aggdown'] = xx['aggdown'].iloc[i]
                input_basin.loc[input_basin['agg'] == xx['aggold'].iloc[i], 'agg'] = xx['agg'].iloc[i]
            agg_basin = input_basin.drop(columns='geometry').groupby(['agg', 'aggdown'], as_index=False).agg({'unitarea': 'sum'})
            agg_basin = agg_basin.rename(columns={'agg': 'COMID', 'aggdown': 'NextDownID'})
            agg_basin = agg_basin.merge(input_basin[['COMID', 'uparea']], on='COMID', how='left')
            agg_basin = agg_basin.rename(columns={'COMID': 'agg', 'NextDownID': 'aggdown'})
            agg_basin = agg_basin[~((agg_basin['aggdown'] <= 0) & (agg_basin['uparea'] < min_subarea))]
        # Aggregated the intermediate sub-basins 
        small_subbasin = agg_basin[agg_basin['agg'].isin(agg_basin['aggdown']) & (agg_basin['unitarea'] < min_subarea)].sort_values(by='uparea', ascending=False)
        if not small_subbasin.empty:
            for i in range(len(small_subbasin)):
                xx = input_basin[input_basin['COMID'] == small_subbasin['agg'].iloc[i]].index[0]
                if input_basin['unitarea'][input_basin['agg'] == input_basin['agg'].iloc[xx]].sum() < min_subarea:
                    xy = input_basin[input_basin['NextDownID'] == input_basin['COMID'].iloc[xx]].index
                    if not xy.empty:
                        xz = input_basin['uparea'].iloc[xy].idxmax()                        
                        zz = input_basin[input_basin['aggdown'] == input_basin.loc[xz, 'agg']].index        
                        input_basin.loc[input_basin['agg'] == input_basin['agg'].iloc[xz], 'agg'] = input_basin['agg'].iloc[xx]
                        input_basin.loc[input_basin['agg'] == input_basin['agg'].iloc[xz], 'aggdown'] = input_basin['aggdown'].iloc[xx]
                        if not zz.empty:
                            input_basin.loc[zz, 'aggdown'] = input_basin['agg'].iloc[xx]
 
            agg_basin = input_basin.drop(columns='geometry').groupby(['agg', 'aggdown'], as_index=False).agg({'unitarea': 'sum'})
            agg_basin = agg_basin.rename(columns={'agg': 'COMID', 'aggdown': 'NextDownID'})
            agg_basin = agg_basin.merge(input_basin[['COMID', 'uparea']], on='COMID', how='left')
            agg_basin = agg_basin.rename(columns={'COMID': 'agg', 'NextDownID': 'aggdown'})
            agg_basin = agg_basin[~((agg_basin['aggdown'] <= 0) & (agg_basin['uparea'] < min_subarea))]
        # Break if no small sub-basins are left        
        if len(agg_basin[agg_basin['unitarea'] < min_subarea]) == NoSubbasin:
            break
        NoSubbasin = len(agg_basin[agg_basin['unitarea'] < min_subarea])
    # Final aggregation the sub-basins
    agg_basin = input_basin.dissolve(by='agg', aggfunc={'unitarea': 'sum'}, as_index=False).rename(columns={'agg': 'COMID'})
    agg_basin = agg_basin.merge(input_basin[['COMID', 'aggdown', 'uparea']].copy(), on='COMID', how='left').rename(columns={'aggdown': 'NextDownID'})
    # Check for invalid geometries
#    invalid_geometries = agg_basin[~agg_basin.is_valid]
#    if not invalid_geometries.empty:
#        agg_basin = agg_basin.make_valid()
    # Aggregating river network based on the aggregated sub-basins    
    agg_river = input_river.merge(input_basin[['COMID', 'agg']].copy(), on='COMID', how='left')
    agg_river['mask'] = 0
    for i in agg_river['agg'].unique():
        xx = agg_river.index[agg_river['agg'] == i].tolist()
        while True:
            yy = agg_river['uparea'].iloc[xx].idxmax()
            agg_river.at[yy, 'mask'] = 1
            xx = agg_river.index[agg_river['NextDownID'] == agg_river['COMID'].iloc[yy]].tolist()
            if len(xx) < 1:
                break
    agg_river = agg_river[agg_river['mask'] == 1].copy()
    agg_river['slope'] = agg_river['slope'] * agg_river['lengthkm']
    # Final aggregation the river network
    agg_river = agg_river.dissolve(by='agg', aggfunc={'lengthkm': 'sum', 'slope': 'sum'}, as_index=False).rename(columns={'agg': 'COMID'})
    # Computes the weighted slope per length, checking for zero
    agg_river['slope'] = agg_river['slope'] / agg_river['lengthkm'].replace(0, np.nan)
    agg_river = agg_river.merge(agg_basin[['COMID', 'NextDownID', 'uparea']].copy(), on='COMID', how='left')
    agg_river = agg_river.merge(input_river[['COMID', 'order', 'hillslope']].copy(), on='COMID', how='left')
    # Check for invalid geometries
    invalid_geometries = agg_river[~agg_river.is_valid]
    if not invalid_geometries.empty:
        agg_river = agg_river.make_valid()
    return agg_basin, agg_river
 
 
