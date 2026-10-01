#


#

from importlib import reload
import os

import Python.Data_preparation.wind_import as wi
import Python.Package.grid as grid

reload(wi)
reload(grid)

from Python.Data_preparation.wind_import import WindImport
from Python.Package.grid import Grid

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
# path_work = os.path.join(path_git, "urban_wind_predict")
georef_input = os.path.join(path_data, "GeoReference", "Georef_input")
georef_output = os.path.join(path_data, "GeoReference", "Georef_output")

filename = "FR-Par-V2_d30"

wind_imported = WindImport(
    path_data=path_data,
    georef_input=georef_input,
    georef_output=georef_output,
    path_git=path_git,
)

wind_dict = wind_imported.retrieve_wind_info(filename_e=filename)
epsg = wind_dict["epsg"].to_epsg()

# Test
grid_test = Grid(
    georef_output=georef_output,
    path_data=path_data,
    filename_e=filename,
    buffer=20,
    target_resolution=100,
    epsg=epsg,
)
