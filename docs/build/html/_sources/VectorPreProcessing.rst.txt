VectorPreProcessing package
===========================

Submodules
----------

VectorPreProcessing.Aggregation\_vector module
----------------------------------------------

.. automodule:: VectorPreProcessing.Aggregation_vector
   :members:
   :undoc-members:
   :show-inheritance:

VectorPreProcessing.NetCDFWriter module
---------------------------------------

.. automodule:: VectorPreProcessing.NetCDFWriter
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

VectorPreProcessing.convert\_ddbnetcdf module
---------------------------------------------

.. automodule:: VectorPreProcessing.convert_ddbnetcdf
   :members:
   :undoc-members:
   :show-inheritance:

VectorPreProcessing.gdf\_edit module
------------------------------------

.. automodule:: VectorPreProcessing.gdf_edit
   :members:
   :undoc-members:
   :show-inheritance:

VectorPreProcessing.gsde\_soil module
-------------------------------------

.. automodule:: VectorPreProcessing.gsde_soil
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:

VectorPreProcessing.remap\_climate\_to\_ddb module
--------------------------------------------------

.. automodule:: VectorPreProcessing.remap_climate_to_ddb
   :members:
   :undoc-members:
   :show-inheritance:

SLURM Script Usage
------------------

This SLURM script demonstrates how to use the functions
``remap_rdrs_climate_data`` and ``remap_rdrs_climate_data_single_year`` in an HPC environment.

Typical Usage
^^^^^^^^^^^^^

Run all sections in a single job:

.. code-block:: bash

   sbatch Forcing_RDRS_processingMet3.sh --section1 --section2 --section3

Run each year in parallel using SLURM array jobs:

.. code-block:: bash

   sbatch --array=0-38 Forcing_RDRS_processingMet3.sh --section1

SLURM Shell Script
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   #!/bin/bash
   #SBATCH --account=rpp-kshook
   #SBATCH --nodes=1
   #SBATCH --tasks-per-node=1
   #SBATCH --mem-per-cpu=30G
   #SBATCH --time=24:00:00
   #SBATCH --job-name=vectForcRDRS
   #SBATCH --mail-user=fuad.yassin@usask.ca
   #SBATCH --mail-type=BEGIN,END,FAIL

   : '
   This script processes climate forcing data for the vector-based MESH RDRS dataset.
   Supports array jobs and all-years processing.
   '

   module load cdo
   module load nco

   basin="sras"
   start_year=1980
   end_year=2018
   input_forcing_easymore='/scratch/fuaday/sras-agg-model/easymore-outputs'
   ddb_remapped_output_forcing='/scratch/fuaday/sras-agg-model/easymore-outputs2'
   input_basin='/scratch/fuaday/sras-agg-model/geofabric-outputs/sras_subbasins_MAF_Agg.shp'
   input_ddb='/scratch/fuaday/sras-agg-model/MESH-sras-agg/MESH_drainage_database.nc'
   dir_merged_file="/scratch/fuaday/sras-agg-model/easymore-outputs-merged"
   merged_file="${dir_merged_file}/${basin}_rdrs_${start_year}_${end_year}_v21_allVar.nc"

   source $HOME/virtual-envs/scienv/bin/activate
   module load StdEnv/2020
   module load gcc/9.3.0
   module restore scimods
   module load cdo
   module load nco

   function run_section1_single_year {
       local year=$1
       python -c "
   import sys
   sys.path.append('$HOME/virtual-envs/scienv/lib/python3.8/site-packages')
   from MESHpyPreProcessing.remap_rdrs_climate_data import remap_rdrs_climate_data_single_year
   remap_rdrs_climate_data_single_year(
       input_directory='$input_forcing_easymore',
       output_directory='$ddb_remapped_output_forcing',
       input_basin='$input_basin',
       input_ddb='$input_ddb',
       year=$year
   )
   "
   }

   function run_section1_all_years {
       python -c "
   import sys
   sys.path.append('$HOME/virtual-envs/scienv/lib/python3.8/site-packages')
   from MESHpyPreProcessing.remap_rdrs_climate_data import remap_rdrs_climate_data
   remap_rdrs_climate_data(
       input_directory='$input_forcing_easymore',
       output_directory='$ddb_remapped_output_forcing',
       input_basin='$input_basin',
       input_ddb='$input_ddb',
       start_year=$start_year,
       end_year=$end_year
   )
   "
   }

   function run_section2 {
       mkdir -p "$dir_merged_file"
       merge_cmd="cdo mergetime"
       for (( year=$start_year; year<=$end_year; year++ )); do
           merge_cmd+=" ${ddb_remapped_output_forcing}/remapped_remapped_ncrb_model_${year}*.nc"
       done
       $merge_cmd "$merged_file"
   }

   function run_section3 {
       ncatted -O -a units,RDRS_v2.1_P_TT_09944,o,c,"K" "$merged_file"
       ncatted -O -a units,RDRS_v2.1_P_P0_SFC,o,c,"Pa" "$merged_file"
       ncatted -O -a units,RDRS_v2.1_P_UVC_09944,o,c,"m s-1" "$merged_file"
       ncatted -O -a units,RDRS_v2.1_A_PR0_SFC,o,c,"mm s-1" "$merged_file"

       temp_file="${dir_merged_file}/${basin}_temp.nc"
       cdo -z zip -b F32 -aexpr,'RDRS_v2.1_P_TT_09944=RDRS_v2.1_P_TT_09944 + 273.15; RDRS_v2.1_P_P0_SFC=RDRS_v2.1_P_P0_SFC * 100.0; RDRS_v2.1_P_UVC_09944=RDRS_v2.1_P_UVC_09944 * 0.514444; RDRS_v2.1_A_PR0_SFC=RDRS_v2.1_A_PR0_SFC / 3.6' "$merged_file" "$temp_file"
       mv "$temp_file" "$merged_file"
   }

   for arg in "$@"; do
       case $arg in
           --section1)
               if [ -z "$SLURM_ARRAY_TASK_ID" ]; then
                   run_section1_all_years
               else
                   year=$((start_year + SLURM_ARRAY_TASK_ID))
                   run_section1_single_year $year
               fi
               ;;
           --section2)
               run_section2
               ;;
           --section3)
               run_section3
               ;;
       esac
   done

Module contents
---------------

.. automodule:: VectorPreProcessing
   :members:
   :undoc-members:
   :show-inheritance:
