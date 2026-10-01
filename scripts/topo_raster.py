#######################################################################

### CLASS : TOPO RASTER CREATION AND LOADING

### Instantiate a non-georeferenced raster as object

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
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.colors as colors

from scripts.raster import Raster
from scripts.metadata import Metadata

# --- Define class ----------------------------------------------


class TopoRaster(Raster):
    """
    Instantiate a non-georeferenced raster object with topo information i.e. building heights.
    Inherits from Raster class.

    Attributes
    ----------
    filename_e: str
        The name of scenario in export format (e.g.: "FR-Par-V2_d15").
    georef_input: str
        The path to rasters before georeferencing operation.
    georef_output: str
        The path to store the raster after georeferencing operation.
    path_data: str
        The general path to data.
    m: Metadata
        A Metadata object.

    Methods
    -------
    to_geojson(destination_folder, viz)
        Open topo_georef.tif file and save it into geojson format.
    """

    def __init__(
        self,
        filename_e: str,
        georef_input: str,
        georef_output: str,
        path_data: str,
        m: Metadata,
    ):
        self.filename_e = filename_e
        metadata_df = m.metadata_df
        self.name_topo = metadata_df["name_topo"][
            metadata_df["NameE"] == self.filename_e
        ].iloc[0]
        self.georef_input = georef_input
        self.georef_output = georef_output

        # --- Step 1 : Obtain all topo paths ---
        (
            self.wind_layer_path,
            self.topo_txt_path,
            self.topo_tif_path,
        ) = self._get_topo_paths(georef_input, path_data)

        # --- Step 2 : Create the raster topo if necessary ---
        if not os.path.exists(self.topo_tif_path):
            print(f"⚠️ Topo raster not found, creating it at {self.topo_tif_path}...")
            self._rasterize_topo()
        else:
            print(f"✅ Topo raster already exists at {self.topo_tif_path}.")

        # --- Step 3 : Load raster in parent object Raster ---
        super().__init__(self.filename_e, self.topo_tif_path)
        print(f"✅ TopoRaster successfully initialized for {self.filename_e}.")

    # ---------------------------
    # ---------------------------

    @staticmethod
    def _transformer_str(s):
        """
        Transform a filename (zone identifier) (ex: 'UA-Kyi-V6_d15') en format abrégé 'UA-KY'.
        """
        parts = s.split("-")
        if len(parts) > 0:
            parts[0] = parts[0][:2].upper()
        if len(parts) > 1:
            parts[1] = parts[1][:2].upper()
        return "-".join(parts)

    # ---------------------------
    # ---------------------------

    def _get_topo_paths(self, georef_input, path_data):
        """
        Get all the paths for topo functions.

        Parameters
        ----------
        georef_input: str
            The path to rasters before georeferencing operation.
        path_data: str
            The general path to data.

        Returns
        -------
        [wind_layer_path, topo_txt_path, topo_tif_path] : [str, str, str]
            wind_layer_path : the path to wind layer.
            topo_txt_path : the path to topo file.
            topo_tif_path : the path to the raster derived from the topo file.
        """

        # --- Path for reference wind layer ---
        wind_layer_path = os.path.join(
            georef_input, self.filename_e, "wind_layer_0.25.tif"
        )

        # --- Topo paths ---
        topo_txt_path = os.path.join(
            path_data,
            "UrbanTALES",  # Copie_UrbanTALES
            "topo",
            self.name_topo,
            f"{self.name_topo}_topo",
        )

        if os.path.isfile(topo_txt_path):
            print(f"[INFO] Topo file found in location: {topo_txt_path}")
        else:
            print(f"[INFO] Topo file not found at: {topo_txt_path}")

        # topo_txt_path2 = None
        # if self.filename_e_other is not None:
        #     topo_txt_path2 = os.path.join(
        #         path_data,
        #         "Copie_UrbanTALES",
        #         "topo",
        #         self.filename_e_other,
        #         f"{self.filename_e_other}_topo",
        #     )
        #     if os.path.isfile(topo_txt_path2):
        #         print(f"[OK] Topo file found: {topo_txt_path2}")
        #         topo_txt_path = topo_txt_path2
        #     else:
        #         print(f"[INFO] Topo file not found at: {topo_txt_path2}")
        #         # On ne fait rien ici, on retombe sur le chemin classique

        # # --- Chemin classique si topo_txt_path2 inexistant ou non fourni ---
        # if not os.path.isfile(topo_txt_path):
        #     print(f"[INFO] Topo file not found at: {topo_txt_path}")

        # # Try alternate path
        # self.filename_e_alt = self._transformer_str(self.filename_e)
        # alt_topo_path = os.path.join(
        #     path_data,
        #     "Copie_UrbanTALES",
        #     "topo",
        #     self.filename_e_alt,
        #     f"{self.filename_e_alt}_topo",
        # )

        #     if os.path.isfile(alt_topo_path):
        #         topo_txt_path = alt_topo_path
        #         print(f"[INFO] Found topo file in alternate location: {alt_topo_path}")
        #     else:
        #         raise FileNotFoundError(
        #             f"No topo file found for work zone '{self.filename_e_alt}'.\n"
        #             f"Tried paths:\n - {topo_txt_path}\n - {alt_topo_path}"
        #         )
        # else:
        #     print(f"[OK] Topo file found: {topo_txt_path}")

        # --- Output raster topo directory and path ---
        topo_output_dir = os.path.join(
            path_data, "Extracting_buildings", self.filename_e
        )
        os.makedirs(topo_output_dir, exist_ok=True)
        topo_tif_path = os.path.join(topo_output_dir, "layer_topo.tif")

        return [wind_layer_path, topo_txt_path, topo_tif_path]

    # ---------------------------
    # ---------------------------

    def _rasterize_topo(self):
        """
        Rasterize the topo file into a GeoTIFF file.

        Returns
        -------
        topo_flipped : np
            The topo raster created.
        """

        # --- Step 0 : Define topo paths ---
        # wind_layer_path = self._get_topo_paths()[0]
        # topo_txt_path = self._get_topo_paths()[1]
        # topo_tif_path = self._get_topo_paths()[2]
        wind_layer_path = self.wind_layer_path
        topo_txt_path = self.topo_txt_path
        topo_tif_path = self.topo_tif_path

        # --- Step 1 : Load topo file (txt file) ---
        topo = np.loadtxt(topo_txt_path)
        print("Dimensions of topo file:", topo.shape)
        print("Insight:", topo[:3, :6])

        # --- Step 2 : Open the reference raster (wind_layer) ---
        with rasterio.open(wind_layer_path) as ref:
            ref_transform = ref.transform
            ref_crs = ref.crs
            ref_width = ref.width
            ref_height = ref.height
            print("\nTransform of reference raster:", ref_transform)
            print("CRS of reference raster:", ref_crs)

        # Checking dimensions consistency
        nrows, ncols = topo.shape
        if ncols != ref_width or nrows != ref_height:
            print(
                f"\n⚠️ Warning: different dimensions! "
                f"Topo = ({nrows}, {ncols}), Reference wind layer = ({ref_height}, {ref_width})"
            )
            print(
                "The raster will be created with topo size, but spatial alignment will be that of the reference raster."
            )

        topo_flipped = np.flipud(topo)

        # --- Step 3 : Create the aligned GeoTIFF ---
        with rasterio.open(
            topo_tif_path,
            mode="w",
            driver="GTiff",
            height=nrows,
            width=ncols,
            count=1,
            dtype=topo.dtype,
            transform=ref_transform,
            crs=ref_crs,
        ) as dst:
            dst.write(topo_flipped, 1)

        print(f"\n✅ Raster topo exported successfully: {topo_tif_path}")

        return topo_flipped

    # ---------------------------
    # ---------------------------

    # def visualize_topo(self, data_topo):

    #     # --- Visualize
    #     vmin = np.nanmin(data_topo)
    #     vmax = np.nanmax(data_topo)
    #     print("vmin =", vmin, "vmax =", vmax)
    #     norm = colors.Normalize(vmin=vmin, vmax=vmax)
    #     cmap = plt.colormaps["Reds"]
    #     plt.figure()
    #     plt.imshow(data_topo, cmap=cmap, vmin=vmin, vmax=vmax)
    #     plt.colorbar(label=f"Building heights")
    #     plt.title(f"Building heights in {self.filename_e}")
    #     plt.show()

    # ---------------------------
    # ---------------------------

    def to_geojson(self, destination_folder, viz: bool = True):
        """
        Open topo_georef.tif file and save it into geojson format.

        Parameters
        ----------
        destination_folder : str
            The folder in which the topo raster is stored.
        viz : bool = True
            If True, the topo raster is plotted.

        Returns
        -------
        None.
        """

        # Set up input/output paths
        # topo_output = os.path.join(path_data, "Extracting_buildings", work_zone)
        tif_path = os.path.join(destination_folder, "layer_topo_georef.tif")
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
