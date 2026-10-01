#######################################################################

### CLASS : TOPO RASTER GEOREF CREATION AND LOADING

### Instantiate a georeferenced raster as object

#######################################################################


# --- Packages ------------------------------------------------------

import os
import shutil
import rasterio
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import shape
from rasterio import features

import matplotlib.pyplot as plt
import matplotlib.colors as colors

from scripts.raster import Raster

# --- Define class ----------------------------------------------


class TopoRasterGeoref(Raster):
    """
    Instance of a georeferenced raster with building heights information.
    Inherits from Raster class.

    Attributes
    ----------
    filename_e : str
        The name of scenario in export format (e.g.: "FR-Par-V2_d15").
    georef_output : str
        The path to the georeferenced raster.

    Methods
    -------
    to_geojson(viz)
        Open topo_georef.tif file and save it into geojson or geodataframe format.

    """

    def __init__(self, filename_e: str, georef_output: str):

        self.filename_e = filename_e
        self.georef_output = georef_output

        self.topo_georef_path = os.path.join(
            self.georef_output, self.filename_e, "layer_topo_georef.tif"
        )
        if not os.path.exists(self.topo_georef_path):
            raise FileNotFoundError(
                f"No topo georeferenced file found at: {self.topo_georef_path}."
            )
        super().__init__(filename_e=self.filename_e, path_raster=self.topo_georef_path)
        print(f"✅ TopoRasterGeoref successfully initialized for {self.filename_e}.")

    # ---------------------------
    # ---------------------------

    def to_geojson(self, viz: bool = True):
        """
        Open topo_georef.tif file and save it into geojson or geodataframe format

        Parameters
        ----------
        viz : bool = True
            If True, plot the raster with visualize_data() function.

        Returns
        -------
        None.
        """

        # Set up input/output paths
        # topo_output = os.path.join(path_data, "Extracting_buildings", work_zone)
        tif_path = self.topo_georef_path
        destination_folder = os.path.join(self.georef_output, self.filename_e)
        geojson_path = os.path.join(destination_folder, "topo.geojson")

        # Load topo data
        with rasterio.open(tif_path) as src:
            data_topo = src.read(1)
            transform = src.transform
            crs = src.crs

        if viz == True:
            self.visualize_data(data_topo)

        # Conversion of raster into polygons
        mask = data_topo > 0  # conservation of valid pixels only (pixels > 0)
        shapes = features.shapes(data_topo, mask=mask, transform=transform)

        # --- Construction of the GeoDataFrame
        geoms = []
        vals = []
        for geom, value in shapes:
            geoms.append(shape(geom))
            vals.append(value)

        gdf = gpd.GeoDataFrame({"height": vals}, geometry=geoms, crs=crs)

        # --- Saving into GeoJSON ---
        gdf.to_file(geojson_path, driver="GeoJSON")
        print(f"✅ GeoJSON file saved: {geojson_path}")
