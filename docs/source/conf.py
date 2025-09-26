# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyGPT'
copyright = '2025, pygpt.net'
author = 'szczyglis-dev, Marcin Szczygliński'
release = '2.6.61'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
extensions = [
    'sphinx_rtd_theme',
    'myst_parser'
]

latex_elements = {
    'maketitle': '',  # No Title Page
    # ...
}

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 3,
}

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

language = 'en'
locale_dirs = ['locale/']   # path is example but recommended.
gettext_compact = False     # optional.