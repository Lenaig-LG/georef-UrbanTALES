#######################################################################

### CLASS : WIND GRID CREATION AND LOADING

#######################################################################


# --- Packages --------------------------------------------------------

import rasterio
import os
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
import math
import rasterio
from rasterio.features import geometry_mask

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from rasterio.features import geometry_mask

from scripts.grid import Grid
from scripts.metadata import Metadata

# --- Define class ----------------------------------------------------


class WindGrid:
    """
    This class defines the wind grid containing the wind variables.
    Class composed of a Grid object.

    Attributes
    ----------
    grid : Grid
        A Grid object on which wind variables will be computed.
    metadata : Metadata
        A Metadata file.

    Methods
    -------
    rotate_WD_deg(angle_to_add)
        Modify the wind direction if necessary.
    """

    def __init__(self, grid: Grid, metadata: Metadata):
        self.grid = grid
        self.metadata = metadata
        self.target_resolution = grid.target_resolution
        self.target_shape = self._compute_target_shape()

        # # Wind data
        # self.data_dict, self.transform, self.crs_raster = self._load_wind_data()
        # # Grid data
        # gdf_grid = load_grid(filename_e=filename_e, target_resolution=100)
        # # Create grid id
        # self.gdf_grid = self._create_cell_id(self.grid)
        # display_wind_field_grid(data_u, "u", gdf_grid)
        # display_wind_field_grid(data_v, "v", gdf_grid)
        # display_wind_field_grid(data_w, "w", gdf_grid)

        output_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "wind_grid_all.geojson"
        )
        # Check if wind_grid exists, else create it.
        if os.path.isfile(output_path):
            print("Loading wind grid...")
            self.gdf_wind_grid = gpd.read_file(output_path)
            print("Wind grid loaded!")
        else:
            # Create wind grid
            print("Creation of wind grid...")
            self.gdf_wind_grid = self._extract_wind_grid()
            print("Wind grid created!")

    # ---------------------------------
    # ---------------------------------

    def _compute_target_shape(self):
        georef_tif_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "wind_layer_0.25_georef.tif"
        )
        with rasterio.open(georef_tif_path) as src:
            pixel_size = src.res[0]  # in meters

        cell_size = self.grid.target_resolution  # size r defined in Grid

        n = int(round(cell_size / pixel_size))

        return (n, n)

    # ---------------------------------
    # ---------------------------------

    # @staticmethod
    # def _extract_submatrix(data, transform, polygon):
    #     mask = geometry_mask(
    #         [polygon], transform=transform, invert=True, out_shape=data.shape
    #     )
    #     submatrix = np.where(mask, data, np.nan)
    #     return submatrix

    # ---------------------------------
    # ---------------------------------

    # @staticmethod
    # def _crop_to_bbox(submatrix):
    #     mask = ~np.isnan(submatrix)
    #     if mask.any():
    #         rows, cols = np.where(mask)
    #         return submatrix[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
    #     else:
    #         return np.array([])  # empty polygon

    # ---------------------------------
    # ---------------------------------

    @staticmethod
    def _extract_submatrix(data, transform, polygon):
        """
        Reliable extraction of a submatrix corresponding to a polygon.
        Does not modify the values. No loss of information.
        """
        # Creation of a mask of same size as matrix
        mask = geometry_mask(
            [polygon],
            transform=transform,
            invert=True,  # True = we keep the interior of the polygon
            out_shape=data.shape,
        )

        # Mask application
        submatrix = data.astype(float).copy()
        submatrix[~mask] = np.nan

        return submatrix

    # ---------------------------------
    # ---------------------------------

    def _crop_to_bbox_fixed_size(self, submatrix):
        """
        Crop the matrix to the bounding box, then adjust its size to target_shape (H, W) by padding or cropping.
        Objective: to obtain comparable matrices of the same dimensions.
        """

        # Find useful lines/columns
        valid = ~np.isnan(submatrix)
        if not valid.any():
            return np.full(self.target_shape, np.nan)

        rows, cols = np.where(valid)

        # Re frame without useful data loss
        cropped = submatrix[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]

        h, w = cropped.shape
        H, W = self.target_shape

        # New matrix filled with NaN
        result = np.full((H, W), np.nan)

        # Edges (if matrix exceeds we properly truncate it)
        h_end = min(h, H)
        w_end = min(w, W)

        # Placement at upper-left for consistency
        result[:h_end, :w_end] = cropped[:h_end, :w_end]

        return result

    # ---------------------------------
    # ---------------------------------

    def _submatrix_to_geodataframe(self, data_u, data_v, transform, polygon, id_poly):
        """
        Convert a pair of submatrices (u,v) into a GeoDataFrame with speed and direction.
        """
        mask = geometry_mask(
            [polygon], transform=transform, invert=True, out_shape=data_u.shape
        )

        # Valid index
        rows, cols = np.where(mask)

        # Spatial coordinates
        xs = transform.c + cols * transform.a
        ys = transform.f + rows * transform.e

        # Values
        u_vals = data_u[rows, cols]
        v_vals = data_v[rows, cols]

        # Physical calculations
        speed = np.sqrt(u_vals**2 + v_vals**2)
        angle = np.arctan2(v_vals, u_vals)  # radians (de -pi à pi)

        # Dataframe
        df = pd.DataFrame(
            {
                "id_poly": id_poly,
                "x": xs,
                "y": ys,
                "u": u_vals,
                "v": v_vals,
                "speed": speed,
                "angle_rad": angle,
                "angle_deg": np.degrees(angle),
            }
        )

        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(x, y) for x, y in zip(xs, ys)],
            crs=self.grid.gdf_grid.crs,
        )

        return gdf

    # ---------------------------------
    # ---------------------------------

    def _load_wind_data(self, z):
        """
        Load the georeferenced wind raster for layer z and reproject it to the CRS of the grid if necessary.

        Parameters
        ----------
        z : int
            The z-level (height level).

        Returns
        -------
        data_dict, transform, crs_raster : dict, affine.Affine, crs
            data_dict : The wind data (u, v, w) at level z, stored in dict.
            transform : The affine matrix of wind data.
            crs_raster : The crs of the raster.
        """

        layer_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, f"wind_layer_{z}_georef.tif"
        )

        with rasterio.open(layer_path) as src:
            nb_bandes = src.count
            transform = src.transform
            crs_raster = src.crs

            # --- If raster is not in the samed CRS as the grid ---
            target_crs = self.grid.gdf_grid.crs
            if crs_raster != target_crs:
                print(
                    f"♻️ Reprojecting raster layer {z} from {crs_raster} to {target_crs}"
                )

                # Create a temporary reprojecting profile
                from rasterio.warp import (
                    calculate_default_transform,
                    reproject,
                    Resampling,
                )

                transform, width, height = calculate_default_transform(
                    crs_raster, target_crs, src.width, src.height, *src.bounds
                )

                profile = src.profile
                profile.update(
                    {
                        "crs": target_crs,
                        "transform": transform,
                        "width": width,
                        "height": height,
                    }
                )

                # Read and reproject each band
                data_list = []
                for i in range(1, nb_bandes + 1):
                    band = src.read(i)
                    dest = np.empty((height, width), dtype=band.dtype)
                    reproject(
                        source=band,
                        destination=dest,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear,
                    )
                    data_list.append(dest)

                crs_raster = target_crs  # now same as the grid one

            else:
                # Non need to reproject
                data_list = [src.read(i) for i in range(1, nb_bandes + 1)]

        # --- Attribute band names ---
        var_names = ["u", "v", "w"]
        if nb_bandes <= len(var_names):
            keys = var_names[:nb_bandes]
        else:
            keys = var_names + [
                f"band_{i}" for i in range(len(var_names) + 1, nb_bandes + 1)
            ]

        data_dict = dict(zip(keys, data_list))

        return data_dict, transform, crs_raster

    # ---------------------------------
    # ---------------------------------

    @staticmethod
    def _plot_axes(
        vec_lon: np.array, vec_lat: np.array, vec_x: np.array, vec_y: np.array
    ):
        """
        Plot axes of the scenario (aka the wind grid) and the longitudinal and latitudinal vectors.
        The function enables a clear visualization of domain spatial arrangement.

        Parameters
        ----------
        vec_lon: np.array
            The longitudinal vector.
        vec_lat: np.array
            The latitudinal vector.
        vec_x: np.array
            The vector of X-axis of wind grid (scenario).
        vec_y: np.array
            The vector of Y-axis of wind grid (scenario).

        Returns
        -------
        None.
        """

        plt.figure(figsize=(6, 6))
        plt.axhline(0, color="lightgray")
        plt.axvline(0, color="lightgray")

        origin = np.array([[0, 0], [0, 0]])  # origin for quiver

        # Base vectors
        plt.quiver(
            0,
            0,
            vec_lon[0],
            vec_lon[1],
            color="blue",
            label="vec_lon (1,0)",
            angles="xy",
            scale_units="xy",
            scale=1,
        )
        plt.quiver(
            0,
            0,
            vec_lat[0],
            vec_lat[1],
            color="green",
            label="vec_lat (0,1)",
            angles="xy",
            scale_units="xy",
            scale=1,
        )

        # Tranformed vectors
        plt.quiver(
            0,
            0,
            vec_x[0],
            vec_x[1],
            color="red",
            label="vec_x",
            angles="xy",
            scale_units="xy",
            scale=1,
        )
        plt.quiver(
            0,
            0,
            vec_y[0],
            vec_y[1],
            color="orange",
            label="vec_y",
            angles="xy",
            scale_units="xy",
            scale=1,
        )

        plt.xlim(-1.5, 1.5)
        plt.ylim(-1.5, 1.5)
        plt.gca().set_aspect("equal", "box")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend()
        plt.title("Vizualisation of vectors: lon, lat, x, y")

        plt.show()

    # ---------------------------------
    # ---------------------------------

    def _create_gdf_wind(
        self, data_dict, transform, gdf, vec_x, vec_y, vec_lon, vec_lat
    ):
        """
        Create wind data on a grid for one layer.
        In this function, many wind variables are computed.
        Data are agregated by computation on each cell of the grid.

        Parameters
        ----------
        data_dict : dict
            The dictionnary containing wind data for the corresponding layer.
            Obtained from execution of load_wind_data().
        transform : affine.Affine
            The affine matrix of wind data, obtained from execution of load_wind_data().
        gdf : GeoDataFrame
            The initial GeoDataFrame on which wind data is stored.

        Returns
        -------
        GeoDataFrame of wind data on each cell.
        """

        # Load wind data
        data_u = data_dict["u"]
        data_v = data_dict["v"]
        data_w = data_dict["w"]

        # # Retrieve angle
        # theta_star = (
        #     -1
        #     * self.metadata.metadata_df.loc[
        #         self.metadata.metadata_df["NameE"] == self.grid.filename_e,
        #         "angle_domain",
        #     ].values[0]
        # )  # theta_star in deg

        # theta_star_rad = math.radians(theta_star)
        # psi = 90 - theta_star
        # psi_rad = math.radians(psi)

        # # 1. Express vec x and vec y depending on vec lon and vec lat
        # vec_lon = np.array([1, 0])
        # vec_lat = np.array([0, 1])
        # vec_x = math.sin(theta_star_rad) * vec_lat - math.cos(theta_star_rad) * vec_lon
        # vec_y = math.cos(psi_rad) * vec_lon + math.sin(psi_rad) * vec_lat

        # self._plot_axes(vec_lon, vec_lat, vec_x, vec_y)  # to check if everything is ok

        for idx, poly in enumerate(gdf.geometry):
            # Extract submatrix
            submatrix_u = self._extract_submatrix(data_u, transform, poly)
            submatrix_v = self._extract_submatrix(data_v, transform, poly)
            submatrix_w = self._extract_submatrix(data_w, transform, poly)
            # show_matrix_plot(submatrix_u, "sous matrice")

            # Crop submatrix (remove nan)
            submatrix_u_cropped = self._crop_to_bbox_fixed_size(submatrix_u)
            submatrix_v_cropped = self._crop_to_bbox_fixed_size(submatrix_v)
            submatrix_w_cropped = self._crop_to_bbox_fixed_size(submatrix_w)
            # show_matrix_plot(submatrix_u_cropped, "sous matrice coupée")

            # --- Process pipeline ---

            # 1. Scalar mean
            mean_u = np.nanmean(submatrix_u_cropped)
            mean_v = np.nanmean(submatrix_v_cropped)
            mean_w = np.nanmean(submatrix_w_cropped)

            # 2. Express each u depending on vec_lon and vec_lat
            vec_mean_u = vec_x * mean_u
            vec_mean_v = vec_y * mean_v
            # mean_vector = np.array([mean_u, mean_v])
            # gdf.loc[idx, "mean_u_lon"] = vec_mean_u[0]
            # gdf.loc[idx, "mean_u_lat"] = vec_mean_u[1]
            # gdf.loc[idx, "mean_v_lon"] = vec_mean_v[0]
            # gdf.loc[idx, "mean_v_lat"] = vec_mean_v[1]
            gdf.loc[idx, "mean_w"] = mean_w

            # 3. Compute wind vector
            vec_wind_mean = vec_mean_u + vec_mean_v
            gdf.loc[idx, "wind_mean_lon"] = vec_wind_mean[0]
            gdf.loc[idx, "wind_mean_lat"] = vec_wind_mean[1]

            # 4. Compute norm of wind vector = speed variable
            # speed = np.sqrt(vec_wind[0]**2 + vec_wind[1]**2)
            speed_mean = np.linalg.norm(vec_wind_mean)
            gdf.loc[idx, "speed_mean"] = speed_mean

            # --- Now repeat process with other stats ---

            # Std ---

            std_u = np.nanstd(submatrix_u_cropped)
            std_v = np.nanstd(submatrix_v_cropped)
            std_w = np.nanstd(submatrix_w_cropped)

            vec_std_u = vec_x * std_u
            vec_std_v = vec_y * std_v

            # gdf.loc[idx, "std_u_lon"] = vec_std_u[0]
            # gdf.loc[idx, "std_u_lat"] = vec_std_u[1]
            # gdf.loc[idx, "std_v_lon"] = vec_std_v[0]
            # gdf.loc[idx, "std_v_lat"] = vec_std_v[1]
            gdf.loc[idx, "std_w"] = std_w

            vec_wind_std = vec_std_u + vec_std_v
            gdf.loc[idx, "wind_std_lon"] = vec_wind_std[0]
            gdf.loc[idx, "wind_std_lat"] = vec_wind_std[1]

            speed_std = np.linalg.norm(vec_wind_std)
            gdf.loc[idx, "speed_std"] = speed_std

            # Quantile 25% ---

            q25_u = np.nanquantile(submatrix_u_cropped, q=0.25)
            q25_v = np.nanquantile(submatrix_v_cropped, q=0.25)
            q25_w = np.nanquantile(submatrix_w_cropped, q=0.25)

            vec_q25_u = vec_x * q25_u
            vec_q25_v = vec_y * q25_v

            # gdf.loc[idx, "q25_u_lon"] = vec_q25_u[0]
            # gdf.loc[idx, "q25_u_lat"] = vec_q25_u[1]
            # gdf.loc[idx, "q25_v_lon"] = vec_q25_v[0]
            # gdf.loc[idx, "q25_v_lat"] = vec_q25_v[1]
            gdf.loc[idx, "q25_w"] = q25_w

            vec_wind_q25 = vec_q25_u + vec_q25_v
            gdf.loc[idx, "wind_q25_lon"] = vec_wind_q25[0]
            gdf.loc[idx, "wind_q25_lat"] = vec_wind_q25[1]

            speed_q25 = np.linalg.norm(vec_wind_q25)
            gdf.loc[idx, "speed_q25"] = speed_q25

            # Quantile 75% ---

            q75_u = np.nanquantile(submatrix_u_cropped, q=0.75)
            q75_v = np.nanquantile(submatrix_v_cropped, q=0.75)
            q75_w = np.nanquantile(submatrix_w_cropped, q=0.75)

            vec_q75_u = vec_x * q75_u
            vec_q75_v = vec_y * q75_v

            # gdf.loc[idx, "q75_u_lon"] = vec_q75_u[0]
            # gdf.loc[idx, "q75_u_lat"] = vec_q75_u[1]
            # gdf.loc[idx, "q75_v_lon"] = vec_q75_v[0]
            # gdf.loc[idx, "q75_v_lat"] = vec_q75_v[1]
            gdf.loc[idx, "q75_w"] = q75_w

            vec_wind_q75 = vec_q75_u + vec_q75_v
            gdf.loc[idx, "wind_q75_lon"] = vec_wind_q75[0]
            gdf.loc[idx, "wind_q75_lat"] = vec_wind_q75[1]

            speed_q75 = np.linalg.norm(vec_wind_q75)
            gdf.loc[idx, "speed_q75"] = speed_q75

            # Mini ---

            min_u = np.nanmin(submatrix_u_cropped)
            min_v = np.nanmin(submatrix_v_cropped)
            min_w = np.nanmin(submatrix_w_cropped)

            vec_min_u = vec_x * min_u
            vec_min_v = vec_y * min_v
            # min_vector = np.array([min_u, min_v])
            # gdf.loc[idx, "min_u_lon"] = vec_min_u[0]
            # gdf.loc[idx, "min_u_lat"] = vec_min_u[1]
            # gdf.loc[idx, "min_v_lon"] = vec_min_v[0]
            # gdf.loc[idx, "min_v_lat"] = vec_min_v[1]
            gdf.loc[idx, "min_w"] = min_w

            vec_wind_min = vec_min_u + vec_min_v
            gdf.loc[idx, "wind_min_lon"] = vec_wind_min[0]
            gdf.loc[idx, "wind_min_lat"] = vec_wind_min[1]

            speed_min = np.linalg.norm(vec_wind_min)
            gdf.loc[idx, "speed_min"] = speed_min

            # Maxi ---

            max_u = np.nanmax(submatrix_u_cropped)
            max_v = np.nanmax(submatrix_v_cropped)
            max_w = np.nanmax(submatrix_w_cropped)

            vec_max_u = vec_x * max_u
            vec_max_v = vec_y * max_v
            # max_vector = np.array([max_u, max_v])
            # gdf.loc[idx, "max_u_lon"] = vec_max_u[0]
            # gdf.loc[idx, "max_u_lat"] = vec_max_u[1]
            # gdf.loc[idx, "max_v_lon"] = vec_max_v[0]
            # gdf.loc[idx, "max_v_lat"] = vec_max_v[1]
            gdf.loc[idx, "max_w"] = max_w

            vec_wind_max = vec_max_u + vec_max_v
            gdf.loc[idx, "wind_max_lon"] = vec_wind_max[0]
            gdf.loc[idx, "wind_max_lat"] = vec_wind_max[1]

            speed_max = np.linalg.norm(vec_wind_max)
            gdf.loc[idx, "speed_max"] = speed_max

            # --- End stats on wind vector ---

            # 6. Angle of wind vector from north = -lat axis
            theta_a_rad = np.arccos(
                (1 / speed_mean) * np.dot((-1 * vec_lat), vec_wind_mean)
            )
            theta_a_deg = np.degrees(theta_a_rad)
            gdf.loc[idx, "angle_wind_deg"] = theta_a_deg
            gdf.loc[idx, "angle_wind_rad"] = theta_a_rad

            # # 7. Add wind direction
            # match = re.search(r"_d(\d+)", self.grid.filename_e)
            # if match:
            #     wd_deg = float(match.group(1))
            #     wd_rad = math.radians(wd_deg)
            #     init_wind = math.cos(wd_rad) * vec_x - math.sin(wd_rad) * vec_y
            #     speed_i = np.linalg.norm(init_wind)
            #     theta_i_rad = np.arccos(
            #         (1 / speed_i) * np.dot((-1 * vec_lat), init_wind)
            #     )
            #     theta_i_deg = np.degrees(theta_i_rad)
            #     gdf.loc[idx, "WD_deg"] = theta_i_deg
            #     gdf.loc[idx, "WD_rad"] = theta_i_rad
            #     gdf.loc[idx, "init_speed"] = speed_i
            #     gdf.loc[idx, "init_lon"] = init_wind[0]
            #     gdf.loc[idx, "init_lat"] = init_wind[1]
            # else:
            #     print("Wind direction not found, set to NaN")

            # ---- Other wind variables, near ground ----

            # Harmonisation des NaN
            mask = (
                np.isnan(submatrix_u_cropped)
                | np.isnan(submatrix_v_cropped)
                | np.isnan(submatrix_w_cropped)
            )
            u = submatrix_u_cropped.copy()
            v = submatrix_v_cropped.copy()
            w = submatrix_w_cropped.copy()

            u[mask] = np.nan
            v[mask] = np.nan
            w[mask] = np.nan

            # Vectorial norm point by point
            norm_vect_speed = np.sqrt(u**2 + v**2 + w**2)

            # Statistics
            mean_norm_speed = np.nanmean(norm_vect_speed)
            median_norm_speed = np.nanmedian(norm_vect_speed)
            std_norm_speed = np.nanstd(norm_vect_speed)
            q25_norm_speed = np.nanquantile(norm_vect_speed, q=0.25)
            q75_norm_speed = np.nanquantile(norm_vect_speed, q=0.75)
            q10_norm_speed = np.nanquantile(norm_vect_speed, q=0.10)
            q90_norm_speed = np.nanquantile(norm_vect_speed, q=0.90)

            # Add to gdf
            gdf.loc[idx, "mean_norm_speed"] = mean_norm_speed
            gdf.loc[idx, "median_norm_speed"] = median_norm_speed
            gdf.loc[idx, "std_norm_speed"] = std_norm_speed
            gdf.loc[idx, "q25_norm_speed"] = q25_norm_speed
            gdf.loc[idx, "q75_norm_speed"] = q75_norm_speed
            gdf.loc[idx, "q10_norm_speed"] = q10_norm_speed
            gdf.loc[idx, "q90_norm_speed"] = q90_norm_speed

        # gdf = gdf.drop("centroid", axis=1)

        # gdf.to_file(output_path, driver="GeoJSON")
        # print(f"File created here : {output_path}")

        return gdf

    # ---------------------------------
    # ---------------------------------

    def _extract_wind_grid(self):
        """
        Build the wind grid by extracting wind data on each cell of a grid.

        Returns
        -------
        GeoDataFrame
            The GeoDataFrame of wind data extracted and aggregated on the grid.
        """

        z_values = pd.read_csv(
            os.path.join(self.grid.path_data, "Copie_UrbanTALES", "z_values.csv")
        )
        gdf_all_wind = []

        # --- Retrieve angle between x-axis and longitude axis ---
        theta_star = (
            -1
            * self.metadata.metadata_df.loc[
                self.metadata.metadata_df["NameE"] == self.grid.filename_e,
                "angle_domain",
            ].values[0]
        )  # theta_star in deg

        theta_star_rad = math.radians(theta_star)
        psi = 90 - theta_star
        psi_rad = math.radians(psi)

        # --- Express vec x and vec y depending on vec lon and vec lat ---
        vec_lon = np.array([1, 0])
        vec_lat = np.array([0, 1])
        vec_x = math.sin(theta_star_rad) * vec_lat - math.cos(theta_star_rad) * vec_lon
        vec_y = math.cos(psi_rad) * vec_lon + math.sin(psi_rad) * vec_lat
        vec_y = -vec_y
        vec_x = -vec_x

        self._plot_axes(
            vec_lon=vec_lon, vec_lat=vec_lat, vec_x=vec_x, vec_y=vec_y
        )  # to check if everything is ok

        # --- Processing for each z ---

        for z in z_values["Height_z"]:
            print(f"\n--- Processing layer z = {z} ---")

            # Load the raster (now reprojected in grid CRS)
            data_dict, transform, crs_raster = self._load_wind_data(z)

            # Initialisation of wind grid
            grid_base = self.grid.gdf_grid.copy()
            if "centroid" in grid_base.columns:
                grid_base = grid_base.drop("centroid", axis=1)
                print("Colonne 'centroid' supprimée.")
            gdf_wind = grid_base

            # Extraction and statistics
            gdf_wind = self._create_gdf_wind(
                data_dict=data_dict,
                transform=transform,
                gdf=gdf_wind,
                vec_x=vec_x,
                vec_y=vec_y,
                vec_lon=vec_lon,
                vec_lat=vec_lat,
            )

            gdf_wind["z"] = z

            # Add wind direction
            match = re.search(r"_d(\d+)", self.grid.filename_e)
            if match:
                wd_deg = float(match.group(1))
                wd_rad = math.radians(wd_deg)
                init_wind = math.cos(wd_rad) * vec_x + math.sin(wd_rad) * vec_y
                speed_i = np.linalg.norm(init_wind)  # should be 1...
                theta_i_rad = np.arccos(
                    (1 / speed_i) * np.dot((-1 * vec_lat), init_wind)
                )
                theta_i_deg = np.degrees(theta_i_rad)
                gdf_wind["WD_deg"] = theta_i_deg
                gdf_wind["WD_rad"] = theta_i_rad
                gdf_wind["init_speed"] = speed_i
                gdf_wind["init_lon"] = init_wind[0]
                gdf_wind["init_lat"] = init_wind[1]
            else:
                print("Wind direction not found, set to NaN")

            gdf_all_wind.append(gdf_wind)

        # Final fusion of all height levels
        gdf_all_wind = gpd.GeoDataFrame(
            pd.concat(gdf_all_wind, ignore_index=True),
            crs=self.grid.gdf_grid.crs,
        )

        # Output exportation
        output_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "wind_grid_all.geojson"
        )
        gdf_all_wind.to_file(output_path, driver="GeoJSON")
        print(f"✅ Wind grid saved to: {output_path}")

        return gdf_all_wind

    # ---------------------------------
    # ---------------------------------

    def rotate_WD_deg(self, angle_to_add):
        """
        Modify the wind direction if necessary.
        The domain is rotated.
        A parallel visual inspection is encouraged.

        Parameters
        ----------
        angle_to_add : int
            The angle to add to the existing angle value.
        """

        wind_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "wind_grid_all.geojson"
        )
        wind_grid = gpd.read_file(wind_path)

        wind_grid["WD_deg"] = (wind_grid["WD_deg"] + angle_to_add) % 360

        output_path = os.path.join(
            self.grid.georef_output, self.grid.filename_e, "wind_grid_all.geojson"
        )
        wind_grid.to_file(output_path, driver="GeoJSON")

        return wind_grid

    # ---------------------------------
    # ---------------------------------
    #          Other methods
    # ---------------------------------
    # ---------------------------------

    # def display_wind_field_grid(
    #     data_variable, name_variable, gdf_grid, cmap="coolwarm"
    # ):
    #     """
    #     Display wind field data from raster layer called "data_{name of a variable}

    #     Parameters
    #     ----------
    #     data_variable : np.array
    #         Raster layer extracted from georeferenced raster.
    #     name_variable : str
    #         The name of the wind variable (either "u", "v", "w", or "U").
    #     gdf_grid : GeoDataFrame
    #         The grid of the corresponding zone.

    #     Returns
    #     -------
    #     None
    #     """

    #     # --- Display wind and grid ---

    #     plt.figure(figsize=(8, 8))

    #     # Wind
    #     if any(data_variable is x for x in [data_u, data_v, data_w]):
    #         vmin = min(np.nanmin(data_u), np.nanmin(data_v), np.nanmin(data_w))
    #         vmax = max(np.nanmax(data_u), np.nanmax(data_v), np.nanmax(data_w))
    #     else:  # case data_variable = data_variable
    #         vmin = np.nanmin(data_variable)
    #         vmax = np.nanmax(data_variable)

    #     extent = (
    #         transform.c,  # xmin
    #         transform.c + data_variable.shape[1] * transform.a,  # xmax
    #         transform.f + data_variable.shape[0] * transform.e,  # ymin
    #         transform.f,  # ymax
    #     )
    #     plt.imshow(
    #         data_variable,
    #         cmap=cmap,
    #         vmin=vmin,
    #         vmax=vmax,
    #         extent=extent,
    #         origin="upper",
    #     )
    #     plt.colorbar(label=f"{name_variable} (m/s)")

    #     # Grid
    #     for poly in gdf_grid.geometry:
    #         gx, gy = poly.exterior.xy
    #         plt.plot(
    #             gx,
    #             gy,
    #             color="gray",
    #             linewidth=3,
    #             label=(
    #                 "Grid"
    #                 if "Grid" not in plt.gca().get_legend_handles_labels()[1]
    #                 else ""
    #             ),
    #         )

    #     # Options
    #     plt.axis("equal")
    #     plt.title(f"Wind field {name_variable} and grid")
    #     plt.legend()
    #     plt.show()

    # ---------------------------------
    # ---------------------------------

    def show_matrix_plot(
        data_variable,
        nom_variable,
        title=None,
        cmap="coolwarm",
        interpolation="nearest",
    ):
        """
        Display plot of the input array.

        Parameters
        ----------
        data_variable : np.array
        nom_variable : str
        title : str, optional
            The title of the plot.
            If none, "Representation of {nom_variable}"
        cmap : str
            The colourmap used, "coolwarm" by default.
        interpolation : str
            The interpolation used in plt.imshow, "nearest" by default.

        Returns
        -------
        None.
        """

        if title is None:
            title = f"Representation of {nom_variable}"
        else:
            pass

        plt.figure()
        plt.imshow(data_variable, cmap=cmap, interpolation=interpolation)
        plt.colorbar(label=f"{nom_variable}")
        plt.title(title)
        plt.show()
        # plt.close()
