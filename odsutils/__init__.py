from importlib.metadata import version
__version__ = version('odsutils')

import warnings
from erfa import ErfaWarning
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=ErfaWarning)

from . import ods_engine