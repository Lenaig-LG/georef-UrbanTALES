# Copyright (C) 2026 Lenaig Le Grognec
# Licensed under the GNU Lesser General Public License v3.0 or later.
# See COPYING.LESSER for details.

#
import sys
import os

project_path = "/home/llegrogn/Documents/These_Lenaig_perso/Lenaig_Le_Grognec/4.Coding/Projet_git/urban_wind_predict"
sys.path.append(project_path)
import pandas as pd
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

# import grid as grid
# import wind_grid as wgrid
# import geo_grid as ggrid
# import final_grid as fg
# import metadata as mt
# import netcdf as nc
# import topo_raster as tr
# import topo_raster_georef as trg
# import raster as r

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
import scripts.functions as fct

# from metadata import Metadata
# from netcdf import NetCdf
# from topo_raster import TopoRaster
# from topo_raster_georef import TopoRasterGeoref
# from grid import Grid
# from wind_grid import WindGrid
# from geo_grid import GeoGrid
# from final_grid import FinalGrid
# import functions as fct

reload(fct)

# -----


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
# -----

# Open metadata file
m = Metadata(path_metadata=os.path.join(path_data, "Copie_UrbanTALES", "metadata.csv"))
m.metadata_df

# -----

# Which geo domain do we focus on?
# from scripts.scenario import *

import scripts.scenario as scenario

reload(scenario)
from scripts.scenario import *

print(scenario_list)

for filename in scenario_list:

    # filename = filenames_list[0]
    # filename = "CN-Bei-V1_d15"
    print(filename)
    if (
        fct.find_final_grid(filename=filename, georef_output=georef_output, res=50)
        == True
    ):
        print("✅ Georef processing already done!")
        continue
    else:
        # nc_code = m.metadata_df["NameI"][m.metadata_df["NameE"] == filename].iloc[0]
        # if pd.isna(nc_code) or not str(nc_code).strip():
        #     print(f"NameI (nc file code) is empty: {nc_code}.")
        # nc_file = f"{nc_code}_data.nc"
        # nc_path = os.path.join(path_3D, nc_file)
        # if os.path.exists(nc_path):
        #     print(f"{nc_file} found at: {nc_path}")
        # else:
        #     print(f"File not found at: {nc_path}")

        wind_dict = m.retrieve_wind_info(filename)
        epsg = wind_dict["epsg"].to_epsg()

        # Load nc file
        nc = NetCdf(
            filename_e=filename,
            metadata=m,
            path_3d_folder=path_3D,
            georef_input=georef_input,
        )

        nc.nc_xr
        nc.process_nc(overwrite=False)

        # ---

        # # Add name_topo of the domain
        # # filename = "UA-Kyi-V5_d00"
        # # metadata = m.metadata_df
        # df = m.metadata_df

        # # Trouver la ligne dont le NameE commence par filename
        # match_df = df[df["NameE"].astype(str) == str(filename)]
        # # match_df["angle_domain"] = pd.NA

        # if not match_df.empty:
        #     # On récupère la première correspondance
        #     row = match_df.iloc[0]
        #     if pd.notna(row.get("name_topo")):
        #         name_topo = str(row["name_topo"])
        #         print(f"Topo file name retrieved from metadata : {name_topo}")
        #     else:
        #         print("Enter the topo name manually (name_topo empty in metadata)")
        #         # Determine the name of topo file from associated folder
        #         # name_topo = "FR-PA-V2_d00"
        #         # m.metadata_df = m.add_name_topo_to_metadata(name_topo=name_topo, filename_e=filename)

        # else:
        #     print("Enter the name of topo file manually (no correspondance in NameE)")

        # Open and process to raster the topo file used in UrbanTALES associated with the filename_e
        topo_test = TopoRaster(
            filename_e=filename,
            georef_input=georef_input,
            georef_output=georef_output,
            path_data=path_data,
            m=m,
        )

        # # topo_test.dataset
        # # topo_test.close

        # ---
        # For georeference operations, we did not compute any classes and choose to use functions instead.

        fct.find_gcp(filename=filename, georef_input=georef_input)

        groovy_georef_path = os.path.join(
            path_git, "urban_wind_predict", "Groovy", "WindDataGDALCommands.groovy"
        )

        fct.georeferencement(
            filename_e=filename,
            topo=topo_test,
            georef_input=georef_input,
            georef_output=georef_output,
            path_data=path_data,
            groovy_path=groovy_georef_path,
        )
        # The georeferenced topo file is loaded with another class
        topo_georef = TopoRasterGeoref(filename_e=filename, georef_output=georef_output)
        topo_georef.to_geojson(viz=True)  # save into geojson

        # # Add angle value of the domain
        # # metadata = m.metadata_df
        # df = m.metadata_df

        # # Trouver la ligne dont le NameE commence par filename
        # match_df = df[df["NameE"].astype(str) == str(filename)]
        # # match_df["angle_domain"] = pd.NA

        # if not match_df.empty:
        #     # On récupère la première correspondance
        #     row = match_df.iloc[0]
        #     if pd.notna(row.get("angle_domain")):
        #         angle = float(row["angle_domain"])
        #         print(f"Angle retrieved from metadata : {angle}")
        #     else:
        #         print("Enter the angle value manually (angle_domain empty in metadata)")
        #         # Determine the angle value at hand with QGIS
        #         # angle = 102.920
        #         # m.metadata_df = m.add_angle_to_metadata(angle=angle, filename_e=filename)

        # else:
        #     print(
        #         "Renseigner à la main la valeur d'angle (aucune correspondance dans NameE)"
        #     )

        # Construction of the base grid
        base_grid = Grid(
            georef_output=georef_output,
            path_data=path_data,
            filename_e=filename,
            buffer=20,
            target_resolution=50,
            epsg=epsg,
        )

        # base_grid.gdf_grid.head()
        # base_grid.epsg
        # a = base_grid._create_cell_id(base_grid.gdf_grid)

        # Creation of the wind grid from base grid
        wind_grid_test = WindGrid(base_grid, m)
        # wind_grid_test.gdf_wind_grid.head()

        # Creation of the geo grid from base grid
        groovy_path_eb = os.path.join(
            path_git, "urban_wind_predict", "Groovy", "extractBuilding.groovy"
        )
        groovy_path_geo = os.path.join(
            path_git, "urban_wind_predict", "Groovy", "geoClimateIndicators.groovy"
        )

        geo_grid_test = GeoGrid(
            base_grid, groovy_path_eb=groovy_path_eb, groovy_path_geo=groovy_path_geo
        )

        # We check if epsg codes are equals
        wind_grid_test.grid.epsg
        geo_grid_test.grid.epsg

        # # Insight on grids:
        # wind_grid_test.gdf_wind_grid.columns
        # geo_grid_test.gdf_geo_grid.head()
        # geo_grid_test.gdf_geo_grid.columns

        # The final grid is generated:
        final_grid_test = FinalGrid(wind_grid=wind_grid_test, geo_grid=geo_grid_test)
        # table = final_grid_test.final_grid

        print(f"End georef {filename}.")


# # Creation of the geo grid from base grid
# groovy_path_eb = os.path.join(
#     path_git, "urban_wind_predict", "Groovy", "extractBuilding.groovy"
# )
# groovy_path_geo = os.path.join(
#     path_git, "urban_wind_predict", "Groovy", "geoClimateIndicators.groovy"
# )

# geo_grid_test = GeoGrid(
#     base_grid, groovy_path_eb=groovy_path_eb, groovy_path_geo=groovy_path_geo
# )

# # We check if epsg codes are equals
# wind_grid_test.grid.epsg
# geo_grid_test.grid.epsg

# # Insight on grids:
# wind_grid_test.gdf_wind_grid.columns
# geo_grid_test.gdf_geo_grid.head()
# geo_grid_test.gdf_geo_grid.columns

# # The final grid is generated:

# final_grid_test = FinalGrid(wind_grid=wind_grid_test, geo_grid=geo_grid_test)
# # table = final_grid_test.final_grid


m.metadata_df[m.metadata_df["NameE"] == filename]
