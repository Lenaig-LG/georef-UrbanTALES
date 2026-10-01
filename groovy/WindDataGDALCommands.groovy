//@GrabResolver(name='orbisgis', root='https://central.sonatype.com/repository/maven-snapshots')
//@Grab(group='org.orbisgis', module='cts', version='1.7.2-SNAPSHOT')



/**
 * This script is used to prepare the wind data with gdal
 */

if(!args){
    println("Please set a folder thar contains the GDAL commands from QGIS georeferencing tool, named gdal_command.txt\n" +
            "Example :  /tmp/lenaig_data")
    return
}

File dataFolder =  new File(args[0])

if(dataFolder && !dataFolder.exists()){
    println("The data folder doesn't exist")
    return
}

//Find the first image
def imagePrefix =  "wind_layer"
File pyGDALCommandFile = new File(dataFolder.getAbsolutePath()+File.separator+"gdal_command.txt")
File imageFile = new File(dataFolder.getAbsolutePath()+File.separator+imagePrefix+"_0.25.tif")

File outPutFolder =  new File(args[0]+File.separator+"results")

if(outPutFolder.exists()){
    outPutFolder.deleteDir()
    outPutFolder.mkdir()
}else{
    outPutFolder.mkdir()
}

if(pyGDALCommandFile && !pyGDALCommandFile.exists()){
    println("The GDAL command file doesn't exist")
    return
}

if(imageFile && !imageFile.exists()){
    println("The first image wind_layer_0.25.tif doesn't exist")
    return
}


String imagefileName= imageFile.name.toLowerCase()
if (!imagefileName.endsWith(".tif")) {
    println("The input file must be in a tiff format")
    return
}

def outputImage = imagefileName.substring(0, imagefileName.size()-4)

def outputTranslateImage = "${outPutFolder.getAbsolutePath()+File.separator}${outputImage}_translate.tif"

def outputGeoRefImage = "${outPutFolder.getAbsolutePath()+File.separator}${outputImage}_georef.tif"

def outputPolygonImage = "${outPutFolder.getAbsolutePath()+File.separator}${outputImage}_polygon.shp"

def outputReplaceNaN = "${outPutFolder.getAbsolutePath()+File.separator}${outputImage}_nan.tif"

def outputReclass = "${outPutFolder.getAbsolutePath()+File.separator}${outputImage}_rec.tif"

def lines = pyGDALCommandFile.readLines()

def gdal_translate_command = lines[0]

List gdal_translate_args = gdal_translate_command.split(" ") as List

gdal_translate_args.removeLast()
gdal_translate_args.removeLast()

def gdal_wrap_command = lines[1]
List gdal_wrap_command_args = gdal_wrap_command.split(" ") as List
gdal_wrap_command_args.removeLast()
gdal_wrap_command_args.removeLast()

def command =  ""
command += "echo A set of GDAL commands to transform the wind images in the good projection\n"
command+="\n\n"
command+="echo Step 1 : Extract the polygon as a geometry\n"
command += "echo replace NaN values to -9999\n"
command +="gdal_calc.py -A ${imageFile.getAbsolutePath()} --outfile=${outputReplaceNaN} --calc='numpy.nan_to_num(A, nan=-9999)'\n"
command +=  "echo start translating... $outputGeoRefImage\n"
command+= gdal_translate_args.join(" ")+ " ${outputReplaceNaN}  ${outputTranslateImage}\n"
command +=  "echo end translating... $outputTranslateImage\n"

command+="echo edit the projection of the raster\n"

command+=gdal_wrap_command_args.join(" ") +  " ${outputTranslateImage} ${outputGeoRefImage}\n"

command +=  "echo reclass ... $outputGeoRefImage\n"
command +="gdal_calc.py -A ${outputGeoRefImage} --outfile=${outputReclass} --calc='A>=-9999'\n"

command +=  "echo polygozine ... $outputReclass\n"
command+= "gdal_polygonize.py ${outputReclass} -b 1  ${outputPolygonImage}\n"

command+= "rm ${outputReclass} ${outputTranslateImage} ${outputReplaceNaN} ${outputGeoRefImage}\n"

command+="\n\n\n"
//Now geo_ref all bands for each levels
command+="echo Step 2 : Georeferencing all images by level 25, 30, 35...\n"
command+="\n\n"
0.25.step(50, 0.5){it->
    def inputImage = dataFolder.getAbsolutePath()+File.separator+ imagePrefix+"_"+it+".tif"
    def refImage = outPutFolder.getAbsolutePath()+File.separator+ imagePrefix+"_"+it+"_georef.tif"
    def translateImage = outPutFolder.getAbsolutePath()+File.separator+ imagePrefix+"_"+it+"_translate.tif"
    command+="\n\n"
    command+="echo Start image : $inputImage\n"
    command +=  "echo start translating... $refImage\n"
    command+=gdal_translate_args.join(" ") +  " ${inputImage}  ${translateImage}\n"
    command +=  "echo end translating... $translateImage\n"

    command+="echo edit the projection of the raster\n"

    command+="${gdal_wrap_command_args.join(" ")} ${translateImage} ${refImage}\n"

    command+= "rm  ${translateImage}\n"

    command+="echo End image : $inputImage\n"

}

/*
* Let's check if the topo tif exists
 */
imagePrefix =  "layer"
String topoImagePath = dataFolder.getAbsolutePath()+File.separator+imagePrefix+"_topo.tif"
File topoImage = new File(topoImagePath)
if(topoImage.exists()){
    String translateImage = dataFolder.getAbsolutePath()+File.separator+imagePrefix+"_translate_topo.tif"
    command +=  "echo start translating... $topoImagePath\n"
    command+=gdal_translate_args.join(" ") +  " ${topoImagePath}  ${translateImage}\n"
    command +=  "echo end translating... $translateImage\n"
    command+="echo edit the projection of the raster\n"
    String topoImageGeoref = outPutFolder.getAbsolutePath()+File.separator+imagePrefix+"_topo_georef.tif"
    command+="${gdal_wrap_command_args.join(" ")} ${translateImage} ${topoImageGeoref}\n"
    command+= "rm  ${translateImage}\n"
    command+="echo End image : $topoImageGeoref\n"
}

command += "echo end all\n"

println(command)

File data = new File(dataFolder.getAbsolutePath()+File.separator+"process_wind_data.txt")

data<<command

