MESH-Scripts-PyLib Documentation
================================

**MESH-Scripts-PyLib** is a Python library for preprocessing and analyzing hydrometric, geospatial, and soil datasets for hydrological modeling. It provides tools for:

- Generating streamflow input files from USGS and EC sources
- Processing soil and land cover properties into model-ready formats
- Aggregating basin shapefiles and preparing spatial inputs
- Writing NetCDF files compatible with the MESH model
- Visualizing MESH input/output variables (e.g., discharge, snow, climate forcing)

.. note::
   This documentation is auto-generated from source code using Sphinx and updated regularly.

Badges
------

.. image:: https://readthedocs.org/projects/mesh-scripts-pylib/badge/?version=latest
   :target: https://mesh-scripts-pylib.readthedocs.io/en/latest/
   :alt: Documentation Status

.. image:: https://img.shields.io/github/license/fuadyassin/MESH-Scripts-PyLib
   :target: https://github.com/fuadyassin/MESH-Scripts-PyLib/blob/main/LICENSE
   :alt: License

.. image:: https://img.shields.io/github/stars/fuadyassin/MESH-Scripts-PyLib?style=social
   :target: https://github.com/fuadyassin/MESH-Scripts-PyLib/stargazers
   :alt: GitHub stars

.. image:: https://img.shields.io/github/forks/fuadyassin/MESH-Scripts-PyLib?style=social
   :target: https://github.com/fuadyassin/MESH-Scripts-PyLib/network/members
   :alt: GitHub forks

Installation
------------

Install the package directly from GitHub:

.. code-block:: bash

   pip install git+https://github.com/MESH-Model/MESH-Scripts-PyLib.git

Alternatively, you can clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/fuadyassin/MESH-Scripts-PyLib.git
   cd MESH-Scripts-PyLib
   pip install -e .

API Reference
-------------

.. toctree::
   :maxdepth: 1
   :caption: Python Modules

   modules

Jupyter Notebooks
-----------------

.. toctree::
   :maxdepth: 1
   :caption: Examples

   MESH_StreamflowFilePrep.ipynb
   Visualization.ipynb

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
