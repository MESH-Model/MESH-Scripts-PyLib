import geopandas as gpd
import pandas as pd

def flag_ncaalg(
    gdf1: gpd.GeoDataFrame,
    gdf2: gpd.GeoDataFrame,
    threshold: float = 0.1,  # Threshold set to 10% by default
    output_path: str = None,
    ncontr_col: str = "ncontr",  # User-defined column name for flag in gdf1
    value_column: str = None,    # Optional column in gdf2 for dynamic values
    initial_value=None           # Initial value for the ncontr_col in gdf1
) -> gpd.GeoDataFrame:
    """
    Flag intersections and optionally assign values from gdf2.

    This function identifies intersections between polygons in gdf1 and gdf2 that meet a specified
    threshold. If an intersection is found, a constant value (default is 2) or a value from a specified
    column in gdf2 (if provided) is assigned to the corresponding row in gdf1. If multiple intersections 
    exist, the first match is used.

    Parameters
    ----------
    gdf1 : gpd.GeoDataFrame
        The primary GeoDataFrame.
    gdf2 : gpd.GeoDataFrame
        The secondary GeoDataFrame with values to assign.
    threshold : float, optional
        The threshold for considering an intersection significant (default is 0.1 or 10%).
    output_path : str, optional
        Path where the modified gdf1 should be saved. If None, the file is not saved.
    ncontr_col : str, optional
        The name of the column to store assigned values in gdf1.
    value_column : str, optional
        The name of the column in gdf2 with values to assign to gdf1. If None, a constant value (2) is used.
    initial_value : optional
        The initial value to assign to the ncontr_col column in gdf1 before processing intersections.

    Returns
    -------
    gpd.GeoDataFrame
        The modified gdf1 with assigned values based on intersections.
    """
    # Initialize the target column with initial_value in gdf1
    gdf1[ncontr_col] = initial_value
    
    # Create spatial index for gdf2
    spatial_index = gdf2.sindex
    
    # Iterate over gdf1 using spatial indexing to find potential intersections
    for index, row in gdf1.iterrows():
        # Use spatial index to find potential intersections
        possible_matches_index = list(spatial_index.query(row['geometry'], predicate='intersects'))
        if not possible_matches_index:
            continue  # No intersections, move to next row
        
        # Filter possible matches for actual intersection
        possible_matches = gdf2.iloc[possible_matches_index]
        actual_intersections = possible_matches[possible_matches.intersects(row['geometry'])]
        
        # Calculate area fractions for actual intersections
        for _, match in actual_intersections.iterrows():
            intersection_area = row['geometry'].intersection(match['geometry']).area
            area_fraction = intersection_area / row['geometry'].area
            if area_fraction > threshold:
                # Assign either a constant value or a value from gdf2's value_column
                gdf1.at[index, ncontr_col] = match[value_column] if value_column else 2
                break  # Use only the first valid intersection to assign the value
                
    # Save the modified gdf1 to a new shapefile if an output path is provided
    if output_path is not None:
        gdf1.to_file(output_path)
    
    return gdf1

def flag_ncaalg_from_files(
    shapefile1: str,
    shapefile2: str,
    threshold: float = 0.1,  # Threshold set to 10% by default
    output_path: str = None,
    ncontr_col: str = "ncontr",  # User-defined column name for flag in gdf1
    value_column: str = None,    # Optional column in gdf2 for dynamic values
    initial_value=None           # Initial value for the ncontr_col in gdf1
) -> gpd.GeoDataFrame:
    """
    Read two shapefiles, set their CRS to EPSG:4326, and apply the `flag_ncaalg` function.

    Parameters
    ----------
    shapefile1 : str
        Path to the first shapefile.
    shapefile2 : str
        Path to the second shapefile.
    threshold : float, optional
        The threshold for considering an intersection significant, as a fraction of
        the first GeoDataFrame's polygon area (default is 0.1 for 10%).
    output_path : str, optional
        Path where the modified first GeoDataFrame should be saved. If None, the file is not saved.
    ncontr_col : str, optional
        The name of the column to flag intersections in gdf1.
    value_column : str, optional
        The name of the column in gdf2 with values to assign to gdf1.
    initial_value : optional
        The initial value to assign to the ncontr_col column in gdf1 before processing intersections.

    Returns
    -------
    gpd.GeoDataFrame
        The modified GeoDataFrame of the first GeoDataFrame with the specified column added.
    """
    # Read the shapefiles into GeoDataFrames
    gdf1 = gpd.read_file(shapefile1)
    gdf2 = gpd.read_file(shapefile2)

    # Set the CRS to EPSG:4326 in place
    gdf1.to_crs(epsg=4326, inplace=True)
    gdf2.to_crs(epsg=4326, inplace=True)

    # Call the original flag_ncaalg function with the specified column name, value column, and initial value
    return flag_ncaalg(gdf1, gdf2, threshold, output_path, ncontr_col, value_column, initial_value)

# Examples:

# 1. Default usage without initial value, constant value assignment (default is 2):
# flagged_gdf = flag_ncaalg_from_files(input_basin_path, nctr_test, threshold=0.1, output_path=output_river_path)

# 2. Using a value column from gdf2, still with default initialization (None):
# flagged_gdf = flag_ncaalg_from_files(input_basin_path, nctr_test, threshold=0.1, output_path=output_river_path, value_column="NON_ID")

# 3. Default usage with initial value set to 0, constant value assignment:
# flagged_gdf = flag_ncaalg_from_files(input_basin_path, nctr_test, threshold=0.1, output_path=output_river_path, initial_value=0)

# 4. Using a value column from gdf2 with initial value set to 0:
# flagged_gdf = flag_ncaalg_from_files(input_basin_path, nctr_test, threshold=0.1, output_path=output_river_path, value_column="NON_ID", initial_value=0)
