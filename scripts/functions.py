#######################################################################

### Functions used in the pipeline but not attached to a class

#######################################################################


# --- Packages ------------------------------------------------------
import os
import shutil
import subprocess
from typing import Optional, List, Tuple, Dict, Any

########################################################################

# --- Functions for georeferencement -----------------------------------


def list_nc_files(path_3d_folder) -> List[str]:
    """
    Make the list of all .nc files in the 3Dwind folder.
    """

    folder = path_3d_folder

    if not os.path.isdir(folder):
        print("3D folder does not exist: %s", folder)
        return []

    return [f for f in os.listdir(folder) if f.endswith(".nc")]


# ------
# ------


def is_folder_empty(path):
    return not os.path.exists(path) or (os.path.isdir(path) and not os.listdir(path))


# ------
# ------


def prepare_georef(filename_e, georef_output):
    """
    Creation of output folder.

    Parameters
    ----------
    filename_e : str.
        The name of the work zone (scenario) (e.g.: "FR-Par-V2_d15").
    georef_output : str.
        The path to folder where georeferenced files will be stored.

    Returns
    -------
    str : folder path to store the future georeferenced files of the associated filename_e.
    """

    out_dir = os.path.join(georef_output, f"{filename_e}")
    os.makedirs(out_dir, exist_ok=True)

    print("Prepare tmp folder like presented in 0_expl_tmp.")

    return out_dir


# ------
# ------


from scripts.topo_raster import TopoRaster


def prepare_tmp(
    filename_e,
    topo: TopoRaster,
    georef_input,
    groovy_path,
    path_data,
    tmp_path="/tmp/lenaig",
):
    """
    Prepare tmp folder to georeference function.

    Parameters
    ----------
    filename_e : str
        The name of the work zone (scenario) (exemple: "FR-Par-V2_d15").
    topo : Topo
        Object from Topo class, associated with same filename_e.
    georef_input : str
        The path to wind rasters to georeference.
    groovy_path : str
        The path to the WindDataGDALCommands.groovy script.
    path_data : str
        General path to data.
    tmp_path : str, "/tmp/lenaig" by default
        Path to local temporary folder.

    Returns
    -------
    None

    """

    destination_folder = tmp_path
    os.makedirs(destination_folder, exist_ok=True)

    # Copy topo raster to tmp
    source_topo = topo._get_topo_paths(georef_input=georef_input, path_data=path_data)[
        2
    ]
    if is_folder_empty(os.path.dirname(source_topo)):
        raise FileNotFoundError(
            f"Source topo folder is empty: {os.path.dirname(source_topo)}"
        )
    print("Copying topo file...")
    shutil.copy2(source_topo, destination_folder)

    # Move all files stored in Georef_input/work_zone to tmp
    source_wind = os.path.join(georef_input, f"{filename_e}")
    if is_folder_empty(source_wind):
        raise FileNotFoundError(f"The folder of wind files is empty: {source_wind}")
    print("Copying wind files...")
    for filename in os.listdir(source_wind):
        file_path = os.path.join(source_wind, filename)
        if os.path.isfile(file_path):
            shutil.copy2(file_path, destination_folder)

    # Copy groovy script to tmp ("WindDataGDALCommands.groovy")
    if not os.path.isfile(groovy_path):
        raise FileNotFoundError(f"The groovy script is untraceable: {groovy_path}")
    print("Copying groovy script...")
    shutil.copy2(groovy_path, destination_folder)

    print(f"✅ All files have been copied to {destination_folder}.")


# ------
# ------


def georeferencement(
    filename_e: str,
    topo: TopoRaster,
    georef_input: str,
    georef_output: str,
    path_data: str,
    groovy_path: str,
    path_to_files: str = "/tmp/lenaig",
):
    """
    Execute georeferencement groovy script from python_code.

    Parameters
    ----------
    filename_e : str
        The name of the work zone (scenario) (exemple: "FR-Par-V2_d15").
    topo : Topo
        Object from Topo class, associated with same filename_e.
    georef_input : str
        The path to wind rasters to georeference.
    georef_output : str
        The path to folder where georeferenced files will be stored.
    path_data : str
        General path to data.
    groovy_path : str, /tmp/lenaig/WindDataGDALCommands.groovy by default
        Where is located the groovy script when execution of the georef task.
    path_to_files : str, /tmp/lenaig by default

    Returns
    -------
    The destination folder, in str.

    """

    out_dir = prepare_georef(filename_e, georef_output)

    # Prepare tmp folder
    prepare_tmp(filename_e, topo, georef_input, groovy_path, path_data)

    # --- Execute Groovy script ---
    result = subprocess.run(
        [
            "groovy",
            "/tmp/lenaig/WindDataGDALCommands.groovy",
            path_to_files,
        ],
        capture_output=True,  # pour récupérer stdout/stderr
        text=True,
    )

    print("Standard output :", result.stdout)
    print("Potential errors :", result.stderr)
    print("Output code :", result.returncode)

    # Execute process_wind_data (= Groovy output)
    subprocess.run(["bash", "/tmp/lenaig/process_wind_data.txt"], check=True)

    # --- Move georef files into correct folder ---

    source_folder = "/tmp/lenaig/results/"
    destination_folder = out_dir
    os.makedirs(destination_folder, exist_ok=True)

    if is_folder_empty(source_folder):
        raise FileNotFoundError(f"Followind folder is empty: {source_folder}")
    else:
        print("Folder is not empty")
        for item in os.listdir(source_folder):
            source_path = os.path.join(source_folder, item)
            destination_path = os.path.join(destination_folder, item)
            shutil.move(source_path, destination_path)
        print(f"Files moved to {destination_folder}.")

        # Clear tmp/lenaig folder
        folder_path = path_to_files
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    os.rmdir(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        print(f"Deletion of files done in {path_to_files}")

    print(f"Returning destination folder: {destination_folder}")
    return destination_folder


# ------
# ------

import os
import re


def list_files_starting_with(prefix, directory="."):
    pattern = re.compile(r"^" + re.escape(prefix) + r"(_\w+)?$")
    files = os.listdir(directory)
    return [f for f in files if pattern.match(f)]


# # Example
# fichiers = list_files_starting_with("FR-Par-V2", georef_input)
# print(fichiers)


# ------
# ------


def extract_prefix(filename):
    match = re.match(r"^([^-]+-[^-]+-[^_]+)", filename)
    return match.group(1) if match else None


# # Example of use
# filename = "FR-Par-V2_d15"
# prefix = extract_prefix(filename)
# print(prefix)  # Output: FR-Par-V2


# ------
# ------


def find_gcp(filename: str, georef_input: str):
    """
    Search the gdal_command.txt file containing the ground control points file.
    The founded path is printed.

    Parameters
    ----------
    filename : str
        The name of the work zone (scenario) (exemple: "FR-Par-V2_d15").
    georef_input : str
        The path to files which need to be georeferenced.

    Returns
    -------
    None
    """

    georef_input_path = os.path.join(georef_input, filename)
    # Does the directory have the gdal command?
    try_path = os.path.join(georef_input_path, "gdal_command.txt")
    if os.path.isfile(try_path):
        print(f"File 'gdal_command.txt' already exists.")
    else:
        # If not, does the other scenarii of the same domain have it?
        prefix = extract_prefix(filename)
        files_same_prefix = list_files_starting_with(prefix, georef_input)
        found = False
        for file in files_same_prefix:
            print("---------------------------------")
            print(file)
            path_gdal = os.path.join(georef_input, file, "gdal_command.txt")
            if os.path.isfile(path_gdal):
                print(f"File 'gdal_command.txt exists at {path_gdal}.")
                shutil.copy2(path_gdal, georef_input_path)
                found = True
                break
        if not found:
            print(
                "No 'gdal_command.txt' file found. \nPlease make the visual correspondence between OSM layer and wind raster layer on QGIS (manual step)."
            )


# Example of use:
# find_gcp(filename="KO-Dae-V11_d15", georef_input=georef_input)


# ------
# ------


def find_final_grid(filename: str, georef_output: str, res: int):
    """
    Search final_grid_{res}m.geojson in georef_output/filename directory.

    Parameters
    ----------
    filename : str
        The name of the work zone (scenario) (exemple: "FR-Par-V2_d15").
    georef_input : str
        The path to files which need to be georeferenced.
    res : int
        The resolution of the searched grid (default value in project: 50 m).

    Returns
    -------
    bool : whether final_grid is found (True) or not.
    """

    georef_output_path = os.path.join(georef_output, filename)
    # Does the directory have the gdal command?
    try_path = os.path.join(georef_output_path, f"final_{res}m.geojson")
    if os.path.isfile(try_path):
        print(f"File 'final_{res}m.geojson' already exists.")
        return True
    else:
        print("No 'final_{res}m.geojson' file found.")
        return False


# ------
# ------

import geopandas as gpd


def open_final_gdf(filename: str, georef_output: str, res_cell: int = 50):
    """
    Open the final grid with associated filename.

    Parameters
    ----------
    filename : str
        The name of the work zone (scenario) (exemple: "FR-Par-V2_d15").
    georef_output : str
        The path to georeference pipeline outputs.
    res_cell : int
        The grid cell resolution.

    Returns
    -------
    GeoDataFrame : the final grid.
    """

    path_final = os.path.join(georef_output, filename, f"final_{res_cell}m.geojson")
    gdf = gpd.read_file(path_final)
    return gdf
