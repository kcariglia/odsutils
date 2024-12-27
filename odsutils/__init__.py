from importlib.metadata import version
__version__ = version('odsutils')

try:
    import warnings
    from erfa import ErfaWarning
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
except ImportError:
    pass

from . import ods_engine