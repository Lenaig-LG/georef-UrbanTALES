#######################################################################

### CLASS : NETCDF PROCESSING

#######################################################################


# --- Packages ------------------------------------------------------

from __future__ import annotations
import os
import logging
from typing import Optional, List

import numpy as np
import xarray as xr
import rasterio
from rasterio.transform import from_origin


# Configure logging simple
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NetCdf")

from scripts.metadata import Metadata

# --- Define class ----------------------------------------------


class NetCdf:
    """
    Defines a NetCDF object obtained from UrbanTALES project.
    The NetCDF contains wind data in three-dimensions (x,y,z) : (u,v,w).

    Attributes
    ----------
    filename_e : str
        The name of scenario, in export format (e.g.: "FR-Par-V2_d15").
    metadata : Metadata
        A Metadata object.
    path_3d_folder : str
        The path to the UrbanTALES NetCDF files.
    georef_input : str
        The path to store the wind rasters before georeferencing operation.

    Methods
    -------
    to_raster(variables, overwrite)
        Translate NetCDF file into 100 rasters layers.
    list_nc_files()
        Make the list of .nc files in 3Dwind folder.
    process_nc(overwrite)
        Process the NetCDF file (translating into rasters, storage of rasters, deletion of NetCDF file).
    """

    def __init__(
        self, filename_e, metadata: Metadata, path_3d_folder: str, georef_input: str
    ):
        self.filename_e = filename_e
        self.metadata = metadata
        self.path_3d_folder = path_3d_folder
        self.georef_input = georef_input
        result = self._load_netcdf()
        if result is None:
            self.nc_xr = None
            self.name_i = None
        else:
            self.nc_xr, self.name_i = result

    # -------------------------
    # -------------------------

    def _load_netcdf(self):
        """
        Load a wind nc file from UrbanTALES configuration, with xarray package.

        Returns
        -------
        Xarray file
        """

        # --- Select corresponding nc file ---

        # Localize netCDF file via metadata (NameE -> NameI_data.nc)
        metadata_df = self.metadata.metadata_df
        mask = metadata_df["NameE"] == self.filename_e
        if not mask.any():
            logger.error("⚠️ No metadata entry for NameE='%s'", self.filename_e)
            return None

        name_i = metadata_df.loc[mask, "NameI"].iloc[0]
        nc_filename = f"{name_i}_data.nc"

        path_nc = os.path.join(self.path_3d_folder, nc_filename)
        if not os.path.isfile(path_nc):
            print("⚠️ NetCDF file not found: %s", path_nc)
            return None

        # --- Load nc file ---

        logger.info("Opening NetCDF: %s", path_nc)
        ds = xr.open_dataset(path_nc, engine="netcdf4")  # lazy open

        return ds, name_i

    # -------------------------
    # -------------------------

    def to_raster(self, variables: Optional[List[str]] = None, overwrite: bool = False):
        """
        Translate NetCDF file into 100 rasters layers.

        Parameters
        ----------
        nc_file : xarray
            NetCDF file loaded with xarray package.
        overwrite : bool
            If the extracted files overwrite the existing stored files or not.

        Returns
        -------
        None. The files are extracted and stored locally in georef_input.
        """
        nc_file = self.nc_xr
        if nc_file is None:
            print("Nc file not found, no rasterisation possible.")
        else:
            print("From NetCDF file to raster -------")

            # In case no precision on variables
            if variables is None:
                variables = ["u", "v", "w"]

            # Extract coords
            if not {"x", "y", "z"}.issubset(set(nc_file.coords.keys())):
                logger.error(
                    "⚠️ NetCDF missing required coordinates (x,y,z). Found: %s",
                    list(nc_file.coords.keys()),
                )
                nc_file.close()
                return None

            x = nc_file["x"].values
            y = nc_file["y"].values
            z = nc_file["z"].values

            # Transformation raster (assume regular grid)
            dx = float(np.mean(np.diff(x)))
            dy = float(np.mean(np.diff(y)))
            transform = from_origin(x.min(), y.max(), dx, -dy)

            # Loop on z levels
            out_dir = os.path.join(self.georef_input, self.filename_e)
            os.makedirs(out_dir, exist_ok=True)

            exported_levels = []
            for k, z_val in enumerate(z):
                arrays_for_bands = []
                band_names = []

                logger.info("\n=== Processing z level index=%d z=%s ===\n", k, z_val)

                for var in variables:
                    if var not in nc_file:
                        logger.warning(
                            "⚠️ Variable '%s' not present in dataset; skipping.", var
                        )
                        continue

                    # Select layer and ensure orientation (y,x)
                    try:
                        arr_xr = nc_file[var].isel(z=k).transpose("y", "x")
                    except Exception:
                        # Fallback for datasets without named dims or different order
                        arr_xr = nc_file[var].isel(z=k)
                        if ("y" in arr_xr.dims) and ("x" in arr_xr.dims):
                            arr_xr = arr_xr.transpose("y", "x")
                        else:
                            arr_xr = arr_xr.T  # best-effort

                    np_arr = arr_xr.values.astype(np.float32)
                    arrays_for_bands.append(np_arr)
                    band_names.append(var)

                    nan_ratio = float(np.isnan(np_arr).mean() * 100.0)
                    logger.debug(
                        "var=%s shape=%s nan%%=%.2f", var, np_arr.shape, nan_ratio
                    )

                if not arrays_for_bands:
                    logger.info("⚠️ No valid variables for z=%s -> skipping.", z_val)
                    continue

                out_tif = os.path.join(out_dir, f"wind_layer_{float(z_val):.2f}.tif")
                if os.path.exists(out_tif) and not overwrite:
                    logger.info(
                        "File exists and overwrite=False: %s (skipping)", out_tif
                    )
                    exported_levels.append(out_tif)
                    continue

                # Write multi-band GeoTIFF
                height, width = arrays_for_bands[0].shape
                count = len(arrays_for_bands)
                dtype = arrays_for_bands[0].dtype

                # Note: ds has no CRS information here; we write without CRS. The user can set crs later.
                with rasterio.open(
                    out_tif,
                    "w",
                    driver="GTiff",
                    height=height,
                    width=width,
                    count=count,
                    dtype=dtype,
                    crs=None,
                    transform=transform,
                ) as dst:
                    for i, arr in enumerate(arrays_for_bands, start=1):
                        dst.write(arr, i)
                        try:
                            dst.set_band_description(i, band_names[i - 1])
                        except Exception:
                            pass

                logger.info("✅ Saved: %s", out_tif)
                exported_levels.append(out_tif)

            nc_file.close()
            print("End raster conversion ---------------")

    # -------------------------
    # -------------------------

    def list_nc_files(self) -> List[str]:
        """
        Make the list of .nc files in 3Dwind folder.
        """

        folder = self.path_3d_folder
        if not os.path.isdir(folder):
            logger.warning("3D folder does not exist: %s", folder)
            return []

        return [f for f in os.listdir(folder) if f.endswith(".nc")]

    # -------------------------
    # -------------------------

    @staticmethod
    def _check_all_rasters_exist(path_raster, z_list):
        all_exist = True
        for z_val in z_list:
            out_tif = os.path.join(path_raster, f"wind_layer_{float(z_val):.2f}.tif")
            if not os.path.isfile(out_tif):
                print(f"Raster not found: {out_tif}")
                all_exist = False
        return all_exist

    # -------------------------
    # -------------------------

    def process_nc(self, overwrite: bool = False):
        """
        Process the NetCDF file. The execution includes:
        - transforming the .nc file to 100 rasters files with to_raster() function;
        - storage of new rasters in georef_input path;
        - deletion of .nc file in path_3d_folder path.

        If rasters files are found, no need to process any longer and the raster files are stored in georef_input folder.
        Elif nc file in the nc path directory, conversion from .nc to multiple .tif files and deletion of .nc file in the directory.

        Warning
        -------
        Before running this function, please take note that this step will delete your .nc data.
        Copying your data on a SSD in highly encouraged.

        Parameters
        ----------
        overwrite : bool
            If True, the rasters overwrite existing files.

        Returns
        -------
        None.
        """

        name_i = self.name_i
        nc_filename = f"{name_i}_data.nc"
        path_nc = os.path.join(self.path_3d_folder, nc_filename)
        path_raster = os.path.join(self.georef_input, self.filename_e)
        z_list = np.arange(0.25, 50, 0.5).tolist()

        # Find rasters ?
        if self._check_all_rasters_exist(path_raster, z_list):
            print("All rasters (.tif files) exist, no need to process NetCDF file.")
            print("Files are stored at : ", path_raster)
        else:
            print("Some rasters are missing, continue processing...")
            self.to_raster(overwrite=overwrite)

        # Delete the nc file stored on local machine
        if os.path.isfile(path_nc):
            os.remove(path_nc)
            print("File deleted : ", path_nc)
        else:
            print("⚠️ NetCDF file not found: %s", path_nc)
            print(
                "Nc file already deleted or not found, \nIf any doubt, please check the data stored in SSD support."
            )
