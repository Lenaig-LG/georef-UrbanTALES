# Copyright (C) 2026 Lenaig Le Grognec
# Licensed under the GNU Lesser General Public License v3.0 or later.
# See COPYING.LESSER for details.

#######################################################################

### MODULE : PROCESSING OF ALL SCENARIOS

# This module starts the processing pipeline for all scenarios
# listed in scripts.scenario.py

#######################################################################


import pandas as pd
from importlib import reload

from scripts.config import *

from scripts.config import (
    PROJECT_ROOT,
    DATA_DIR,
    OUTPUT_DIR,
    PATH_3D,
    GEOREF_INPUT,
    GEOREF_OUTPUT,
    check_paths,
)

check_paths()

import scripts.functions as fct

# -----

# Open metadata file
m = Metadata(path_metadata=os.path.join(DATA_DIR, "UrbanTALES", "metadata.csv"))
print(m.metadata_df)

# -----

# Which geo domain do we focus on?
import scripts.scenario as scenario

reload(scenario)
from scripts.scenario import *

print("List of all scenarios : \n", scenario_list)
print("Number of scenarios : ", len(scenario_list))


# --- Process line ---

print("Starting the processing chain : ")
for filename in scenario_list:
    print(
        "-------------------------------------- \n",
        filename,
        "\n--------------------------------------",
    )

    print(
        f"Metada of {filename} : \n", m.metadata_df[m.metadata_df["NameE"] == filename]
    )

    # filename = filenames_list[0]
    # filename = "CN-Bei-V1_d15"
    print(filename)
    if (
        fct.find_final_grid(filename=filename, georef_output=GEOREF_OUTPUT, res=50)
        == True
    ):
        print("✅ Georef processing already done!")
        continue
    else:
        # nc_code = m.metadata_df["NameI"][m.metadata_df["NameE"] == filename].iloc[0]
        # if pd.isna(nc_code) or not str(nc_code).strip():
        #     print(f"NameI (nc file code) is empty: {nc_code}.")
        # nc_file = f"{nc_code}_data.nc"
        # nc_path = os.path.join(PATH_3D, nc_file)
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
            path_3d_folder=PATH_3D,
            georef_input=GEOREF_INPUT,
        )

        nc.nc_xr
        nc.process_nc(overwrite=False)

        # ---

        # # Add name_topo of the domain
        # # filename = "UA-Kyi-V5_d00"
        # # metadata = m.metadata_df
        # df = m.metadata_df

        # # Finding line which NameE begins with filename
        # match_df = df[df["NameE"].astype(str) == str(filename)]
        # # match_df["angle_domain"] = pd.NA

        # if not match_df.empty:
        #     # We retrieve first correspondence
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
            georef_input=GEOREF_INPUT,
            georef_output=GEOREF_OUTPUT,
            path_data=PATH_3D,
            m=m,
        )

        # # topo_test.dataset
        # # topo_test.close

        # ---
        # For georeference operations, we did not compute any classes and choose to use functions instead.

        fct.find_gcp(filename=filename, georef_input=GEOREF_INPUT)

        groovy_georef_path = os.path.join(
            PROJECT_ROOT,
            "groovy",
            "WindDataGDALCommands.groovy",
        )

        fct.georeferencement(
            filename_e=filename,
            topo=topo_test,
            georef_input=GEOREF_INPUT,
            georef_output=GEOREF_OUTPUT,
            path_data=DATA_DIR,
            groovy_path=groovy_georef_path,
        )
        # The georeferenced topo file is loaded with another class
        topo_georef = TopoRasterGeoref(filename_e=filename, georef_output=GEOREF_OUTPUT)
        topo_georef.to_geojson(viz=True)  # save into geojson

        # # Add angle value of the domain
        # # metadata = m.metadata_df
        # df = m.metadata_df

        # # Finding line which NameE begins with filename
        # match_df = df[df["NameE"].astype(str) == str(filename)]
        # # match_df["angle_domain"] = pd.NA

        # if not match_df.empty:
        #     # We retrieve first correspondence
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
        #         "Enter the angle value manually (no match in NameE)."
        #     )

        # Construction of the base grid
        base_grid = Grid(
            georef_output=GEOREF_OUTPUT,
            path_data=DATA_DIR,
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
        groovy_path_eb = os.path.join(PROJECT_ROOT, "Groovy", "extractBuilding.groovy")
        groovy_path_geo = os.path.join(
            PROJECT_ROOT, "Groovy", "geoClimateIndicators.groovy"
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
