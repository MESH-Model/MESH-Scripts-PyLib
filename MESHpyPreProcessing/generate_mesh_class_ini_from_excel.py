import os
import pandas as pd

def generate_mesh_class_ini_from_excel(excel_file, output_file, selected_land_covers):
    """
    Generates a MESH parameter file (.ini) using values from an Excel file.

    This function reads parameter values from an Excel sheet and structures them into
    a MESH-compatible `.ini` file, following the format of vegetation, one-to-one,
    and multi-value assignments.

    Parameters:
    ------------
    excel_file : str
        Path to the Excel file containing parameter values.
    output_file : str
        Path to the output `.ini` file where processed values will be written.
    selected_land_covers : list of str
        A list of land cover types to include (case-insensitive). These land covers
        should match column names in the Excel file.

    File Structure:
    ----------------
    The output file consists of:
    1. **Header Information**: Includes metadata such as location, author, and details.
    2. **Land Cover Blocks**: Each selected land cover is written separately, including:
       - Vegetation parameters (written in pairs)
       - One-to-One parameter assignments (written in pairs)
       - Multi-value parameter assignments (written in structured format)
    3. **Final Footer**: Contains three mandatory lines required for MESH processing.

    Example Usage:
    --------------
    >>> generate_mesh_ini_from_excel("meshparameters.xlsx", "MESH_output.ini", ["Forest", "crop"])

    """
    # Load Excel file
    df = pd.read_excel(excel_file, sheet_name='Sheet1')
    df.columns = df.columns.str.lower()  # Normalize column names to lowercase for case insensitivity
    df['par'] = df['par'].str.lower()    # Normalize parameter names

    # Define vegetation columns
    vegetation_cols = ['v_nforest', 'v_bforest', 'v_crop', 'v_grass', 'v_bare']

    # Ensure colum row exists
    colum_row = df[df['par'] == 'colum']
    if colum_row.empty:
        raise ValueError("The 'colum' row is missing in the provided Excel file.")

    with open(output_file, 'w') as f:
        # Write header
        f.write("NCRB\n")
        f.write("FuadYassin\n")
        f.write("ECCC\n")
        f.write("     53.18    -99.25     40.00     40.00     50.00   -1.0    1 6408    16\n\n")
        
        for lc in selected_land_covers:
            lc_lower = lc.lower()
            if lc_lower not in df.columns:
                raise ValueError(f"Land cover '{lc}' is not found in the Excel columns.")
            
            f.write(f"# Land Cover: {lc}\n")
            
            # Block 1: Vegetation Parameters
            vegetation_pairs = [
                ('fcan', 'lamx'),
                ('lnz', 'lamn'),
                ('alvc', 'cmas'),
                ('alir', 'root'),
                ('rsmn', 'qa50'),
                ('vpda', 'vpdp'),
                ('psga', 'psgb')
            ]
            for pair in vegetation_pairs:
                values_pair = []
                for param in pair:
                    values = {col: 0.000 for col in vegetation_cols}  # Default zero
                    if param in df['par'].values:
                        assigned_col = colum_row[lc_lower].values[0].lower()
                        if assigned_col in vegetation_cols:
                            try:
                                values[assigned_col] = float(df[df['par'] == param][lc_lower].values[0])
                            except (ValueError, IndexError):
                                values[assigned_col] = 0.000
                    values_pair.append(values)
                # Write both parameters in one line
                f.write("  " + "   ".join(f"{values_pair[i][col]:8.3f}" for i in range(len(pair)) for col in vegetation_cols) + f"  # {', '.join(pair)}\n")

            # Block 2: One-to-One Parameter Assignments
            one_to_one_pairs = [
                ('drn', 'sdep', 'fare', 'dden'),
                ('xslp', 'grkf', 'man', 'wfci', 'mid', 'name ')
            ]
            for pair in one_to_one_pairs:
                values_pair = []
                for param in pair:
                    if param in df['par'].values:
                        try:
                            param_value = float(df[df['par'] == param][lc_lower].values[0]) if lc_lower in df.columns else 0.000
                        except (ValueError, IndexError):
                            param_value = 0.000
                        values_pair.append(f"{param_value:8.3f}")
                    else:
                        values_pair.append(f"{0.000:8.3f}")
                f.write("  " + "   ".join(values_pair) + f"  # {', '.join(pair)}\n")

            # Block 3: Multi-Value Assignments
            multi_value_pairs = [
                ('sand',),
                ('clay',),
                ('org',),
                ('soit', 'cant', 'snot', 'pndt'),
                ('soiwf', 'soiif', 'pond'),
                ('rcan', 'scan', 'sno', 'albs', 'rho', 'gro')
            ]
            for pair in multi_value_pairs:
                values_pair = []
                for param in pair:
                    if param in df['par'].values:
                        raw_value = df[df['par'] == param][lc_lower].values[0]
                        if isinstance(raw_value, str) and '{' in raw_value:
                            values = raw_value.strip('{}').split(',')
                            try:
                                values = [float(v) for v in values]
                            except ValueError:
                                values = [0.000] * len(values)  # Default in case of parsing error
                        else:
                            try:
                                values = [float(raw_value)]
                            except ValueError:
                                values = [0.000]
                        values_pair.append("  " + "   ".join(f"{v:8.3f}" for v in values))
                    else:
                        values_pair.append("  " + f"{0.000:8.3f}")
                f.write("  " + "   ".join(values_pair) + f"  # {', '.join(pair)}\n")
            
            f.write("\n")  # Add a blank line to separate land cover blocks

        # Footer
        f.write("         0         0         0         0                                  20 (not used, but 4x integer values are required)\n")
        f.write("         0         0         0         0                                  21 (not used, but 4x integer values are required)\n")
        f.write("         0         0         0         0                                  22 IHOUR/IMINS/IJDAY/IYEAR\n")
    print(f"MESH parameter file '{output_file}' created successfully!")


# Example usage
# generate_mesh_class_ini_from_excel("/content/drive/MyDrive/ColabNotebook_FY/meshparametersvalues1.xlsx", "MESH_output.ini", ["Forest", "crop"])
