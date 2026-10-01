#######################################################################

### CLASS : GRID CREATION AND LOADING

#######################################################################


# --- Packages --------------------------------------------------------

import os
import subprocess
from shapely.geometry import Polygon, MultiPolygon

import shutil
import rasterio
import re
import matplotlib.pyplot as plt
import geopandas as gpd
from rasterio import features
from shapely.geometry import shape

# from matplotlib import colormaps
from rasterstats import zonal_stats
import pandas as pd

import matplotlib.cm as cm
import matplotlib.colors as colors


import numpy as np
import rasterio
from rasterio.features import geometry_mask

from shapely.geometry import Point
from rasterio.features import geometry_mask

from scripts.grid import Grid

# --- Define class ----------------------------------------------------


class GeoGrid:
    """
    Defines the geographic grid containing all geographical / morphological variables.
    Class composed by a Grid object.

    Attributes
    ----------
    grid : Grid
            A grid object on which the geographical variables will be computed.
    groovy_path_eb : str
        The path to the groovy script extractBuilding.groovy
    groovy_path_geo : str
            The path to the groovy script geoClimateIndicators.groovy
    """

    def __init__(self, grid: Grid, groovy_path_eb: str, groovy_path_geo: str):

        # --- Initialisation ---
        self.grid = grid
        self.groovy_path_eb = groovy_path_eb
        self.groovy_path_geo = groovy_path_geo
        self.target_resolution = grid.target_resolution

        # Retrieve grid_path (the path to the GeoJSON grid)
        folder = os.path.join(self.grid.georef_output, self.grid.filename_e)
        self.path_grid = self.grid._find_grid_file(
            folder=folder, target_resolution=self.grid.target_resolution
        )

        # --- Grid creation ---
        self._extract_buildings(self.groovy_path_eb)
        self.buildings_with_heights = self._attribute_heights()
        # Create grid
        output_grid = self._extract_geo_indic()
        self.gdf_geo_grid = gpd.read_file(output_grid)

    # ---------------------------------
    # ---------------------------------

    def _extract_buildings(
        self,
        groovy_path_eb,
    ):
        """
        Extract buildings and zone from GeoClimate with groovy script.
        """

        print("Begin Extract Buildings....")
        # nameE = self.wind_dict["nameE"]
        out_dir = os.path.join(self.grid.georef_output, self.grid.filename_e)

        # Groovy script path
        # groovy_path = os.path.join(path_git, "urban_wind_predict", "Groovy", "extractBuilding.groovy")

        # Execute Groovy script
        result = subprocess.run(
            [
                "groovy",
                groovy_path_eb,
                self.path_grid,
                out_dir,
            ],
            capture_output=True,  # pour récupérer stdout/stderr
            text=True,
        )

        print("Standard output :", result.stdout)
        print("Potential errors :", result.stderr)
        print("Output code :", result.returncode)
        print("End Extract buildings")

    # ---------------------------------
    # ---------------------------------

    def _find_building_file(self):
        """
        Search the file "building.fgb" in the osm_ folder and load it.
        """

        root_dir = os.path.join(self.grid.georef_output, self.grid.filename_e)

        for item in os.listdir(root_dir):
            osm_folder = os.path.join(root_dir, item)
            if os.path.isdir(osm_folder) and item.startswith("osm_"):
                # Check if building.fgb exists in this folder
                candidate = os.path.join(osm_folder, "building.fgb")
                if os.path.isfile(candidate):
                    building_path = candidate
                    break  # stop when correct file is retrieved

        if building_path:
            print(f"File found: {building_path}")
            gdf = gpd.read_file(building_path)
            return gdf
        else:
            raise FileNotFoundError(
                "No file 'building.fgb' found in the folder begining with 'osm_'."
            )

    # ---------------------------------
    # ---------------------------------

    @staticmethod
    def _remove_holes(geom):
        if geom.is_empty:
            return geom
        # If it is a polygon, keep only external shell
        if isinstance(geom, Polygon):
            return Polygon(geom.exterior)
        # If it is a multipolygon, repeat for each polygon
        elif isinstance(geom, MultiPolygon):
            return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])
        # Other types (LineString, Point, etc.) : don't touch it
        else:
            return geom

    # ---------------------------------
    # ---------------------------------

    def _attribute_heights(self):
        """
        This function attributes heights retrieved in UrbanTALES data to building geometries extracted from OSM.

        The function retrieve 2 paths:
        - fgb_path is the path to buildings geometries stored in fgb file, extracted from OSM with GeoClimate.
        - height_path is the path to buildings_heights used in UrbanTALES project retrieved from topo file.

        Return
        ------
        gpd.GeoDataFrame : a geoDataFrame with building geometries of buildings and associated heights.
        This file is also stored on local machine.
        """

        # Open files
        gdf_fgb = self._find_building_file()
        height_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "topo.geojson"
        )
        gdf_height = gpd.read_file(height_path)

        # Visualization
        plt.figure()
        gdf_height.plot(
            column="height",
            cmap="viridis_r",
            legend=True,
            figsize=(8, 8),
        )
        plt.title("Building heights used in UrbanTALES (in m)")
        plt.show()

        # CRS harmonization,
        print("CRS of OSM file: ", gdf_fgb.crs)
        print("CRS of topo file: ", gdf_height.crs)
        if gdf_fgb.crs != gdf_height.crs:
            gdf_height = gdf_height.to_crs(gdf_fgb.crs)
            print("CRS harmonized.")

        # --- Step 1 : Join with representative point (accurate heights) ---

        gdf_points = gdf_fgb.copy()
        gdf_points["geometry"] = gdf_points["geometry"].representative_point()

        gdf_join_within = gpd.sjoin(
            gdf_points,
            gdf_height[["height", "geometry"]],
            how="left",
            predicate="within",
        )[["ID_BUILD", "height"]]
        # gdf_join_within = gpd.sjoin(
        #     gdf_height[["height", "geometry"]],
        #     gdf_points,
        #     how="left",
        #     predicate="within",
        # )[["ID_BUILD", "height"]]

        # Merging heights with origin file
        gdf_fgb = gdf_fgb.merge(
            gdf_join_within, on="ID_BUILD", how="left", suffixes=("", "_within")
        )
        # gdf_fgb = gdf_join_within.merge(
        #     gdf_fgb, on="ID_BUILD", how="left", suffixes=("", "_within")
        # )

        # Visualization
        plt.figure()
        gdf_fgb.plot(
            column="height",
            cmap="viridis_r",
            legend=True,
            figsize=(8, 8),
        )
        plt.title("Building heights (m) after merging with representative points")
        plt.show()

        # --- Step 2 : Focus on buildings with no heights at this step ---

        missing = gdf_fgb[gdf_fgb["height"].isna()].copy()
        if len(missing) > 0:
            print(
                f"→ {len(missing)} buildings without height after 'within'. Attempt with 'intersects'."
            )

            # Spatial join with intersects
            gdf_join_intersects = gpd.sjoin(
                missing,
                gdf_height[["height", "geometry"]],
                how="left",
                predicate="intersects",
            )

            # Height mean if many intersections
            mean_height = (
                gdf_join_intersects.groupby("ID_BUILD")["height_right"]
                .mean()
                .reset_index()
            )

            # Complete missing values
            gdf_fgb = gdf_fgb.merge(
                mean_height, on="ID_BUILD", how="left", suffixes=("", "_intersects")
            )
            gdf_fgb["height"] = gdf_fgb["height"].fillna(gdf_fgb["height_right"])
            gdf_fgb.drop(columns=["height_right"], inplace=True)

        print(
            f"Heights attributed to {gdf_fgb['height'].notna().sum()} / {len(gdf_fgb)} buildings."
        )

        # --- Final visualisation ---
        plt.figure()
        gdf_fgb.plot(
            column="height",
            cmap="viridis_r",
            legend=True,
            figsize=(8, 8),
        )
        plt.title("Building heights (m) — hybrid method within + intersects")
        plt.show()

        # Remove buildings where we have no info on height
        gdf_fgb = gdf_fgb.dropna(subset=["height"])
        print(f"Before cleaning : {len(gdf_points)} buildings")
        print(f"After cleaning : {len(gdf_fgb)} buildings")

        # --- Step 3 : Remove holes in buildings only when it's in a one building ---

        # Application of remove_holes to the layer
        gdf_fgb["geometry"] = gdf_fgb["geometry"].apply(self._remove_holes)

        # --- Visualization ---
        plt.figure()
        gdf_fgb.plot(
            column="height",
            cmap="viridis_r",
            legend=True,
            figsize=(8, 8),
        )
        plt.title("Building heights (m) and inner courtyard removal")
        plt.show()

        # --- Save into fgb file ---
        output_path = os.path.join(
            self.grid.georef_output,
            self.grid.filename_e,
            "buildings_with_height.geojson",
        )
        gdf_fgb.to_file(output_path, driver="GeoJSON")
        print("File stored here:", output_path)
        return gdf_fgb

    # ---------------------------------
    # ---------------------------------

    def _extract_geo_indic(self):
        """
        Extract geographic indicators from OSM on a grid with GeoClimate.
        """

        # Groovy script
        # groovy_path_geo = os.path.join(
        #     self.wind_import.path_git,
        #     "urban_wind_predict",
        #     "Groovy",
        #     "geoClimateIndicators.groovy",
        # )

        print("Begin extract geo from grid ...")

        # Building heights file
        path_building = os.path.join(
            self.grid.georef_output,
            self.grid.filename_e,
            "buildings_with_height.geojson",
        )

        # Grid file
        # path_grid = self.path_grid

        # Output path
        output_grid = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "geo_grid.geojson"
        )
        # output_grid = "/tmp/lenaig/outputgrid.geojson"

        # Harmoniser CRS des bâtiments avec celui de la grille
        gdf_build = gpd.read_file(path_building)
        gdf_grid = gpd.read_file(self.path_grid)
        if gdf_build.crs != gdf_grid.crs:
            gdf_build = gdf_build.to_crs(gdf_grid.crs)
            gdf_build.to_file(path_building, driver="GeoJSON")

        # Execute Groovy script
        result = subprocess.run(
            [
                "groovy",  # language
                self.groovy_path_geo,  # path to groovy script
                path_building,  # path to heights + footprints of buildings
                self.path_grid,  # path to the grid
                output_grid,  # path to store output grid
                "cell_id",  # id of cells
            ],
            capture_output=True,  # to retrieve stdout/stderr
            text=True,
        )

        print("Standard output :", result.stdout)
        print("Potential errors :", result.stderr)
        print("Output code :", result.returncode)

        print("End extract geo !")
        return output_grid
