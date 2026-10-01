#######################################################################

### CLASS : GRID CREATION AND LOADING

#######################################################################


# --- Packages --------------------------------------------------------

import os
import re
import numpy as np
import pandas as pd
import rasterio
import pprint as pp
from rasterio import features
from shapely.geometry import shape, mapping
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import geopandas as gpd
import matplotlib.pyplot as plt
import csv
import folium

# from python_code.Data_preparation.wind_import import WindImport
# from python_code.Data_preparation.topo import Topo

# --- Define class ----------------------------------------------------


class Grid:
    """
    Defines a regular grid on the UrbanTALES scenario.

    Attributes
    ----------
    georef_output : str
        The path where georef outputs are stored.
    path_data : str
        The general path to data.
    filename_e : str
        The name of scenario in export format (e.g.: "FR-Par-V2_d15").
    buffer : int
        The length we remove at each side of the bounding box of the domain.
    target_resolution: float
        The cell resolution desired (in the project = 50 m).
    epsg : int
        The epsg of the scenario/domain.
    """

    def __init__(
        self,
        georef_output: str,
        path_data: str,
        filename_e: str,
        buffer: int,
        target_resolution: float,
        epsg,
    ):
        # Attributes' initialisation
        self.georef_output = georef_output
        self.path_data = path_data
        self.filename_e = filename_e
        self.buffer = buffer
        self.target_resolution = target_resolution
        self.epsg = epsg

        # Grid instanciation
        # if the grid is still created, load grid
        # if not, create the grid

        try:
            # Try loading existing grid
            self.gdf_grid = self._load_grid()
            self.corners_df = pd.read_csv(
                os.path.join(
                    self.georef_output, self.filename_e, "polygon_contour_coins.csv"
                )
            )
            print("✅ Grid successfully loaded.")

        except Exception as e:
            # If grid doesn't exist yet, creation here
            print(f"⚠️ Grid not found or failed to load ({e}) \n Creating new grid...")

            perimeter_polygon = self._define_perimeter_polygon(viz=True)
            self.corners_df = self._retrieve_corners(perimeter_polygon, viz=True)
            inner_polygon = self._define_inner_polygon(
                epsg_WGS84=4326, viz=False, interactive_map=True
            )
            self.gdf_grid = self._create_grid_in_polygon(polygon_inner=inner_polygon)
            print("✅ Grid successfully created.")

    # ---------------------------
    # ---------------------------

    # Mask polygon

    def _extract_polygon_from_raster(self, viz=False):
        """
        Extract a polygon from the valid wind data stored in georeferenced 0.25 layers.

        Parameters
        ----------

        viz : bool, optional
            If a plot is displayed or not.

        Return
        ------

        GeoDataFrame
            A GeoDataFrame with the polygon extracted.

        """

        # --- Load georeferenced raster ---

        print("Loading wind_layer_0.25_georef.tif...")

        layer_path = os.path.join(
            self.georef_output, self.filename_e, "wind_layer_0.25_georef.tif"
        )
        output_geojson = os.path.join(
            self.georef_output, self.filename_e, "polygon_mask.geojson"
        )

        with rasterio.open(layer_path) as src:
            data_u = src.read(1)
            # data_v = src.read(2)
            # data_w = src.read(3)
            # data_U = src.read(4)
            transform = src.transform
            crs_raster = src.crs

        # create a mask on valid data (True = valid data)
        mask_valid = (
            (~np.isnan(data_u))
            & (data_u != 0)
            # | (~np.isnan(data_v)) & (data_v != 0)
            # | (~np.isnan(data_w)) & (data_w != 0)
            # | (~np.isnan(data_U)) & (data_U != 0)
        )

        # show_matrix_plot(mask_valid, "mask", cmap="hot")

        # Conversion into uint8 (1 for True, 0 for False)
        mask_img = mask_valid.astype("uint8")

        # rasterio.features.shapes -> generate (geom, value) for each non-zero area
        shapes_generator = features.shapes(mask_img, mask=mask_img, transform=transform)

        polygons = []
        for geom_dict, value in shapes_generator:
            if int(value) == 1:
                polygons.append(shape(geom_dict))

        if not polygons:
            raise ValueError("Neither extracted geometry from the mask.")

        # Merge all geometries to only one (dissolve / union)
        union = unary_union(polygons)

        # # Keep only the greatest part
        # if union.geom_type == "MultiPolygon":
        #     largest = max(union, key=lambda p: p.area)
        #     geom_to_save = largest
        # else:
        #     geom_to_save = union

        gdf_final = gpd.GeoDataFrame({"id": [1]}, geometry=[union], crs=crs_raster)

        if viz:
            plt.figure(figsize=(8, 8))
            gdf_final.plot(color="lightblue", edgecolor="black")
            plt.title("Polygon extracted from valid wind data", fontsize=14)
            plt.xlabel("Longitude")
            plt.ylabel("Latitude")
            plt.grid(True)
            plt.axis("equal")
            plt.show()
        else:
            pass

        # Export in GeoJSON
        os.makedirs(os.path.dirname(output_geojson), exist_ok=True)
        gdf_final.to_file(output_geojson, driver="GeoJSON")

        print("✅ GeoJSON saved :", output_geojson)

        return gdf_final

    ##############################################################################

    ### PRELIMINARY WORK ON THE POLYGON ###

    ##############################################################################

    def _define_perimeter_polygon(self, viz=False):
        """
        Calculates the oriented minimum bounding box of a polygon
        derived from a polygonized shapefile, and exports the result as GeoJSON and CSV.

        Main steps: dissolve + reprojection + oriented minimum *bounding box*.
        Generates a CSV file containing the four labeled vertices of the polygon.

        Parameters
        ----------
        georef_output : str
            The root folder with georeferenced data.
        work_zone : str
            The localisation (expl: "HdS", "Par"...).
        epsg : int
            The EPSG code of the work_zone. Emphasize local UTM (expl : 32631).
        viz : bool, optional
            If True, show a matplotlib visualization of the polygon perimeter and containing rectangle.

        Returns
        -------
        perimeter_gdf : GeoDataFrame
            The perimeter of the input polygon.
            Also saved in geojson in georef_output folder.

        """

        # --- 0. Preliminary verifications ---

        # Check if folder exists
        if not os.path.isdir(self.georef_output):
            raise FileNotFoundError(
                f"❌ The georef_output folder does not exist: {self.georef_output}"
            )

        # --- 1. Instantiate the gdf polygon ---

        print("Retrieve dbf file...")
        # Build the path to the polygon
        dbf_path = os.path.join(
            self.georef_output, f"{self.filename_e}/wind_layer_0.25_polygon.dbf"
        )

        # Check if file exists, else create the polygon with _extract_polygon_from_raster function
        if os.path.isfile(dbf_path):
            print(f"✅ File found: {dbf_path}")
            gdf = gpd.read_file(dbf_path)
        else:
            print(
                f"❌ The file '{dbf_path}' is untraceable. \n Polygonization of a wind layer..."
            )
            gdf = self._extract_polygon_from_raster(viz=False)

        print(f"Insight on the polygon: \n", gdf.head())

        # if viz == True:
        #     plt.figure()
        #     gdf.plot(edgecolor="black", facecolor="lightblue")
        #     plt.show()
        #     # polygon = gdf.geometry.iloc[0]
        #     # polygon.exterior.xy

        # --- 2. Dissolve ---

        # Merge all polygons to only one
        gdf_diss = gdf.dissolve()
        # gdf_diss = gdf_diss.geometry.iloc[0]
        # gdf_diss.exterior.xy
        print("After dissolve : \n", gdf_diss)
        print("✅ Dissolve done.")

        # --- 3. Reproject to correct epsg ---

        gdf_reproj = gdf_diss.to_crs(epsg=self.epsg)
        print(f"✅ Reprojection into EPSG {self.epsg} done.")

        # --- 4. Compute oriented minimum bounding box ---

        # (shapely >= 1.8 : minimum_rotated_rectangle)
        geom = gdf_reproj.geometry.iloc[0]
        obb = geom.minimum_rotated_rectangle
        print("✅ Computation of minimum oriented bounding box done.")

        # --- 5. Save into GeoJSON ---

        output_path = os.path.join(
            self.georef_output, f"{self.filename_e}/polygon_contour.geojson"
        )
        perimeter_gdf = gpd.GeoDataFrame(geometry=[obb], crs=gdf_reproj.crs)
        perimeter_gdf.to_file(output_path, driver="GeoJSON")
        print(f"✅ GeoJSON created: {output_path}")

        # --- 6. Extract 4 corners of the polygon ---

        # The rectangle is represented by a closed polygon (5 points, the last repeated the first one)
        coords = list(obb.exterior.coords)[:-1]

        # --- 7. Ordonnate corners ---

        # Sort by y then by x, then reconstitution
        coords_sorted = sorted(
            coords, key=lambda p: (p[1], p[0])
        )  # sort firstly by Y then X
        bas = sorted(coords_sorted[:2], key=lambda p: p[0])
        haut = sorted(coords_sorted[2:], key=lambda p: p[0])
        ordered_coords = [bas[0], bas[1], haut[1], haut[0]]
        coin_names = ["Bottom_Left", "Bottom_Right", "High_Right", "High_Left"]

        # --- 8. Save into CSV ---

        csv_path = output_path.replace(".geojson", "_coins.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Corner", "X", "Y"])
            for name, (x, y) in zip(coin_names, ordered_coords):
                writer.writerow([name, x, y])
        print(f"✅ CSV of corners created: {csv_path}")

        corners_df = pd.read_csv(csv_path)

        # plt.figure(figsize=(10, 8))
        # plt.scatter(df["X"], df["Y"], color="blue")
        # # Ajout des étiquettes pour chaque point
        # for index, row in df.iterrows():
        #     plt.text(row["X"], row["Y"], row["Coin"], fontsize=9, ha="right")
        # # Configuration du graphique
        # plt.title("Tracé des points géographiques")
        # plt.xlabel("Coordonnée X")
        # plt.ylabel("Coordonnée Y")
        # plt.grid(True)
        # plt.axis("equal")  # Pour que les échelles soient identiques sur les deux axes
        # plt.show()
        # # plt.close()

        # --- 9. Optionnal visualisation ---

        if viz:
            print("ℹ️ Visualization of polygon and containing rectangle:")
            print("Geom count:", len(gdf_reproj))
            print("OBB bounds:", obb.bounds)
            print("CRS:", gdf_reproj.crs)
            plt.figure()
            base = gdf_reproj.plot(edgecolor="gray", facecolor="lightblue")
            gpd.GeoSeries(obb).plot(
                ax=base, edgecolor="red", facecolor="none", linewidth=2
            )

            xs, ys = zip(*ordered_coords)
            plt.scatter(xs, ys, c="red")
            for i, (x, y) in enumerate(ordered_coords):
                plt.text(x, y, f"{coin_names[i]}", fontsize=8, ha="center", va="bottom")
            plt.title("Layout of polygon corners and containing rectangle")
            plt.show()
            # plt.close()
        # else:
        # print("ℹ️ No request for visualization.")

        # print("🎯 End of execution")

        return perimeter_gdf

    ##############################################################################

    ### GRID CREATION BASED ON THE GEOJSON FILE ###

    ##############################################################################

    def _retrieve_corners(self, polygon_gdf, viz=False):
        """
        Retrieve the corners and their spatial names (bottom left, high right...)

        Parameters
        ----------
        polygon_gdf : GeoDataFrame
        viz : bool, optional

        Return
        ------
        A DataFrame with corners' geographical coordinates and name attribution.

        """

        output_path = os.path.join(
            self.georef_output, f"{self.filename_e}/polygon_contour.geojson"
        )

        geom = polygon_gdf.geometry.iloc[0]
        # The rectangle is represented by a closed polygon (5 points, the last repeated the first one)
        coords = list(geom.exterior.coords)[:-1]

        # Ordonnate corners
        # Sort by y then by x, then reconstitution
        coords_sorted = sorted(
            coords, key=lambda p: (p[1], p[0])
        )  # sort firstly by Y then X
        bas = sorted(coords_sorted[:2], key=lambda p: p[0])
        haut = sorted(coords_sorted[2:], key=lambda p: p[0])
        ordered_coords = [bas[0], bas[1], haut[1], haut[0]]
        corner_names = ["Bottom_Left", "Bottom_Right", "High_Right", "High_Left"]

        # Save into csv
        csv_path = output_path.replace(".geojson", "_coins.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Corner", "X", "Y"])
            for name, (x, y) in zip(corner_names, ordered_coords):
                writer.writerow([name, x, y])
        print(f"✅ CSV of corners created: {csv_path}")
        corners_df = pd.read_csv(csv_path)

        if viz:
            print("ℹ️ Visualization of polygon and containing rectangle:")
            print("CRS:", polygon_gdf.crs)
            plt.figure()
            base = polygon_gdf.plot(edgecolor="gray", facecolor="lightblue")
            # gpd.GeoSeries(obb).plot(ax=base, edgecolor="red", facecolor="none", linewidth=2)

            xs, ys = zip(*ordered_coords)
            plt.scatter(xs, ys, c="red")
            for i, (x, y) in enumerate(ordered_coords):
                plt.text(
                    x, y, f"{corner_names[i]}", fontsize=8, ha="center", va="bottom"
                )
            plt.title("Layout of polygon corners and containing rectangle")
            plt.show()
            # plt.close()
        else:
            print("ℹ️ No request for visualization.")

        return corners_df

    # -----------------------
    # -----------------------

    def _define_inner_polygon(
        self,
        epsg_WGS84=4326,
        viz=False,
        interactive_map=True,
    ):
        """
        Create the inner polygon, corresponding to the perimeter of the future grid.
        The inner polygon is centered.

        Parameters
        ----------
        work_zone : str
            The localisation (expl: "HdS", "Par"...).
        epsg : str
            The local UTM epsg code.
        epsg_WGS84 : int
            The WGS84 code for EPSG of the work_zone. Used only if interactibve_map = true.
        perimeter_polygon : GeoDataFrame
            The output polygon of _define_perimeter_polygon function.
        buffer : float
            The length we remove at each side of the polygon.
        georef_output : str
            The root folder with georeferenced data.
        viz_inner : bool, optional
            If True, show a matplotlib visualization of the outer and inner polygons.
        interactive_map : bool, optional
            If True, create a Folium interactive map for the input polygon.

        Returns
        -------
        polygon_inner : GeoDataFrame
            The inner polygon created, centered.
            Also saved in geojson in output path.
        """

        # --- 0. Check directories and paths ---

        work_dir = os.path.join(self.georef_output, self.filename_e)
        if not os.path.exists(work_dir):
            raise FileNotFoundError(f"❌ The directory '{work_dir}' does not exist.")
        # geojson_path = os.path.join(work_dir, "losange_contour.geojson")
        # if not os.path.isfile(geojson_path):
        #     raise FileNotFoundError(f"❌ File not found: {geojson_path}")

        # --- 1. Construct perimeter polygon ---

        perimeter_polygon = self._define_perimeter_polygon()

        # --- 2. Interactive map (optionnal) ---

        if interactive_map:
            print(
                "ℹ️ Interactive visualization of the input polygon (before inner reduction):"
            )
            try:
                # Visual insight
                # gdf = gpd.read_file(os.path.join(geojson_path))
                # gdf.plot(edgecolor="black", facecolor="lightblue")
                # plt.show()
                # plt.close()
                # Reproject in WGS84 (lat/lon)
                gdf_map = perimeter_polygon.to_crs(epsg=epsg_WGS84)
                m = folium.Map(
                    location=[
                        gdf_map.geometry.centroid.y.iloc[0],
                        gdf_map.geometry.centroid.x.iloc[0],
                    ],
                    zoom_start=15,
                )
                # Add the polygon
                folium.GeoJson(gdf_map).add_to(m)
                map_path = os.path.join(work_dir, "perimeter_polygon.html")
                m.save(map_path)
                print(f"✅ Interactive map saved at: {map_path}")
                m
            except Exception as e:
                print(f"⚠️ Could not generate interactive map: {e}")
        else:
            print("ℹ️ No request for interactive visualisation of the input polygon.")

        # --- 3. Construct the inner polygon ---

        # bottom_left = data["features"][0]["geometry"]["coordinates"][0][0]
        # bottom_right = data["features"][0]["geometry"]["coordinates"][0][1]
        # upper_right = data["features"][0]["geometry"]["coordinates"][0][2]
        # upper_left = data["features"][0]["geometry"]["coordinates"][0][3]
        try:
            polygon = perimeter_polygon.geometry
        except Exception as e:
            raise ValueError(f"❌ Invalid polygon structure in GeoJSON: {e}")

        # Reduce the polygon inward (negative buffer)
        polygon_inner = polygon.buffer(-self.buffer)  # 20 m erosion on each sides
        print("✅ Inner polygon created successfully.")
        print("Insight of polygon_inner: \n", polygon_inner)

        # --- 4. Visualisation of inner polygon (optionnal) ---

        if viz:
            print("ℹ️ Visualization of constructed inner polygon:")
            try:
                # Plot
                x, y = polygon.exterior.xy
                x_bis, y_bis = polygon_inner.exterior.xy
                plt.figure(figsize=(6, 6))
                plt.plot(x, y, color="black", linewidth=1)
                plt.fill(x, y, alpha=0.2, facecolor="lightblue")

                plt.plot(x_bis, y_bis, color="red", linewidth=1)
                plt.fill(x_bis, y_bis, alpha=0.2, facecolor="red")

                plt.legend()
                plt.axis("equal")
                plt.show()
                # plt.close()
            except Exception as e:
                print(f"⚠️ Could not visualize polygons: {e}")
        else:
            print("ℹ️ No request for visualization of the inner polygon.")

        # --- 5. Save inner polygon into GeoJSON ---

        # Convert the Shapely polygon into a GeoJSON dict
        output_path = os.path.join(work_dir, "polygon_contour_inner.geojson")
        try:
            gdf_inner = gpd.GeoDataFrame(
                geometry=polygon_inner, crs=f"EPSG:{self.epsg}"
            )
            gdf_inner.to_file(output_path, driver="GeoJSON")
            print(f"✅ Inner polygon saved successfully at: {output_path}")
        except Exception as e:
            raise IOError(f"❌ Failed to save inner polygon: {e}")

        gdf_final = gpd.read_file(output_path)

        return gdf_final

    # --------------------------------
    # --------------------------------

    def _create_grid_in_polygon(
        self,
        polygon_inner,
        align_to: str = "center",  # "center" or "bottom_left"
    ):
        """
        Create a regular grid of square cells with exact resolution inside a given polygon.
        The grid is centered (default) or aligned from the bottom-left corner.

        Parameters
        ----------
        polygon_inner : GeoDataFrame
            The input polygon (buffered, centered).
        align_to : {"center", "bottom_left"}, optional
            Define the alignment of the grid inside the polygon.
            - "center": center the grid in the polygon (default)
            - "bottom_left": start grid from bottom-left corner

        Returns
        -------
        GeoDataFrame
            The grid contained in the polygon, with square cells of exact resolution.
        """

        output_folder = os.path.join(self.georef_output, self.filename_e)
        os.makedirs(output_folder, exist_ok=True)

        # --- 1. Retrieve polygon corners ---
        corners_df = self._retrieve_corners(polygon_gdf=polygon_inner)

        bl = corners_df[corners_df["Corner"] == "Bottom_Left"][["X", "Y"]].values[0]
        br = corners_df[corners_df["Corner"] == "Bottom_Right"][["X", "Y"]].values[0]
        hl = corners_df[corners_df["Corner"] == "High_Left"][["X", "Y"]].values[0]

        print(f"📌 Bottom_left: {bl}, \n   Bottom_right: {br}, \n   High_left: {hl}")

        # --- 2. Compute rotation angle ---
        vec = np.array(br) - np.array(bl)
        angle = np.degrees(np.arctan2(vec[1], vec[0]))
        print(f"🔧 Necessary rotation to align the grid: {-angle:.2f}°")

        # --- 3. Rotate polygon to align it with axes ---
        if isinstance(polygon_inner, gpd.GeoDataFrame):
            polygon = polygon_inner.geometry.iloc[0]
        elif isinstance(polygon_inner, gpd.GeoSeries):
            polygon = polygon_inner.iloc[0]
        else:
            raise TypeError("polygon_inner must be a GeoDataFrame or GeoSeries.")

        polygon_rot = rotate(polygon, -angle, origin=tuple(bl), use_radians=False)

        # --- 4. Get bounding box of rotated polygon ---
        minx, miny, maxx, maxy = polygon_rot.bounds
        width = maxx - minx
        height = maxy - miny

        # Exact resolution wanted
        r = float(self.target_resolution)

        # --- 5. Compute how many full cells fit ---
        n_cols = int(np.floor(width / r))
        n_rows = int(np.floor(height / r))
        print(
            f"📐 Grid dimensions: {n_cols} cols × {n_rows} rows at {r:.2f} m resolution"
        )

        # --- 6. Define starting point according to alignment mode ---
        if align_to not in ["center", "bottom_left"]:
            raise ValueError("align_to must be 'center' or 'bottom_left'.")

        if align_to == "center":
            # Centered grid
            total_grid_width = n_cols * r
            total_grid_height = n_rows * r
            x_start = minx + (width - total_grid_width) / 2
            y_start = miny + (height - total_grid_height) / 2
            print("🎯 Grid alignment: centered within the polygon.")
        else:
            # Aligned to bottom-left
            x_start = minx
            y_start = miny
            print("📍 Grid alignment: bottom-left corner.")

        # --- 7. Create cells ---
        grid_cells = []
        for i in range(n_cols):
            for j in range(n_rows):
                x0 = x_start + i * r
                y0 = y_start + j * r
                x1 = x0 + r
                y1 = y0 + r
                cell = box(x0, y0, x1, y1)
                # Keep cells which center is inside polygons
                if polygon_rot.contains(cell.centroid):
                    grid_cells.append(cell)

        print(f"✅ Grid generated with {len(grid_cells)} exact {r:.1f} m squares.")

        # --- 8. Rotate back to original orientation ---
        grid_rot_back = [
            rotate(cell, angle, origin=tuple(bl), use_radians=False)
            for cell in grid_cells
        ]

        # --- 9. Export GeoDataFrame ---
        gdf_grid = gpd.GeoDataFrame(geometry=grid_rot_back, crs=f"EPSG:{self.epsg}")
        gdf_grid = self._create_cell_id(gdf=gdf_grid)
        gdf_grid = gdf_grid.drop("centroid", axis=1)

        output_path = os.path.join(
            self.georef_output,
            f"{self.filename_e}/grid_square_fixed_res_{int(r)}m_{align_to}.geojson",
        )
        gdf_grid.to_file(output_path, driver="GeoJSON")
        print(f"✅ Grid saved in GeoJSON: {output_path}")

        return gdf_grid

    # --------------------------------
    # --------------------------------
    # -        Other methods
    # --------------------------------
    # --------------------------------

    @staticmethod
    def _find_grid_file(folder, target_resolution):
        """
        Search a folder for the file ‘grid_square_aligned_resXXX.geojson’
        whose resolution is closest to target_resolution.
        """

        grid_path = os.path.join(
            folder, f"grid_square_fixed_res_{target_resolution}m_center.geojson"
        )
        return grid_path
        # pattern = re.compile(r"grid_square_aligned_res_([\d.]+)\.geojson$")
        # best_file = None
        # best_diff = float("inf")

        # for f in os.listdir(folder):
        #     match = pattern.match(f)
        #     if match:
        #         res = float(match.group(1))
        #         diff = abs(res - target_resolution)
        #         if diff < best_diff:
        #             best_diff = diff
        #             best_file = f

        # if best_file is not None:
        #     print("Success")
        #     return os.path.join(folder, best_file)
        # else:
        #     print("Not found.")
        #     return None

    # --------------------------------
    # --------------------------------

    def _load_grid(self):
        """
        Load the geojson grid file, retrieved with the given target resolution.

        Parameters
        ----------
        filename_e : str
            The name of the work zone (exemple: FR-Par-V2_d15).
        target_resolution : float
            The desired resolution of grid cells.

        Returns
        ------
        The GeoDataFrame of grid cells.

        Raises
        ------
        FileNotFoundError
            If no grid file matching the target resolution is found.

        """
        folder = os.path.join(self.georef_output, self.filename_e)
        grid_path = self._find_grid_file(
            folder=folder, target_resolution=self.target_resolution
        )
        # grid_path = os.path.join(
        #     folder, f"grid_square_fixed_res_{target_resolution}m_center.geojson"
        # )
        print("grid_path: ", grid_path)

        # if grid_path is None:
        #     raise FileNotFoundError(
        #         f"No grid file found for target resolution {self.target_resolution} in {folder}"
        #     )

        gdf_grid = gpd.read_file(grid_path)

        return gdf_grid

    # --------------------------------
    # --------------------------------

    def _create_cell_id(self, gdf):
        """
        Create cell as entities and attribute cell identifiers.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            A geodataframe object

        Return
        ------
        gpd.GeoDataFrame : the gdf updated.
        """

        # Compute centroids
        gdf["centroid"] = gdf.geometry.centroid
        gdf["x"] = gdf.centroid.x
        gdf["y"] = gdf.centroid.y

        # Sort by y (decreasing = top to the bottom) then by x (increasing = left to right)
        gdf = gdf.sort_values(by=["y", "x"], ascending=[False, True]).reset_index(
            drop=True
        )

        # Create a identifier cell_id based on this new order
        gdf["cell_id"] = gdf.index + 1

        # --- Visual check ---

        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        gdf.plot(
            column="cell_id",
            cmap="coolwarm",
            legend=True,
            ax=ax,
            edgecolor="k",
            linewidth=0.1,
        )
        for idx, row in gdf.iterrows():
            centroid = row.geometry.centroid
            ax.text(
                centroid.x,
                centroid.y,
                str(row.cell_id),
                fontsize=6,
                ha="center",
                va="center",
                color="black",
            )
        ax.set_title(f"Cell id for {self.filename_e}", fontsize=14)
        output_png = os.path.join(self.georef_output, self.filename_e, "cell_img.png")
        plt.savefig(output_png, dpi=300, bbox_inches="tight")
        plt.show()

        # plt.close()

        return gdf
