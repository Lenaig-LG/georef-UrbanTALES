// Add as comment in IntelliJ
// @GrabResolver(name='orbisgis', root='https://central.sonatype.com/repository/maven-snapshots')
@Grab(group='org.orbisgis.geoclimate', module='geoclimate', version='1.2.0')

// Remove comment in IntelliJ
// package org.orbisgis.geoclimate.geoindicators

import org.orbisgis.data.jdbc.JdbcDataSource
import static org.orbisgis.data.H2GIS.open
import org.orbisgis.geoclimate.Geoindicators

// Path of the building file
String input_buildings = args[0]

// Path of the grid file
String input_grid = args[1]

// Path of the folder where the output grid (with indicators calculated) will be saved
String output_grid = args[2]

// Name of the grid cell ID
String grid_id = args[3]


// List of indicators to calculate
list_indicators = ["BUILDING_FRACTION", "BUILDING_HEIGHT", 
                   "FREE_EXTERNAL_FACADE_DENSITY", 
                   "BUILDING_HEIGHT_WEIGHTED", "BUILDING_SURFACE_DENSITY",
                   "ASPECT_RATIO", "SVF", "HEIGHT_OF_ROUGHNESS_ELEMENTS",
                   "TERRAIN_ROUGHNESS", "STREET_WIDTH", "PROJECTED_FACADE_DENSITY_DIR", 
                   "BUILDING_DIRECTION", "BUILDING_NUMBER", "LCZ_PRIMARY"]

// Open an H2GIS connection
h2GIS = open(File.createTempDir().toString() + File.separator + "myH2GIS_DB;AUTO_SERVER=TRUE")

main(h2GIS, input_buildings, input_grid, output_grid, list_indicators, grid_id)

static void main(JdbcDataSource h2GIS, String input_buildings, String input_grid, 
                 String output_grid, List list_indicators, grid_id) {
  
  // Load building and grid files into the Database
  File input_buildings_file = new File(input_buildings)
  String input_buildings_tab = input_buildings_file.name.take(input_buildings_file.name.lastIndexOf('.'))
  if (input_buildings_file.exists() and input_buildings_file.length() != 0){
    h2GIS.load(input_buildings.toString(), input_buildings_tab)
  }
  else{
    println(input_buildings.toString() + " do not exist or is empty")
  }
  
  // Load building and grid files into the Database
  File input_grid_file = new File(input_grid)
  String input_grid_tab = input_grid_file.name.take(input_grid_file.name.lastIndexOf('.'))
  if (input_grid_file.exists() and input_grid_file.length() != 0){
    h2GIS.load(input_grid.toString(), input_grid_tab)
  }
  else{
    println(input_grid.toString() + " do not exist or is empty")
  }
  
  // Create an ID with the right name for grid GeoClimate input
  h2GIS """DROP TABLE IF EXISTS GRID_WITH_ID;
          CREATE TABLE GRID_WITH_ID
          AS SELECT $grid_id AS ID_GRID,
                    THE_GEOM 
          FROM $input_grid_tab"""

  // Use the right building height column name for GeoClimate inputs
  h2GIS """ALTER TABLE $input_buildings_tab DROP COLUMN IF EXISTS HEIGHT_ROOF; 
           ALTER TABLE $input_buildings_tab RENAME COLUMN HEIGHT TO HEIGHT_ROOF;"""

  String outputTable = Geoindicators.WorkflowGeoIndicators.rasterizeIndicators(
                                h2GIS,
                                "GRID_WITH_ID", 
                                list_indicators,
                                input_buildings_tab, 
                                "", 
                                "",
                                "", 
                                "", 
                                "",
                                "", 
                                "", 
                                "",
                                "")
  
  // Rename the id grid to its initial value
  h2GIS """ALTER TABLE $outputTable RENAME COLUMN ID_GRID TO $grid_id;"""
 
  // Save the results at the given location
  h2GIS.save(outputTable, output_grid, true)
}
