# SPDX-License-Identifier: LGPL-3.0-or-later

#######################################################################

### MODULE : SETTINGS

#######################################################################


# --- Paths setting ---------------------------------------------------


import os
from pathlib import Path

# Repository root: scripts/config.py -> scripts/ -> root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data folder
DATA_DIR = (
    Path(os.environ.get("URBANTALES_DATA", PROJECT_ROOT.parent / "Data"))
    .expanduser()
    .resolve()
)

# Outputs
OUTPUT_DIR = (
    Path(os.environ.get("URBANTALES_OUTPUT", PROJECT_ROOT.parent / "Outputs"))
    .expanduser()
    .resolve()
)

# Sub folders of Data
PATH_3D = DATA_DIR / "UrbanTALES" / "3Dwind"
GEOREF_INPUT = DATA_DIR / "GeoReference" / "Georef_input"
GEOREF_OUTPUT = DATA_DIR / "GeoReference" / "Georef_output"


def check_paths():
    """
    Check to see if the “Data” folder exists; if not, display a clear message.
    """

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Data file not found : {DATA_DIR}\n"
            "Set the URBANTALES_DATA environment variable, for example:\n"
            "  export URBANTALES_DATA=/path/to/Data"
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --- Modules and classes importations -----------------------------------


from importlib import reload
import os
import scripts.grid as grid
import scripts.wind_grid as wgrid
import scripts.geo_grid as ggrid
import scripts.final_grid as fg
import scripts.metadata as mt
import scripts.netcdf as nc
import scripts.topo_raster as tr
import scripts.topo_raster_georef as trg
import scripts.raster as r

reload(grid)
reload(wgrid)
reload(ggrid)
reload(fg)
reload(mt)
reload(nc)
reload(tr)
reload(trg)
reload(r)

from scripts.metadata import Metadata
from scripts.netcdf import NetCdf
from scripts.topo_raster import TopoRaster
from scripts.topo_raster_georef import TopoRasterGeoref
from scripts.grid import Grid
from scripts.wind_grid import WindGrid
from scripts.geo_grid import GeoGrid
from scripts.final_grid import FinalGrid
