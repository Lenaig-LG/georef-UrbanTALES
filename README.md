# georef-UrbanTALES

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL_v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

Workflow for processing UrbanTALES data and georeferencing the UrbanTALES scenarios to generate regular three-dimensional grids using wind data retrieved from UrbanTALES and geographic data retrieved from OpenStreetMap using the GeoClimate tool. The data processing workflow involves converting 3D wind data stored in NetCDF files (`.nc` files) into raster layers, which are then georeferenced using manually collected ground control points.

This work is part of a doctoral thesis on the effect of urban morphology on urban ventilation. The paper associated with this work is currently being drafted.

We would like to thank the authors of UrbanTALES for generously sharing their 3D airflow data with us.

## Table of contents

-   [Features](#features)
-   [Repository structure](#repository-structure)
-   [Requirements](#requirements)
-   [Installation](#installation)
-   [Path configuration](#path-configuration)
-   [Usage](#usage)
-   [License](#license)
-   [Author](#author)

## Features {#features}

-   Reading NetCDF files, including metadata handling.
-   Georeferencing of UrbanTALES wind and topography data (from no coordinate system in UrbanTALES data to the local UTM of the scenario).
-   Construction and manipulation of grids (initial grid, geographic grid, wind grid, final grid).
-   Processing of topographic rasters containing building heights.
-   Building extraction and geographical indicator computation using Groovy scripts (GeoClimate).
-   Full pipeline runnable from a Python script (`main.py`) or a notebook (`pipeline_process.ipynb`).

## Repository structure {#repository-structure}

```         
georef-UrbanTALES/
├── scripts/                     
│   ├── config.py                # Project paths (configurable)
│   ├── final_grid.py            # Final grid
│   └── functions.py             # Utility functions
│   ├── geo_grid.py              # Grid of geographical variables
│   ├── grid.py                  # Grids (base class)
│   ├── metadata.py              # Metadata
│   ├── netcdf.py                # NetCDF reading 
│   ├── raster.py                # Raster handling
│   ├── scenario.py              # Listing of all scenarios used
│   ├── topo_raster_georef.py    # Georeferenced building height raster 
│   ├── topo_raster.py           # Building height raster 
│   ├── wind_grid.py             # Grid of wind variables
├── groovy/                      
│   ├── extractBuilding.groovy      # Extracting building from OSM
│   ├── geoClimateIndicators.groovy # Compute geo indicators on grid
│   └── WindDataGDALCommands.groovy # Georeferencing
├── tests/                       
├── main.py                      # Run the pipeline (on all scenarios)
├── pipeline_process.ipynb       # Run the pipeline (on one scenario at a time)
├── LICENCE                      # GPL-3.0 text
├── LICENCE.LESSER               # LGPL-3.0 text
└── README.md
```

The data folder is not versioned. By default, the code looks for it in `../Data` (next to the repository). Please download UrbanTALES data here: https://urbantales.vercel.app/ (select 'realistic cases'). Data required : - the topo files with information on building heights - the png files to visualize the building footprints

The 3D wind NetCDF data are not available on UrbanTALES website. We would like to thank the authors for generously sharing their 3D data with us.

## Requirements {#requirements}

-   Python $\geq$ 3.10 (developed with Python 3.12)

## Installation {#installation}

``` bash
git clone git@github.com:Lenaig-LG/georef-UrbanTALES.git
cd georef-UrbanTALES
 
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Path configuration {#path-configuration}

Paths are defined in a single place: `scripts/config.py`.

-   The **project root** is detected automatically from the location of the code.
-   The **data folder** is not in the repository. By default, the code looks for it in `../Data` (next to the repository):

```         
Projects/
├── Data/                      # data (outside the repository)
│   ├── UrbanTALES/        
│       ├── 3Dwind/            # 3D wind data (NetCDF)
│       ├── png/               # png files downloaded from UrbanTALES
│       ├── topo/              # topo files downloaded from UrbanTALES
│   ├── Extracting_buildings/  # the georeferenced topo rasters (files are created during processing)
│   └── GeoReference/
│       ├── Georef_input/      # inputs for georeferencing
│       └── Georef_output/     # outputs for georeferencing
├── Outputs/                   # outputs (created automatically)
└── georef-UrbanTALES/         # this repository
```

To place the data elsewhere, set an environment variable:

``` bash
export URBANTALES_DATA=/path/to/Data
export URBANTALES_OUTPUT=/path/to/Outputs   # optional
```

To make it permanent, add these lines to `~/.bashrc`.

From the code:

``` python
from scripts.config import DATA_DIR, OUTPUT_DIR, PATH_3D, GEOREF_INPUT, GEOREF_OUTPUT, check_paths
 
check_paths()   # checks that Data exists, with an explicit error message otherwise
```

## Usage {#usage}

Always run from the repository root, with the virtual environment activated. - `main.py`: runs the processing for all scenarios listed in `scripts.scenario.py` - `pipeline_process.ipynb`: runs the processing pipeline one scenario at a time, with details on the steps and plots.

**Python script:**

``` bash
python pipeline_process.py
```

**Notebook:**

``` bash
jupyter notebook pipeline_process.ipynb
```

The first cell of the notebook detects the repository root and sets up imports and paths.

### Example

## Licence

This project is distributed under the **GNU Lesser General Public License v3.0 or later** (`LGPL-3.0-or-later`).

The full text can be found in the [`LICENCE.LESSER`](LICENCE.LESSER) and [`LICENCE`](LICENCE) files (the LGPL-3.0 supplements the GPL-3.0).

Copyright (C) 2026 Lenaig Le Grognec

## Author {#author}

Lenaig Le Grognec ([\@Lenaig-LG](https://github.com/Lenaig-LG))

Lab-STICC, Université de Bretagne Sud.