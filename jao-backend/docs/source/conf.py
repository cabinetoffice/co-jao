import os
import sys
sys.path.insert(0, os.path.abspath('../src'))  # Point to src directory

# initialise django
import django
from django.conf import settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jao_backend.settings.dev')
    django.setup()

# Project information
project = 'JAO Backend'
copyright = '2025, Your Team'
author = 'Your Team'
release = '0.1.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
]

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Autosummary settings
autosummary_generate = True

# HTML theme
#html_theme = 'sphinx_rtd_theme'
html_theme = 'govuk_tech_docs_sphinx_theme'

html_static_path = ['_static']

html_theme_options = {
    "organisation": "Cabinet Office - People Group",
    "phase": "discovery"          # Agile project phase - see https://www.gov.uk/service-manual/agile-delivery
}

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'django': ('https://docs.djangoproject.com/en/stable/', 'https://docs.djangoproject.com/en/stable/_objects/'),
    'requests': ('https://requests.readthedocs.io/en/stable/', None),
}

# Source file suffixes
source_suffix = '.rst'
master_doc = 'index'

html_context = {
    "github_url": "https://github.com/cabinetoffice/co-jao",
    "conf_py_path": "docs/",
    "version": "main",
    "accessibility": "accessibility.md"
}

templates_path = ["_templates"]
