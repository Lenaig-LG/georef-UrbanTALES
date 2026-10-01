#######################################################################

### CLASS : FINAL GRID CREATION

#######################################################################


# --- Packages --------------------------------------------------------

import os
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio

from scripts.grid import Grid
from scripts.wind_grid import WindGrid
from scripts.geo_grid import GeoGrid

# --- Define class ----------------------------------------------------


class FinalGrid:
    """
    Defines the final grid containing wind variables and geographical variables on the domain.

    Attributes
    ----------
    wind_grid : WindGrid
        A WindGrid object containing the wind variables.
    geo_grid : GeoGrid
        A GeoGrid object containing the geographical variables.
    final_output : str
        The path to store the final grid.
    """

    def __init__(
        self, wind_grid: WindGrid, geo_grid: GeoGrid, final_output: str = None
    ):
        self.wind_grid = wind_grid
        self.geo_grid = geo_grid

        self.filename_e = self.wind_grid.grid.filename_e
        self.georef_output = self.wind_grid.grid.georef_output
        self.target_resolution = wind_grid.target_resolution
        if final_output is not None:
            self.output_path = final_output
        else:
            self.output_path = self.georef_output

        # Load gdfs from Grid objects
        self.final_grid = self._join_gdf(
            gdf1=self.wind_grid.gdf_wind_grid,
            gdf2=self.geo_grid.gdf_geo_grid,
            output_path=self.output_path,
        )  # join on cell id

    # ---------------------------------
    # ---------------------------------

    def _join_gdf(self, gdf1, gdf2, output_path, var_join="CELL_ID"):
        """
        Join two geodataframes files to obtain a final dataframe.

        Parameters
        ----------
        gdf1 : GeoDataFrame
            The first geodataframe.
        gdf2 : GeoDataFrame
            The second geodataframe.
        output_path : str
            The output path to store the final gdf.
        var_join : str, optional
            The column name to use for joining (default: 'CELL_ID').

        Return
        ------
        The joined GeoDataFrame.

        """

        # --- Normalize join variable name to uppercase in both dataframes ---
        gdf1.columns = [col.upper() for col in gdf1.columns]
        gdf2.columns = [col.upper() for col in gdf2.columns]
        var_join = var_join.upper()

        # --- Check if gdf have active geometry column ---
        for gdf_name, gdf in zip(["gdf1", "gdf2"], [gdf1, gdf2]):
            if "GEOMETRY" in gdf.columns:
                if (
                    not hasattr(gdf, "geometry")
                    or gdf._geometry_column_name != "GEOMETRY"
                ):
                    gdf = gdf.set_geometry("GEOMETRY")
                    print(f"✅ Set GEOMETRY as active geometry for {gdf_name}")
            else:
                raise AttributeError(f"{gdf_name} does not contain a GEOMETRY column.")

            # update the local variable
            if gdf_name == "gdf1":
                gdf1 = gdf
            else:
                gdf2 = gdf

        # ---  CRS harmonization if necessary ---
        if gdf1.crs != gdf2.crs:
            gdf2 = gdf2.to_crs(gdf1.crs)
            print("CRS harmonized.")

        # --- Check that the join column exists in both dataframes ---
        for i, gdf in enumerate([gdf1, gdf2], start=1):
            if var_join not in gdf.columns:
                raise KeyError(f"{var_join} not found in gdf{i} columns.")

        # # Visual check if geometries overlap (we want it to overlaps)
        # ax = gdf_geo.plot(edgecolor="red", facecolor="none")
        # gdf_all_wind.plot(ax=ax, edgecolor="blue", facecolor="none")

        # --- Perform the join on the specified column ---
        gdf_joined = gdf1.merge(gdf2, on=var_join, how="inner")

        # --- Clean the columns geometry
        # If two columns GEOMETRY appear, compare true geometries
        if "GEOMETRY_x" in gdf_joined.columns and "GEOMETRY_y" in gdf_joined.columns:
            # Compare the geometry with .equals() line by line
            geometries_equal = gdf_joined.apply(
                lambda row: row["GEOMETRY_x"].equals(row["GEOMETRY_y"]), axis=1
            )

            if geometries_equal.all():
                # Remove one and rename the other
                gdf_joined = gdf_joined.drop(columns=["GEOMETRY_x"])
                gdf_joined = gdf_joined.rename(columns={"GEOMETRY_y": "GEOMETRY"})
                print(
                    "✅ Identical geometries detected: kept only one geometry column."
                )
            else:
                print("⚠️ Warning: GEOMETRY_x and GEOMETRY_y differ — keeping both.")

        # --- Redefine active geometry
        if "GEOMETRY" in gdf_joined.columns:
            gdf_joined = gdf_joined.set_geometry("GEOMETRY")

        # --- Save ---
        output = os.path.join(
            output_path, self.filename_e, f"final_{self.target_resolution}m.geojson"
        )
        gdf_joined.to_file(output, driver="GeoJSON")
        print(f"Saved in: {output}")

        return gdf_joined
