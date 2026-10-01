// @GrabResolver(name='orbisgis', root='https://central.sonatype.com/repository/maven-snapshots')
@Grab(group='org.orbisgis.geoclimate', module='geoclimate', version='1.2.0')

import org.locationtech.jts.geom.Geometry
import org.orbisgis.data.H2GIS
import org.orbisgis.geoclimate.osm.OSM


/**
 * This script is used to extract the building based on the extended area of the input grid
 *
 * args[0]  path of the grid
 * args[1]  path of the folder to save the result
 *
 */


//Input grid
String inputGridFile = args[0]

//Directory to store all the results
String outputDirectory =  args[1]

if (!inputGridFile) {
    println "The input unit name cannot be empty"
    return
}

if (!outputDirectory) {
    println "The output directory to store the result cannot be null or empty"
    return
}

File dirFile = new File(outputDirectory)
if (!dirFile.exists()) {
    println "Create the output directory because it doesn't exist"
    dirFile.mkdir()
}
def local_database_name = "gisdata" + System.currentTimeMillis()

def h2gis_db_parameters = [
        "folder": outputDirectory,
        "name"  : "${local_database_name};AUTO_SERVER=TRUE".toString(),
        "delete": true
]

//Create before the local H2GIS database that will be used to compute the BBOX of the area
H2GIS h2GIS = H2GIS.open(h2gis_db_parameters.folder + File.separator + h2gis_db_parameters.name)
if (h2GIS == null) {
    println("Cannot create the local H2GIS database")
    return
}

if(!h2GIS.load(inputGridFile, "grid", true)){
    println("Cannot load the grid file "+inputGridFile)
    return
}
//Let's prepare the data
Geometry bboxGeometry = h2GIS.firstRow("SELECT ST_TRANSFORM(ST_ACCUM(THE_GEOM), 4326) AS the_geom from grid").the_geom

if (!bboxGeometry) {
    println "The bbox to process cannot be null or empty"
    return
}

//Convert the geometry to osm bbox
def env = bboxGeometry.getEnvelopeInternal()
def zone = [ env.getMinY() as float,env.getMinX() as float,env.getMaxY() as float,env.getMaxX() as float]

println("Bbox identified : "+ zone)

/*================================================================================
* Exemple with OSM input areas configuration
*/

def input = ["locations": [zone], "delete": true, "area": 2500]

/*================================================================================
* Folder to store the results and save the tables
*/
def  output  = [
        "folder": ["path"  : outputDirectory,
                   "tables": ["building", "zone"]],
]


/*================================================================================
* WORKFLOW PARAMETERS
*/
def workflow_parameters = [
        "description" : "Run the Geoclimate chain  and export result to a folder",
        "geoclimatedb": h2gis_db_parameters,
        "input"       : input,
        "output"      : output,
        "parameters"  :
                ["distance"             : 100,
                ]
    ]

OSM.workflow(workflow_parameters)
println(workflow_parameters)
