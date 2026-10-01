#######################################################################

### CLASS : METADATA INSTANTIATION

#######################################################################


# --- Packages ------------------------------------------------------

import pandas as pd
import numpy as np
import os
import re
from rasterio.transform import from_origin
from pyproj import CRS

from typing import Optional, List, Tuple, Dict, Any
import logging

# Configure logging simple
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Metadata")


# --- Define class ----------------------------------------------


class Metadata:
    """
    Defines the metadata of UrbanTALES project.

    Attributes
    ----------
    path_metadata : str
        The path to the metadata file.
    metadata_df : pd.DataFrame
        The metadata file.

    Methods
    -------
    get_country(filename_e) :
        Returns the country and the state from the filename.
    retrieve_filenames(country, state) :
        Retrieve filename from input information.
    retrieve_wind_info(filename_e) :
        Create a dictionnary with all information linked to the filename.
    add_angle_to_metadata(angle, filename) :
        Add an angle value in the 'angle_domain' column for all rows whose 'NameE' starts with the base prefix of filename_e.
    add_name_topo_to_metadata(name_topo, filename_e) :
        Add another name for the topo file in the 'name_topo' column for all rows whose 'NameE' starts with the base prefix of filename_e.

    """

    def __init__(self, path_metadata):
        self.path_metadata = path_metadata
        self.metadata_df = self._load_metadata()

    # -------------------------
    # -------------------------

    def _load_metadata(self, filter_realistic: bool = True) -> pd.DataFrame:
        """
        Load metadata.csv and store it in self.metadata_df.
        Optionally, keep only the “realistic” configurations.

        Parameters
        ----------
        filter_realistic: bool (default value = True)
            If True, filter only realistic cases in UrbanTALES domains when loading the metadata.

        Returns
        -------
        pd.DataFrame : the metadata file loaded.
        """

        if not os.path.isfile(self.path_metadata):
            raise FileNotFoundError(f"metadata.csv not found at {self.path_metadata}")

        df = pd.read_csv(self.path_metadata)
        if filter_realistic and "Config" in df.columns:
            df = df[
                df["Config"].astype(str).str.contains("realistic", case=False, na=False)
            ].copy()

        # Standardize text columns for search convenience
        for col in ["Country", "State", "NameI", "NameE", "City"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        self.metadata_df = df
        logger.info("Metadata loaded (%d rows).", len(df))
        return df

    # -------------------------
    # -------------------------

    def get_country(self, filename_e):
        """
        Returns the country and the state from the filename.
        Handles:
            - no match found
            - NaN values
            - non-latin characters (kept as-is)

        Parameters
        ----------
        filename_e : str
            The name of scenario (domain + wind direction) in its export format.

        Returns
        -------
        (str, str) : the country and state of the domain.
        """
        df = self.metadata_df.copy()

        # Text cleaning (lowercase, strip whitespace)
        df["Country_clean"] = df["Country"].astype(str).str.strip().str.lower()
        df["State_clean"] = df["State"].astype(str).str.strip().str.lower()

        # Select matching rows
        row = df.loc[df["NameE"] == filename_e]

        if row.empty:
            print("No matching filename found")
            return None, None

        # Extract the first (and only) match
        country = row["Country_clean"].iloc[0]
        state = row["State_clean"].iloc[0]

        # Handle NaN values → replace with None
        if pd.isna(country) or country == "nan":
            country = None
        if pd.isna(state) or state == "nan":
            state = None

        # country/state may contain non-Latin characters → that's fine
        # They are returned unchanged, but always lowercased if they were strings.

        return country, state

    # -------------------------
    # -------------------------

    def retrieve_filenames(
        self, country: str, state: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Retrieve filename from input information like the country and the state.
        As there may be several configurations (there may be many different configurations for one state),
        the results are printed as a list.

        Parameters
        ----------
        country : str
            The country as written in metadata.csv.
        state : str, optional
            The state as written in metadata.csv.

        Returns
        -------
        List of pairs (NameI, NameE) corresponding to input information.
        """

        df = self.metadata_df.copy()

        # Text cleaning
        df["Country_clean"] = df["Country"].astype(str).str.strip().str.lower()
        df["State_clean"] = df["State"].astype(str).str.strip().str.lower()
        country_clean = str(country).strip().lower()
        state_clean = str(state).strip().lower() if state else None

        if state_clean:
            mask = (df["Country_clean"] == country_clean) & (
                df["State_clean"] == state_clean
            )
        else:
            mask = df["Country_clean"] == country_clean

        matches = df.loc[mask, ["NameI", "NameE"]]

        results = list(matches.itertuples(index=False, name=None))
        logger.info(
            "retrieve_filenames: found %d matches for country=%s state=%s",
            len(results),
            country,
            state,
        )
        return results

    # -------------------------
    # -------------------------

    def retrieve_wind_info(
        self,
        filename_e: str,
    ):
        """
        Create a dictionnary with all information linked to the filename (in export type).

        Parameters
        ----------
        filename_e : str
            The name of the work zone and of the file, in export type (exemple: FR-Par-V2_d30)

        Returns
        -------
        A dictionnary of wind information.
        """

        # Load metadata
        if self.metadata_df is None:
            self._load_metadata()

        # metadata info
        info_row = self.metadata_df[self.metadata_df["NameE"] == filename_e].iloc[0]
        nameE = info_row.get("NameE", filename_e)
        nameI = info_row.get("NameI", None)
        wind_dir = info_row.get("WD", None)
        lon = float(info_row.get("Longitude", np.nan))
        lat = float(info_row.get("Latitude", np.nan))
        city = info_row.get("City", "")
        state = info_row.get("State", "")

        # Decide localisation string (fallback to state on non-latin city)
        if re.search(r"[^A-Za-z0-9\s\-]", str(city)):
            localisation = state
            logger.info(
                "City contains non-latin chars. Using State '%s' as localisation.",
                state,
            )
        else:
            localisation = city
        logger.info("Localisation: %s", localisation)

        # compute UTM zone / EPSG
        try:
            zone = int((lon + 180) / 6) + 1
            if lat >= 0:
                epsg_code = 32600 + zone  # north hemisphere
            else:
                epsg_code = 32700 + zone  # south hemisphere
            crs_utm = CRS.from_epsg(epsg_code)
            logger.info("Computed UTM EPSG:%d", epsg_code)
        except Exception:
            crs_utm = None
            epsg_code = None
            logger.warning(
                "Could not compute UTM from lon/lat: lon=%s lat=%s", lon, lat
            )

        wind_dict = {
            "filename_e": nameE,
            "filename_i": nameI,
            "wind_dir": wind_dir,
            "lon": lon,
            "lat": lat,
            "city": city,
            "localisation": localisation,
            "epsg": crs_utm,
            # "exported_files": exported_levels,
        }

        return wind_dict

    # -------------------------
    # -------------------------

    def add_angle_to_metadata(self, angle: float, filename_e: str):
        """
        Add an angle value in the 'angle_domain' column for all rows whose 'NameE'
        starts with the base prefix of filename_e (i.e. before the '_d...').

        Parameters
        ----------
        angle : float
            The angle value that will be added to metadata.
        filename_e : str
            The name of scenario in export format.

        Returns
        -------
        Updated metadata file.

        Example
        -------
        filename_e = "UA-Kyi-V6_d45"
            --> prefix = "UA-Kyi-V6"
            --> update all rows where NameE starts with this prefix.
        """

        # Extract prefix before `_dXX`
        match = re.match(r"(.*)_d\d+", filename_e)
        if match:
            prefix = match.group(1)
        else:
            # If no pattern, use the full filename_e as prefix
            prefix = filename_e

        # Ensure the column exists
        if "angle_domain" not in self.metadata_df.columns:
            self.metadata_df["angle_domain"] = None

        # Identify matching rows
        mask = self.metadata_df["NameE"].str.startswith(prefix)

        if not mask.any():
            raise ValueError(
                f"No rows found where 'NameE' starts with prefix '{prefix}'."
            )

        # Update angle for all matching rows
        self.metadata_df.loc[mask, "angle_domain"] = angle
        print(f"Angle {angle} ajouté pour les préfixes de {filename_e} (avant _dXX)")

        # Save
        self.metadata_df.to_csv(self.path_metadata, index=False)
        print("metadata file saved locally")

        return self.metadata_df

    # -------------------------
    # -------------------------

    def add_name_topo_to_metadata(self, name_topo: str, filename_e: str):
        """
        Add another name for the topo file in the 'name_topo' column for all rows whose 'NameE'
        starts with the base prefix of filename_e (i.e. before the '_d...').

        Parameters
        ----------
        name_topo : str
            The name of topo file that will be added in metadata file.
        filename_e : str
            The name of scenario in export format.

        Returns
        -------
        Updated metadata file.

        Example
        -------
        filename_e = "UA-Kyi-V6_d45"
        --> prefix = "UA-Kyi-V6"
        --> update all rows where NameE starts with this prefix.
        """

        # Extract prefix before `_dXX`
        match = re.match(r"(.*)_d\d+", filename_e)
        if match:
            prefix = match.group(1)
        else:
            # If no pattern, use the full filename_e as prefix
            prefix = filename_e

        # Ensure the column exists
        if "name_topo" not in self.metadata_df.columns:
            self.metadata_df["name_topo"] = None

        # Identify matching rows
        mask = self.metadata_df["NameE"].str.startswith(prefix)

        if not mask.any():
            raise ValueError(
                f"No rows found where 'NameE' starts with prefix '{prefix}'."
            )

        # Update angle for all matching rows
        self.metadata_df.loc[mask, "name_topo"] = name_topo
        print(
            f"Name {name_topo} for topo file added for all prefixes of {filename_e} (before _dXX)"
        )

        # Save
        self.metadata_df.to_csv(self.path_metadata, index=False)
        print("metadata file saved locally")

        return self.metadata_df
