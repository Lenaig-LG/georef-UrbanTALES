#######################################################################

### CLASS : RASTER

#######################################################################


# --- Packages ------------------------------------------------------

import os
import shutil
import rasterio
import numpy as np
import geopandas as gpd
from shapely.geometry import shape
from rasterio import features
import matplotlib.pyplot as plt
import matplotlib.colors as colors

# --- Define class ----------------------------------------------


class Raster:
    """
    Defines a single raster file.

    Attributes
    ----------
    filename_e : str
        The name of scenario in export format (e.g.: "FR-Par-V2_d15").
    path_raster : str
        The path to the raster.

    Methods
    -------
    summary()
        Displays the path, the resolution and the projection of the raster.
    close()
        Close the raster.
    visualize_data(data)
        Plot the data in the raster.
    to_geojson(source_path, destination_path, viz)
        Save a raster into a geojson file and return the gdf file.

    """

    def __init__(self, filename_e: str, path_raster: str):
        self.filename_e = filename_e
        self.path_raster = path_raster

        self.dataset = rasterio.open(path_raster)

    # ---------------------------
    # ---------------------------

    def summary(self):
        print(f"Raster: {self.path}")
        print(f"Resolution: {self.dataset.res}")
        print(f"Projection: {self.dataset.crs}")

    # ---------------------------
    # ---------------------------

    def close(self):
        self.dataset.close()

    # ---------------------------
    # ---------------------------

    def visualize_data(self, data):
        """
        Plot the data in the raster.
        """

        vmin = np.nanmin(data)
        vmax = np.nanmax(data)
        print("vmin =", vmin, "vmax =", vmax)
        norm = colors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.colormaps["Reds"]
        plt.figure()
        plt.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
        plt.colorbar(label=f"Building heights")
        plt.title(f"Building heights in {self.filename_e}")
        plt.show()

    # ---------------------------
    # ---------------------------

    def to_geojson(self, source_path, destination_path, viz: bool = True):
        """
        Save a raster into a geojson file and return the gdf file.

        Parameters
        ----------
        source_path : str
            The complete path to the raster.
        destination_path : str
            The complete path to the output geojson file.
        viz : bool
            If the raster is plotted or not.

        Returns
        -------
        gdf : GeoDataFrame
            The geodataframe created from the raster.

        """

        # Set up input/output paths
        tif_path = source_path
        geojson_path = destination_path

        # Load topo data
        with rasterio.open(tif_path) as src:
            data = src.read(1)
            transform = src.transform
            crs = src.crs

        if viz == True:
            self.visualize_topo(data)

        # Conversion of raster into polygons
        mask = data > 0  # conservation of valid pixels only (pixels > 0)
        shapes = features.shapes(data, mask=mask, transform=transform)

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

        return gdf

    # ---------------------------
    # ---------------------------

    # def _load_raster(self):
    #     """

    #     Parameters
    #     ----------
    #     path_raster : str
    #         Path to the raster file (ex : 'data/my_raster.tif').

    #     Return
    #     ------
    #     dataset : rasterio.io.DatasetReader
    #         rasterio object to access to raster metadata and values.
    #     """

    #     try:
    #         dataset = rasterio.open(self.path_raster)
    #         print("Raster opened with success ✅")
    #         print(f"Dimensions: {dataset.width} x {dataset.height}")
    #         print(f"Nb of bands: {dataset.count}")
    #         print(f"Projection: {dataset.crs}")
    #         print(f"Resolution: {dataset.res}")
    #         return dataset
    #     except Exception as e:
    #         print(f"Error while opening raster: {e}")
    #         return None

    #     # # Case of use
    #     # raster = _load_raster("data/mon_raster.tif")

    #     # if raster is not None:
    #     #     # Lire la première bande
    #     #     band1 = raster.read(1)
    #     #     print(band1.shape)
    #     #     raster.close()

    # ---------------------------
    # ---------------------------
