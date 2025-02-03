import os
import pandas as pd

def generate_mesh_class_ini_from_excel(excel_file, output_file, selected_land_covers, num_cels, lat, lon):
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
    >>> generate_mesh_ini_from_excel("meshparameters.xlsx", "MESH_output.ini", ["Forest", "crop"],num_cels=7408, lat=53.18, lon=-99.25)

    """
    # Load Excel file
    df = pd.read_excel(excel_file, sheet_name='Sheet1')
    df.columns = df.columns.str.lower()  # Normalize column names to lowercase for case insensitivity
    df['par'] = df['par'].str.lower()    # Normalize parameter names

    # Define vegetation columns
    vegetation_cols = ['v_nforest', 'v_bforest', 'v_crop', 'v_grass', 'v_bare']

    # Parameters that should be replaced with empty space when assign_col == 'v_bare'
    empty_space_params = {'lamx', 'lamn', 'cmas', 'root', 'qa50', 'vpdp', 'psgb', 'psga', 'vpda', 'rsmn'}
    empty_space = " " * 8  # Fixed length of empty space

    # Ensure 'colum' row exists
    colum_row = df[df['par'] == 'colum']
    if colum_row.empty:
        raise ValueError("The 'colum' row is missing in the provided Excel file.")
    # Compute the length dynamically
    land_cover_count = len(selected_land_covers)
    #print(land_cover_count)
    with open(output_file, 'w') as f:
        # Write header
        f.write("Basin\n")
        f.write("Author\n")
        f.write("Org\n")
        f.write(f"     {lat}     {lon}     40.00     40.00     50.00   -1.0    1 {num_cels}    {land_cover_count}\n")

        for lc in selected_land_covers:
            lc_lower = lc.lower()
            if lc_lower not in df.columns:
                raise ValueError(f"Land cover '{lc}' is not found in the Excel columns.")

            #f.write(f"# Land Cover: {lc}\n")

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
                    values = {col: f"{0.000:8.3f}" for col in vegetation_cols}  # Default is zero

                    if param in df['par'].values:
                        if param in empty_space_params:
                            values['v_bare'] = empty_space
                        assigned_col = colum_row[lc_lower].values[0].lower()
                        if assigned_col in vegetation_cols:
                            #print(assigned_col)
                            try:
                                if assigned_col == 'v_bare' and param in empty_space_params:
                                   # values[assigned_col] = empty_space  # Replace with empty space for specific parameters
                                    print(values['v_bare'])
                                else:
                                    values[assigned_col] = f"{float(df[df['par'] == param][lc_lower].values[0]):8.3f}"
                            except (ValueError, IndexError):
                                values[assigned_col] = f"{0.000:8.3f}"
                    values_pair.append(values)

                # Write both parameters in one line
                f.write("  " + "   ".join(values_pair[i][col] for i in range(len(pair)) for col in vegetation_cols) + f"  # {', '.join(pair)}\n")

            # Block 2: One-to-One Parameter Assignments
            one_to_one_pairs = [
                ('drn', 'sdep', 'fare', 'dden'),
                ('xslp', 'grkf', 'man', 'wfci', 'mid', 'name')
            ]
            for pair in one_to_one_pairs:
                values_pair = []
                for param in pair:
                    if param in df['par'].values:
                        try:
                            if param == "name":
                                param_value = str(df[df['par'] == param][lc_lower].values[0]) if lc_lower in df.columns else "N/A"
                            else:
                                param_value = float(df[df['par'] == param][lc_lower].values[0]) if lc_lower in df.columns else 0.000    
                        except (ValueError, IndexError):
                            param_value = "N/A" if param == "name" else 0.000
                        values_pair.append(f"{param_value:8.3f}" if param != "name" else f"{param_value:>8}")
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

# Example usage , num_cels, lat, lon
#generate_mesh_class_ini_from_excel("/content/drive/MyDrive/ColabNotebook_FY/meshparametersvalues1.xlsx", "MESH_output.ini", ["Forest", "crop"],num_cels=7408, lat=53.18, lon=-99.25)
