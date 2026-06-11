# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
#

import subprocess
from pathlib import Path

# Add extensions
extensions = [
    "sphinxcontrib.openapi",
    'sphinx_toolbox.confval',
]

openapi_default_renderer = 'httpdomain'

project = "eln"
copyright = "2026, daphne4nfdi"
author = "daphne4nfdi"

html_logo = "_static/favicon.ico"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]


def run_openapi_generation(app):
    subprocess.run(
        ["python", Path(__file__).parent / "generate_openapi.py"], check=True
    )


def setup(app):
    app.connect("builder-inited", run_openapi_generation)
