MESH-Scripts-PyLib IO Documentation
=====================================

**MESH-Scripts-PyLib** is a Python library for preprocessing hydrometric and soil data, performing spatial analysis, and generating NetCDF files for use in hydrological modeling. The package includes utilities for:

- Streamflow file preparation
- Soil data processing
- Spatial analysis
- NetCDF file generation

.. note::
   This project is under active development.

Installation
------------

You can install the package using pip directly from GitHub:

.. code-block:: bash

   pip install git+https://github.com/MESH-Model/MESH-Scripts-PyLib.git

Overview
--------

This library provides several utilities that streamline data preprocessing for hydrological models like MESH. The key functionalities include:

- **Streamflow Data Processing:** Extraction and processing of streamflow data from Canadian and US hydrometric sources.
- **Soil Data Handling:** Loading, merging, and cleaning soil data from CSV files.
- **Spatial Analysis:** Flagging non-contributing areas using GeoDataFrames.
- **Basin & River Aggregation:** Aggregation of basin and river networks with custom thresholds.
- **NetCDF Generation:** Writing processed soil data to NetCDF format for hydrological modeling.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Aggregation_vector
   NetCDFWriter
   convert_ddbnetcdf
   gdf_edit
   gen_streamflow_file
   gsde_soil
   remap_climate_to_ddb
   generate_mesh_class_ini_from_excel
   plt_var_from_vector_ddb_netcdf


Indices and Tables
------------------

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`
