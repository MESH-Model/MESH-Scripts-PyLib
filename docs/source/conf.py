# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import datetime

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../MESHpyPreProcessing/'))
sys.path.insert(0, os.path.abspath('../../MESHpyPostProcessing/'))


# -- Project information -----------------------------------------------------

project = 'MESH-Scripts-PyLib'
copyright = f'{datetime.datetime.now().year}, Fuad Yassin'
author = 'Fuad Yassin'
release = "1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx_automodapi.automodapi',
    'sphinx_automodapi.smart_resolver',
    'sphinx_rtd_theme',
    'sphinx.ext.autodoc',  # autodocument
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',  # google and numpy doc string support
    'sphinx.ext.mathjax',  # latex rendering of equations using MathJax
    'nbsphinx',  # for direct embedding of jupyter notebooks into sphinx docs
    'sphinx.ext.inheritance_diagram',
    'sphinx.ext.graphviz',
    'nbsphinx_link'
    ]
numpydoc_show_class_members = False

templates_path = ['_templates']
exclude_patterns = ['**.ipynb_checkpoints', '_build']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
pygments_style = 'sphinx'
html_context = {
  'display_github': True,
  'github_user': 'fuadyassin',
  'github_repo': 'MESH-Scripts-PyLib',
  'github_version': 'main/docs/source/'
}
# Options for inheritance diagrams
inheritance_graph_attrs = dict(rankdir="LR", size='"6.0, 8.0"', fontsize=12)
inheritance_node_attrs = dict(shape="ellipse", fontsize=12, color="blue", style="filled", fillcolor="lightgray")

# -- Napoleon autodoc options -------------------------------------------------
napoleon_numpy_docstring = True
