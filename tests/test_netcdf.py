from importlib import reload
import os

import Python.Package.metadata as mt
import Python.Package.netcdf as nc

reload(mt)
reload(nc)

from Python.Package.metadata import Metadata
from Python.Package.netcdf import NetCdf


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

# ---

m = Metadata(path_metadata=os.path.join(path_data, "Copie_UrbanTALES", "metadata.csv"))
m.metadata_df

# ---

filename = "FR-Par-V2_d30"

nc = NetCdf(
    filename_e=filename, metadata=m, path_3d_folder=path_3D, georef_input=georef_input
)

nc.nc_xr
nc.to_raster(overwrite=True)
