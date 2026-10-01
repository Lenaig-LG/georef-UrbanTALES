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

# -----


# Preliminary
path_git = os.path.join(
    "/home",
    "llegrogn",
    "Documents",
    "These_Lenaig_perso",
    "Lenaig_Le_Grognec",
    "4.Coding",
    "Projet_git",
)

path_data = os.path.join(path_git, "Data")
path_3D = os.path.join(path_data, "Copie_UrbanTALES", "3Dwind")

path_output = os.path.join(path_git, "Outputs")
os.makedirs(path_output, exist_ok=True)

path_work = os.path.join(path_git, "urban_wind_predict")

georef_input = os.path.join(path_data, "GeoReference", "Georef_input")
georef_output = os.path.join(path_data, "GeoReference", "Georef_output")
